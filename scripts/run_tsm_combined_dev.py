#!/usr/bin/env python3
"""TASK-TSM-008: combined ERC + volatility-targeting TSM dev run (ADR-0031).

DEVELOPMENT ONLY -- promotion OOS-gated. Composes the two independently-validated
TSM wins: ERC (cross-sectional risk allocation, TSM-003 portfolio_erc flag) and
volatility targeting (time-series exposure scaling, TSM-007 overlay). Compares
four variants -- base / ERC-only / vol-target-only / COMBINED -- across the
robustness battery. The combined cell is preferred ONLY if it beats the best
single component; if it merely ties, parsimony keeps the single overlay.
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
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/tsm_combined_dev.json"
REPORT_MD = PROJECT_ROOT / "reports/tsm_combined_dev.md"
HOLD_HOURS = 120
_ANN = math.sqrt(24 * 365 / HOLD_HOURS)
COST_GRID = (0.0, 6.0, 15.0, 30.0)
_PERIOD_EDGES = ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
_PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
_BTC = "BTCUSDT"
_LOOKBACK_H = 672
_VARIANTS = ("base", "erc", "vol_target", "combined")


def _streams(
    bars: pd.DataFrame, cost_bps: float = 6.0, funding: bool = True
) -> dict[str, pd.Series]:
    base = _net(bars, TsmTrendConfig(include_funding=funding, cost_bps_per_leg=cost_bps))
    erc = _net(
        bars, TsmTrendConfig(include_funding=funding, cost_bps_per_leg=cost_bps, portfolio_erc=True)
    )
    return {
        "base": base,
        "erc": erc,
        "vol_target": apply_vol_target(base),
        "combined": apply_vol_target(erc),
    }


def main() -> int:
    bars = pd.read_csv(
        BARS,
        usecols=["symbol", "open_time", "log_price", "funding_rate_asof", "funding_interval_hours"],
    )
    streams = _streams(bars)
    edges = _edges_ms()
    btc_up = _btc_up(bars, streams["base"].index)

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-TSM-008 combined ERC + vol-target dev run (ADR-0031) -- DEVELOPMENT",
        "headline": {v: _metrics(streams[v]) for v in _VARIANTS},
        "sub_periods": [
            {
                "period": lbl,
                **{v: _metrics(_win(streams[v], edges[i], edges[i + 1])) for v in _VARIANTS},
            }
            for i, lbl in enumerate(_PERIOD_LABELS)
        ],
        "btc_regime": [
            {"regime": "BTC_up", **{v: _metrics(streams[v][btc_up]) for v in _VARIANTS}},
            {"regime": "BTC_down", **{v: _metrics(streams[v][~btc_up]) for v in _VARIANTS}},
        ],
        "cost_sensitivity": _cost_table(bars),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)
    h = payload["headline"]
    print(
        " | ".join(f"{v} {h[v]['sharpe']:.3f}" for v in _VARIANTS),
        file=sys.stderr,
    )
    print(f"Wrote {OUTPUT_JSON}\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


def _net(bars: pd.DataFrame, cfg: TsmTrendConfig) -> pd.Series:
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
        st = _streams(bars, cost_bps=c)
        rows.append({"cost_bps_per_leg": c, **{v: _metrics(st[v]) for v in _VARIANTS}})
    return rows


def _write_report(payload: dict) -> None:
    h = payload["headline"]
    lines = [
        "# TASK-TSM-008 -- Combined ERC + Vol-Targeting TSM (DEVELOPMENT, no verdict)",
        "",
        "Per `docs/pre_registers/TASK-TSM-008.md` (ADR-0031). Composes the two "
        "independently-validated wins -- ERC (cross-sectional, TSM-003) + volatility "
        "targeting (time-series, TSM-007). **Development-window result -- NOT a "
        "promotion; OOS-gated.** The combined cell is preferred only if it beats the "
        "best single component; a tie keeps the single overlay (parsimony).",
        "",
        "## Headline (full dev window) -- Sharpe / maxDD / net",
        "",
        "| Variant | Sharpe | Max drawdown | Net PnL |",
        "|---|---:|---:|---:|",
    ]
    labels = {
        "base": "base",
        "erc": "ERC-only",
        "vol_target": "vol-target-only",
        "combined": "COMBINED",
    }
    for v in _VARIANTS:
        m = h[v]
        lines.append(f"| {labels[v]} | {m['sharpe']:.3f} | {m['max_dd']:.4f} | {m['net']:.4f} |")
    lines += [
        "",
        "## Sub-period Sharpe",
        "",
        "| Period | base | ERC | vol-tgt | COMBINED |",
        "|---|---:|---:|---:|---:|",
    ]
    lines += [_row4(r["period"], r) for r in payload["sub_periods"]]
    lines += [
        "",
        "## BTC regime Sharpe",
        "",
        "| Regime | base | ERC | vol-tgt | COMBINED |",
        "|---|---:|---:|---:|---:|",
    ]
    lines += [_row4(r["regime"], r) for r in payload["btc_regime"]]
    lines += [
        "",
        "## Cost sensitivity (Sharpe)",
        "",
        "| Cost bps/leg | base | ERC | vol-tgt | COMBINED |",
        "|---|---:|---:|---:|---:|",
    ]
    lines += [_row4(f"{r['cost_bps_per_leg']:.0f}", r) for r in payload["cost_sensitivity"]]
    lines += ["", "## Reading", "", _reading(payload), ""]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _row4(label: str, r: dict) -> str:
    def fmt(v: str) -> str:
        return "n/a" if r[v]["sharpe"] is None else f"{r[v]['sharpe']:.3f}"

    return f"| {label} | {fmt('base')} | {fmt('erc')} | {fmt('vol_target')} | {fmt('combined')} |"


def _reading(payload: dict) -> str:
    h = payload["headline"]
    base, erc, vt, comb = (h[v]["sharpe"] for v in _VARIANTS)
    best_single = max(erc, vt)
    best_name = "ERC" if erc >= vt else "vol-targeting"
    dd_ok = h["combined"]["max_dd"] <= h["base"]["max_dd"]

    def combined_beats_all(key: str) -> bool:
        return all(
            r["combined"]["sharpe"] is not None
            and r["base"]["sharpe"] is not None
            and r["combined"]["sharpe"] >= r["base"]["sharpe"]
            for r in payload[key]
        )

    consistent = combined_beats_all("sub_periods") and combined_beats_all("btc_regime")
    margin = comb - best_single
    if margin > 0.02 and dd_ok and consistent:  # noqa: PLR2004
        verdict = (
            f"CANDIDATE (combined preferred): combined Sharpe {comb:.3f} beats the best "
            f"single component ({best_name} {best_single:.3f}) by {margin:+.3f}, drawdown "
            "not worse, consistent across cuts. The two overlays are complementary."
        )
    else:
        verdict = (
            f"NO INCREMENTAL GAIN over the best single component ({best_name} "
            f"{best_single:.3f}); combined {comb:.3f} (delta {margin:+.3f}). By parsimony "
            f"(ADR-0031), the single overlay (vol-targeting, Sharpe {vt:.3f}) remains the "
            "preferred TSM OOS candidate -- combining ERC + vol-target adds complexity "
            "without a material edge. Documented; no promotion; OOS-gated."
        )
    return (
        f"Sharpe: base {base:.3f} | ERC {erc:.3f} | vol-target {vt:.3f} | combined "
        f"{comb:.3f}. Combined beats base in every cut: {consistent}; combined maxDD <= "
        f"base: {dd_ok}. {verdict}"
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
