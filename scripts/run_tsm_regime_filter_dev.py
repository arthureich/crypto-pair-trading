#!/usr/bin/env python3
"""TASK-TSM-001: regime-filter dev run + robustness battery (ADR-0031).

DEVELOPMENT ONLY -- no promotion verdict (promotion is OOS-gated). Compares the
base vol-targeted TSM (FC-II-008, with funding) against the regime-filtered TSM
(flat when aggregate trend strength is below its 90d causal median) across the
mandatory robustness battery: headline risk-adjusted metrics, sub-period
stability, cost sensitivity, funding sensitivity, BTC up/down regimes, drawdown,
and the exposure (fraction of time ON). Params are fixed a priori; nothing is
tuned to the results.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.tsm_trend import (  # noqa: E402
    TsmTrendConfig,
    TsmTrendResult,
    _trend_strength_regime,
    run_tsm_trend_backtest,
    summarize_tsm_trend,
)

BARS = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/tsm_regime_filter_dev.json"
REPORT_MD = PROJECT_ROOT / "reports/tsm_regime_filter_dev.md"
COST_GRID = (0.0, 6.0, 15.0, 30.0, 60.0)
_PERIOD_EDGES = ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
_PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
_BTC = "BTCUSDT"
_LOOKBACK_H = 672


def main() -> int:
    bars = pd.read_csv(
        BARS,
        usecols=["symbol", "open_time", "log_price", "funding_rate_asof", "funding_interval_hours"],
    )
    base_cfg = TsmTrendConfig(include_funding=True)
    filt_cfg = TsmTrendConfig(include_funding=True, regime_filter=True)
    base = run_tsm_trend_backtest(bars, base_cfg)
    filt = run_tsm_trend_backtest(bars, filt_cfg)

    edges = _edges_ms()
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-TSM-001 regime filter dev run (ADR-0031) -- DEVELOPMENT, no verdict",
        "headline": {
            "base": asdict(summarize_tsm_trend(base, base_cfg)),
            "filtered": asdict(summarize_tsm_trend(filt, filt_cfg)),
            "fraction_time_on": _fraction_on(bars, base.rebalance_times),
        },
        "sub_periods": _sub_period_table(base, filt, base_cfg, filt_cfg, edges),
        "btc_regime": _btc_regime_table(bars, base, filt, base_cfg, filt_cfg),
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
        f"base Sharpe {h['base']['tsm_sharpe']:.3f} maxDD {h['base']['tsm_max_drawdown']:.3f} | "
        f"filtered Sharpe {h['filtered']['tsm_sharpe']:.3f} maxDD "
        f"{h['filtered']['tsm_max_drawdown']:.3f} | on {h['fraction_time_on']:.2f}",
        file=sys.stderr,
    )
    print(f"Wrote {OUTPUT_JSON}\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


def _edges_ms() -> tuple[int, ...]:
    return tuple(int(pd.Timestamp(d, tz="UTC").timestamp() * 1000) for d in _PERIOD_EDGES)


def _slice(result: TsmTrendResult, keep: list[bool]) -> TsmTrendResult:
    idx = [i for i, k in enumerate(keep) if k]

    def take(seq: tuple) -> tuple:
        return tuple(seq[i] for i in idx)

    return TsmTrendResult(
        rebalance_times=take(result.rebalance_times),
        tsm_net=take(result.tsm_net),
        tsm_long_only_net=take(result.tsm_long_only_net),
        baseline=take(result.baseline),
        tsm_turnover=take(result.tsm_turnover),
        tsm_long_sleeve=take(result.tsm_long_sleeve),
        tsm_short_sleeve=take(result.tsm_short_sleeve),
    )


def _sharpe_of(result: TsmTrendResult, cfg: TsmTrendConfig) -> dict:
    if len(result.rebalance_times) < 2:  # noqa: PLR2004
        return {"n": len(result.rebalance_times), "sharpe": None, "max_dd": None, "net": None}
    s = summarize_tsm_trend(result, cfg)
    return {
        "n": s.n_rebalances,
        "sharpe": s.tsm_sharpe,
        "max_dd": s.tsm_max_drawdown,
        "net": s.tsm_net_pnl,
    }


def _sub_period_table(base, filt, base_cfg, filt_cfg, edges) -> list[dict]:
    rows = []
    for i, label in enumerate(_PERIOD_LABELS):
        lo, hi = edges[i], edges[i + 1]
        keep = [lo <= t < hi for t in base.rebalance_times]
        rows.append(
            {
                "period": label,
                "base": _sharpe_of(_slice(base, keep), base_cfg),
                "filtered": _sharpe_of(_slice(filt, keep), filt_cfg),
            }
        )
    return rows


def _btc_regime_table(bars, base, filt, base_cfg, filt_cfg) -> list[dict]:
    price = bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    if _BTC not in price.columns:
        return []
    trailing_btc = (price[_BTC] - price[_BTC].shift(_LOOKBACK_H)).reindex(base.rebalance_times)
    up = [bool(v > 0) for v in trailing_btc.to_numpy()]
    rows = []
    for label, mask in (("BTC_up", up), ("BTC_down", [not u for u in up])):
        rows.append(
            {
                "regime": label,
                "base": _sharpe_of(_slice(base, mask), base_cfg),
                "filtered": _sharpe_of(_slice(filt, mask), filt_cfg),
            }
        )
    return rows


def _cost_table(bars) -> list[dict]:
    rows = []
    for cost in COST_GRID:
        b = TsmTrendConfig(include_funding=True, cost_bps_per_leg=cost)
        f = TsmTrendConfig(include_funding=True, cost_bps_per_leg=cost, regime_filter=True)
        rows.append(
            {
                "cost_bps_per_leg": cost,
                "base": _sharpe_of(run_tsm_trend_backtest(bars, b), b),
                "filtered": _sharpe_of(run_tsm_trend_backtest(bars, f), f),
            }
        )
    return rows


def _funding_table(bars) -> list[dict]:
    rows = []
    for funding in (False, True):
        b = TsmTrendConfig(include_funding=funding)
        f = TsmTrendConfig(include_funding=funding, regime_filter=True)
        rows.append(
            {
                "include_funding": funding,
                "base": _sharpe_of(run_tsm_trend_backtest(bars, b), b),
                "filtered": _sharpe_of(run_tsm_trend_backtest(bars, f), f),
            }
        )
    return rows


def _fraction_on(bars: pd.DataFrame, rebalance_times: tuple[int, ...]) -> float:
    cfg = TsmTrendConfig()
    price = bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    vol = price.diff().shift(1).rolling(cfg.vol_window_hours).std()
    trailing = price - price.shift(cfg.lookback_hours)
    regime = _trend_strength_regime(trailing, vol).reindex(rebalance_times)
    valid = regime.dropna()
    return float(valid.mean()) if len(valid) else float("nan")


def _write_report(payload: dict) -> None:
    h = payload["headline"]
    b, f = h["base"], h["filtered"]
    lines = [
        "# TASK-TSM-001 -- Regime Filter Dev Run (DEVELOPMENT, no verdict)",
        "",
        "Per `docs/pre_registers/TASK-TSM-001.md` (ADR-0031). Base = vol-targeted "
        "TSM with funding (FC-II-008); filtered = flat when aggregate trend strength "
        "(mean of |trailing_return|/vol) is below its 90d causal median. Params fixed "
        "a priori. **Development-window result -- NOT a promotion; promotion is "
        "OOS-gated.** Robustness battery below is decisive per the pre-registration.",
        "",
        "## Headline (full dev window)",
        "",
        "| Metric | Base | Filtered |",
        "|---|---:|---:|",
        f"| Sharpe | {b['tsm_sharpe']:.3f} | {f['tsm_sharpe']:.3f} |",
        f"| Max drawdown | {b['tsm_max_drawdown']:.4f} | {f['tsm_max_drawdown']:.4f} |",
        f"| Net PnL | {b['tsm_net_pnl']:.4f} | {f['tsm_net_pnl']:.4f} |",
        f"| Mean turnover | {b['mean_turnover']:.4f} | {f['mean_turnover']:.4f} |",
        f"| Rebalances | {b['n_rebalances']} | {f['n_rebalances']} |",
        "",
        f"Fraction of rebalances the regime is ON (book live): "
        f"**{h['fraction_time_on']:.2f}** (the filter is flat the rest of the time).",
        "",
        "## Sub-period stability (Sharpe)",
        "",
        "| Period | Base | Filtered |",
        "|---|---:|---:|",
    ]
    lines += [_cmp_row(r["period"], r["base"], r["filtered"]) for r in payload["sub_periods"]]
    lines += ["", "## BTC regime (Sharpe)", "", "| Regime | Base | Filtered |", "|---|---:|---:|"]
    lines += [_cmp_row(r["regime"], r["base"], r["filtered"]) for r in payload["btc_regime"]]
    lines += [
        "",
        "## Cost sensitivity (Sharpe)",
        "",
        "| Cost bps/leg | Base | Filtered |",
        "|---|---:|---:|",
    ]
    lines += [
        _cmp_row(f"{r['cost_bps_per_leg']:.0f}", r["base"], r["filtered"])
        for r in payload["cost_sensitivity"]
    ]
    lines += [
        "",
        "## Funding sensitivity (Sharpe)",
        "",
        "| include_funding | Base | Filtered |",
        "|---|---:|---:|",
    ]
    lines += [
        _cmp_row(str(r["include_funding"]), r["base"], r["filtered"])
        for r in payload["funding_sensitivity"]
    ]
    lines += ["", "## Reading", "", _reading(payload), ""]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _cmp_row(label: str, base: dict, filt: dict) -> str:
    def fmt(d: dict) -> str:
        return "n/a" if d["sharpe"] is None else f"{d['sharpe']:.3f}"

    return f"| {label} | {fmt(base)} | {fmt(filt)} |"


def _reading(payload: dict) -> str:
    b, f = payload["headline"]["base"], payload["headline"]["filtered"]
    d_sharpe = f["tsm_sharpe"] - b["tsm_sharpe"]
    d_dd = f["tsm_max_drawdown"] - b["tsm_max_drawdown"]
    subs = payload["sub_periods"]
    helps_all = all(
        s["filtered"]["sharpe"] is not None
        and s["base"]["sharpe"] is not None
        and s["filtered"]["sharpe"] >= s["base"]["sharpe"]
        for s in subs
    )
    btc = payload["btc_regime"]
    helps_both_btc = all(
        r["filtered"]["sharpe"] is not None
        and r["base"]["sharpe"] is not None
        and r["filtered"]["sharpe"] >= r["base"]["sharpe"]
        for r in btc
    )
    verdict = (
        "CANDIDATE for OOS: filter improves Sharpe AND does not worsen drawdown, "
        "consistently across all 3 sub-periods AND both BTC regimes."
        if (d_sharpe > 0 and d_dd <= 0 and helps_all and helps_both_btc)
        else "REJECTED as a dev candidate: the filter does not deliver a CONSISTENT "
        "risk-adjusted improvement (Sharpe up AND drawdown not worse, stable across "
        "all 3 sub-periods and both BTC regimes). Per the pre-registration, an "
        "improvement seen only in aggregate or one regime is treated as a likely "
        "false positive. Hypothesis closed with this negative result; proceed to "
        "Line 2 (position sizing)."
    )
    return (
        f"Filtered vs base: Sharpe {b['tsm_sharpe']:.3f} -> {f['tsm_sharpe']:.3f} "
        f"(delta {d_sharpe:+.3f}); maxDD {b['tsm_max_drawdown']:.4f} -> "
        f"{f['tsm_max_drawdown']:.4f} (delta {d_dd:+.4f}); book live "
        f"{payload['headline']['fraction_time_on']:.0%} of the time. "
        f"Consistent across sub-periods: {helps_all}; across BTC regimes: "
        f"{helps_both_btc}. {verdict}"
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
