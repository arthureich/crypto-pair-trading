#!/usr/bin/env python3
"""TASK-TSM-007: volatility-targeted TSM dev run + robustness battery (ADR-0031).

DEVELOPMENT ONLY -- promotion OOS-gated. Applies the Moreira-Muir managed-vol
overlay (scale each rebalance's return inversely to the strategy's own trailing
realized vol, target ~constant vol) to the base TSM (FC-II-008) return stream,
and compares Sharpe / drawdown / net vs the base across the robustness battery
(sub-period, cost, funding, BTC regime). Honest prior: the benefit is often
muted for pure trend, so a near-neutral result is expected and acceptable.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.tsm_trend import TsmTrendConfig, run_tsm_trend_backtest  # noqa: E402
from src.research.vol_target import apply_vol_target  # noqa: E402

BARS = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/tsm_vol_target_dev.json"
REPORT_MD = PROJECT_ROOT / "reports/tsm_vol_target_dev.md"
HOLD_HOURS = 120
_ANN = math.sqrt(24 * 365 / HOLD_HOURS)
COST_GRID = (0.0, 6.0, 15.0, 30.0)
_PERIOD_EDGES = ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
_PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
_BTC = "BTCUSDT"
_LOOKBACK_H = 672


def main() -> int:
    bars = pd.read_csv(
        BARS,
        usecols=["symbol", "open_time", "log_price", "funding_rate_asof", "funding_interval_hours"],
    )
    base = _net_series(bars, TsmTrendConfig(include_funding=True))
    scaled = apply_vol_target(base)

    edges = _edges_ms()
    btc_up = _btc_up(bars, base.index)
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-TSM-007 vol-targeted TSM dev run (ADR-0031) -- DEVELOPMENT, no verdict",
        "headline": {"base": _metrics(base), "vol_target": _metrics(scaled)},
        "sub_periods": [
            {
                "period": lbl,
                "base": _metrics(_win(base, edges[i], edges[i + 1])),
                "vol_target": _metrics(_win(scaled, edges[i], edges[i + 1])),
            }
            for i, lbl in enumerate(_PERIOD_LABELS)
        ],
        "btc_regime": [
            {
                "regime": "BTC_up",
                "base": _metrics(base[btc_up]),
                "vol_target": _metrics(scaled[btc_up]),
            },
            {
                "regime": "BTC_down",
                "base": _metrics(base[~btc_up]),
                "vol_target": _metrics(scaled[~btc_up]),
            },
        ],
        "cost_sensitivity": _cost_table(bars),
        "funding_sensitivity": _funding_table(bars),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)
    h = payload["headline"]
    print(
        f"base Sharpe {h['base']['sharpe']:.3f} maxDD {h['base']['max_dd']:.3f} | "
        f"vol-target Sharpe {h['vol_target']['sharpe']:.3f} maxDD "
        f"{h['vol_target']['max_dd']:.3f}",
        file=sys.stderr,
    )
    print(f"Wrote {OUTPUT_JSON}\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


def _net_series(bars: pd.DataFrame, cfg: TsmTrendConfig) -> pd.Series:
    r = run_tsm_trend_backtest(bars, cfg)
    return pd.Series(r.tsm_net, index=list(r.rebalance_times))


def _edges_ms() -> tuple[int, ...]:
    return tuple(int(pd.Timestamp(d, tz="UTC").timestamp() * 1000) for d in _PERIOD_EDGES)


def _win(s: pd.Series, lo: int, hi: int) -> pd.Series:
    return s[(s.index >= lo) & (s.index < hi)]


def _btc_up(bars: pd.DataFrame, times: pd.Index) -> pd.Series:
    price = bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    tr = (price[_BTC] - price[_BTC].shift(_LOOKBACK_H)).reindex(times)
    return pd.Series([bool(v > 0) for v in tr.to_numpy()], index=times)


def _metrics(s: pd.Series) -> dict:
    r = np.asarray(s.dropna(), dtype=float)
    if len(r) < 2:  # noqa: PLR2004
        return {"n": int(len(r)), "sharpe": None, "max_dd": None, "net": None}
    std = r.std(ddof=1)
    sharpe = float(r.mean() / std * _ANN) if std > 0 else None
    equity = np.cumsum(r)
    max_dd = float(np.max(np.maximum.accumulate(equity) - equity))
    return {"n": int(len(r)), "sharpe": sharpe, "max_dd": max_dd, "net": float(r.sum())}


def _cost_table(bars: pd.DataFrame) -> list[dict]:
    rows = []
    for c in COST_GRID:
        base = _net_series(bars, TsmTrendConfig(include_funding=True, cost_bps_per_leg=c))
        rows.append(
            {
                "cost_bps_per_leg": c,
                "base": _metrics(base),
                "vol_target": _metrics(apply_vol_target(base)),
            }
        )
    return rows


def _funding_table(bars: pd.DataFrame) -> list[dict]:
    rows = []
    for f in (False, True):
        base = _net_series(bars, TsmTrendConfig(include_funding=f))
        rows.append(
            {
                "include_funding": f,
                "base": _metrics(base),
                "vol_target": _metrics(apply_vol_target(base)),
            }
        )
    return rows


def _write_report(payload: dict) -> None:
    b, v = payload["headline"]["base"], payload["headline"]["vol_target"]
    lines = [
        "# TASK-TSM-007 -- Volatility-Targeted TSM Dev Run (DEVELOPMENT, no verdict)",
        "",
        "Per `docs/pre_registers/TASK-TSM-007.md` (ADR-0031). Managed-vol overlay "
        "(scale each rebalance's return inversely to the strategy's own trailing "
        "realized vol; target ~constant vol, average leverage ~1) on the base TSM "
        "(FC-II-008). **Development-window result -- NOT a promotion; OOS-gated.** "
        "Honest prior: the benefit is often muted for pure trend.",
        "",
        "## Headline (full dev window)",
        "",
        "| Metric | Base | Vol-targeted |",
        "|---|---:|---:|",
        f"| Sharpe | {b['sharpe']:.3f} | {v['sharpe']:.3f} |",
        f"| Max drawdown | {b['max_dd']:.4f} | {v['max_dd']:.4f} |",
        f"| Net PnL | {b['net']:.4f} | {v['net']:.4f} |",
        f"| Rebalances | {b['n']} | {v['n']} |",
        "",
        "## Sub-period stability (Sharpe)",
        "",
        "| Period | Base | Vol-targeted |",
        "|---|---:|---:|",
    ]
    lines += [_row(r["period"], r) for r in payload["sub_periods"]]
    lines += [
        "",
        "## BTC regime (Sharpe)",
        "",
        "| Regime | Base | Vol-targeted |",
        "|---|---:|---:|",
    ]
    lines += [_row(r["regime"], r) for r in payload["btc_regime"]]
    lines += [
        "",
        "## Cost sensitivity (Sharpe)",
        "",
        "| Cost bps/leg | Base | Vol-targeted |",
        "|---|---:|---:|",
    ]
    for r in payload["cost_sensitivity"]:
        lines.append(_row(f"{r['cost_bps_per_leg']:.0f}", r))
    lines += [
        "",
        "## Funding sensitivity (Sharpe)",
        "",
        "| include_funding | Base | Vol-targeted |",
        "|---|---:|---:|",
    ]
    for r in payload["funding_sensitivity"]:
        lines.append(_row(str(r["include_funding"]), r))
    lines += ["", "## Reading", "", _reading(payload), ""]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _row(label: str, r: dict) -> str:
    def fmt(d: dict) -> str:
        return "n/a" if d["sharpe"] is None else f"{d['sharpe']:.3f}"

    return f"| {label} | {fmt(r['base'])} | {fmt(r['vol_target'])} |"


def _reading(payload: dict) -> str:
    b, v = payload["headline"]["base"], payload["headline"]["vol_target"]
    d_sharpe = v["sharpe"] - b["sharpe"]
    d_dd = v["max_dd"] - b["max_dd"]

    def helps_all(key: str) -> bool:
        return all(
            r["vol_target"]["sharpe"] is not None
            and r["base"]["sharpe"] is not None
            and r["vol_target"]["sharpe"] >= r["base"]["sharpe"]
            for r in payload[key]
        )

    consistent = helps_all("sub_periods") and helps_all("btc_regime")
    candidate = d_sharpe > 0 and d_dd <= 0 and consistent
    verdict = (
        "CANDIDATE for OOS: vol-targeting improves Sharpe AND does not worsen "
        "drawdown, consistently across sub-periods and BTC regimes."
        if candidate
        else "REJECTED / NEUTRAL as a dev candidate: vol-targeting does not deliver a "
        "consistent risk-adjusted improvement over the base TSM. Consistent with the "
        "literature caveat that managed-vol adds little to pure trend (already partly "
        "vol-aware via inverse-vol sizing). Documented and closed; the base TSM stays "
        "the lead. No promotion; OOS-gated."
    )
    return (
        f"Vol-targeted vs base: Sharpe {b['sharpe']:.3f} -> {v['sharpe']:.3f} "
        f"(delta {d_sharpe:+.3f}); maxDD {b['max_dd']:.4f} -> {v['max_dd']:.4f} "
        f"(delta {d_dd:+.4f}). Consistent across sub-periods AND BTC regimes: "
        f"{consistent}. {verdict}"
    )


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, bool | str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
