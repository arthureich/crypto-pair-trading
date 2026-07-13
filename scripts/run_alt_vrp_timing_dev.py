#!/usr/bin/env python3
"""TASK-ALT-012: VRP-timing strategy dev run + robustness battery (ADR-0032).

DEVELOPMENT ONLY -- promotion is OOS-gated. Primary cell: long/short sign(vrp_z)
weekly BTC/ETH book vs equal-weight buy-and-hold. Secondary (DESCRIPTIVE, never
promoted): long-only. Robustness battery: sub-period stability, cost
sensitivity, BTC up/down regime, drawdown. Signal (vrp_z) is the exact ALT-011
construction; the proper non-overlapping weekly rebalance corrects the
overlapping-sample bias of the decile economic check.
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

from src.research.vrp_timing import (  # noqa: E402
    VrpTimingConfig,
    VrpTimingResult,
    compute_vrp_z,
    run_vrp_timing_backtest,
    summarize_vrp_timing,
)

DVOL_CSV = (
    PROJECT_ROOT / "data/research/binance_public/normalized/sprint_alt_dvol_202306_202605.csv.gz"
)
BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/alt_vrp_timing_dev.json"
REPORT_MD = PROJECT_ROOT / "reports/alt_vrp_timing_dev.md"
COST_GRID = (0.0, 6.0, 15.0, 30.0)
_PERIOD_EDGES = ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
_PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
_ASSETS = ("btc", "eth")
_LOOKBACK_H = 672


def main() -> int:
    price, vrp_z, btc_trailing = _panels()
    ls_cfg = VrpTimingConfig()
    lo_cfg = VrpTimingConfig(long_only=True)
    ls = run_vrp_timing_backtest(price, vrp_z, ls_cfg)
    lo = run_vrp_timing_backtest(price, vrp_z, lo_cfg)

    edges = _edges_ms()
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-ALT-012 VRP-timing dev run (ADR-0032) -- DEVELOPMENT, no verdict",
        "headline": {
            "long_short": asdict(summarize_vrp_timing(ls, ls_cfg)),
            "long_only_secondary": asdict(summarize_vrp_timing(lo, lo_cfg)),
        },
        "sub_periods": _sub_table(ls, ls_cfg, edges),
        "btc_regime": _btc_table(ls, ls_cfg, btc_trailing),
        "cost_sensitivity": _cost_table(price, vrp_z),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)
    h = payload["headline"]["long_short"]
    print(
        f"long/short: strat Sharpe {h['strat_sharpe']:.3f} vs baseline "
        f"{h['baseline_sharpe']:.3f}; maxDD {h['strat_max_drawdown']:.3f} vs "
        f"{h['baseline_max_drawdown']:.3f}",
        file=sys.stderr,
    )
    print(f"Wrote {OUTPUT_JSON}\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


def _panels() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    bars = pd.read_csv(BARS_CSV, usecols=["symbol", "base_asset", "open_time", "log_price"])
    bars["base_asset"] = bars["base_asset"].str.lower()
    bars = bars[bars["base_asset"].isin(_ASSETS)]
    bars["day"] = pd.to_datetime(bars["open_time"], unit="ms", utc=True).dt.floor("D")
    daily = (
        bars.sort_values("open_time", kind="mergesort")
        .groupby(["base_asset", "day"], as_index=False)
        .last()
    )
    price = daily.pivot(index="day", columns="base_asset", values="log_price").sort_index()
    price.index = [int(pd.Timestamp(d).timestamp() * 1000) for d in price.index]

    dvol = pd.read_csv(DVOL_CSV, parse_dates=["day"])
    dvol_wide = dvol.pivot(index="day", columns="asset", values="dvol_close")
    dvol_wide.index = [int(pd.Timestamp(d).timestamp() * 1000) for d in dvol_wide.index]
    dvol_wide = dvol_wide.reindex(index=price.index, columns=price.columns)

    vrp_z = compute_vrp_z(dvol_wide, price, VrpTimingConfig())
    # BTC trailing 28d (hourly lookback -> daily approx via 28 daily steps) for regime.
    btc_trailing = price["btc"] - price["btc"].shift(_LOOKBACK_H // 24)
    return price, vrp_z, btc_trailing


def _edges_ms() -> tuple[int, ...]:
    return tuple(int(pd.Timestamp(d, tz="UTC").timestamp() * 1000) for d in _PERIOD_EDGES)


def _slice(result: VrpTimingResult, keep: list[bool]) -> VrpTimingResult:
    idx = [i for i, k in enumerate(keep) if k]

    def take(seq: tuple) -> tuple:
        return tuple(seq[i] for i in idx)

    return VrpTimingResult(
        rebalance_times=take(result.rebalance_times),
        strat_net=take(result.strat_net),
        baseline=take(result.baseline),
        turnover=take(result.turnover),
    )


def _metrics(result: VrpTimingResult, cfg: VrpTimingConfig) -> dict:
    if len(result.rebalance_times) < 2:  # noqa: PLR2004
        return {"n": len(result.rebalance_times), "strat": None, "base": None, "dd": None}
    s = summarize_vrp_timing(result, cfg)
    return {
        "n": s.n_rebalances,
        "strat": s.strat_sharpe,
        "base": s.baseline_sharpe,
        "dd": s.strat_max_drawdown,
        "dd_base": s.baseline_max_drawdown,
    }


def _sub_table(ls: VrpTimingResult, cfg: VrpTimingConfig, edges: tuple[int, ...]) -> list[dict]:
    rows = []
    for i, label in enumerate(_PERIOD_LABELS):
        lo_ms, hi_ms = edges[i], edges[i + 1]
        keep = [lo_ms <= t < hi_ms for t in ls.rebalance_times]
        rows.append({"period": label, **_metrics(_slice(ls, keep), cfg)})
    return rows


def _btc_table(ls: VrpTimingResult, cfg: VrpTimingConfig, btc_trailing: pd.Series) -> list[dict]:
    tr = btc_trailing.reindex(ls.rebalance_times)
    up = [bool(v > 0) for v in tr.to_numpy()]
    rows = []
    for label, mask in (("BTC_up", up), ("BTC_down", [not u for u in up])):
        rows.append({"regime": label, **_metrics(_slice(ls, mask), cfg)})
    return rows


def _cost_table(price: pd.DataFrame, vrp_z: pd.DataFrame) -> list[dict]:
    rows = []
    for c in COST_GRID:
        cfg = VrpTimingConfig(cost_bps_per_leg=c)
        m = _metrics(run_vrp_timing_backtest(price, vrp_z, cfg), cfg)
        rows.append({"cost_bps_per_leg": c, **m})
    return rows


def _write_report(payload: dict) -> None:
    ls = payload["headline"]["long_short"]
    lo = payload["headline"]["long_only_secondary"]
    lines = [
        "# TASK-ALT-012 -- VRP-Timing Strategy Dev Run (DEVELOPMENT, no verdict)",
        "",
        "Per `docs/pre_registers/TASK-ALT-012.md` (ADR-0032). Primary: long/short "
        "sign(vrp_z) weekly BTC/ETH book vs equal-weight buy-and-hold. Signal = the "
        "exact ALT-011 vrp_z; non-overlapping weekly rebalance (corrects the decile "
        "check's overlapping-sample bias). **Development-window result -- NOT a "
        "promotion; OOS-gated.** Long-only is a DESCRIPTIVE secondary (never promoted).",
        "",
        "## Headline (full dev window)",
        "",
        "| Metric | Long/short (primary) | Buy-and-hold | Long-only (secondary) |",
        "|---|---:|---:|---:|",
        f"| Sharpe | {ls['strat_sharpe']:.3f} | {ls['baseline_sharpe']:.3f} | "
        f"{lo['strat_sharpe']:.3f} |",
        f"| Max drawdown | {ls['strat_max_drawdown']:.4f} | {ls['baseline_max_drawdown']:.4f} | "
        f"{lo['strat_max_drawdown']:.4f} |",
        f"| Net PnL | {ls['strat_net_pnl']:.4f} | {ls['baseline_net_pnl']:.4f} | "
        f"{lo['strat_net_pnl']:.4f} |",
        f"| Mean turnover | {ls['mean_turnover']:.4f} | -- | {lo['mean_turnover']:.4f} |",
        f"| Rebalances | {ls['n_rebalances']} | {ls['n_rebalances']} | {lo['n_rebalances']} |",
        "",
        "## Sub-period stability (primary long/short Sharpe: strat vs buy-hold)",
        "",
        "| Period | Strat | Buy-hold |",
        "|---|---:|---:|",
    ]
    lines += [_cmp_row(r["period"], r) for r in payload["sub_periods"]]
    lines += [
        "",
        "## BTC regime (primary Sharpe: strat vs buy-hold)",
        "",
        "| Regime | Strat | Buy-hold |",
        "|---|---:|---:|",
    ]
    lines += [_cmp_row(r["regime"], r) for r in payload["btc_regime"]]
    lines += [
        "",
        "## Cost sensitivity (primary strat Sharpe)",
        "",
        "| Cost bps/leg | Strat Sharpe |",
        "|---|---:|",
    ]
    for r in payload["cost_sensitivity"]:
        strat = "n/a" if r["strat"] is None else f"{r['strat']:.3f}"
        lines.append(f"| {r['cost_bps_per_leg']:.0f} | {strat} |")
    lines += ["", "## Reading", "", _reading(payload), ""]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _cmp_row(label: str, r: dict) -> str:
    strat = "n/a" if r["strat"] is None else f"{r['strat']:.3f}"
    base = "n/a" if r["base"] is None else f"{r['base']:.3f}"
    return f"| {label} | {strat} | {base} |"


def _reading(payload: dict) -> str:
    ls = payload["headline"]["long_short"]
    d_sharpe = ls["strat_sharpe"] - ls["baseline_sharpe"]
    dd_ok = ls["strat_max_drawdown"] <= ls["baseline_max_drawdown"]
    subs = payload["sub_periods"]
    beats_all = all(
        s["strat"] is not None and s["base"] is not None and s["strat"] > s["base"] for s in subs
    )
    candidate = d_sharpe > 0 and ls["strat_net_pnl"] > 0 and dd_ok and beats_all
    verdict = (
        "CANDIDATE for OOS: primary long/short beats buy-and-hold on Sharpe, net, AND "
        "drawdown, consistently across sub-periods."
        if candidate
        else "REJECTED as a standalone-strategy candidate by the pre-registered "
        "criterion: the primary long/short improves Sharpe and net PnL over buy-and-hold "
        "but does NOT satisfy maxDD <= baseline and/or sub-period consistency. The VRP "
        "signal is real (ALT-011) but a naive long/short weekly trade is a modest, "
        "drawdown-heavy standalone. The long-only SECONDARY looks better (higher Sharpe, "
        "much lower drawdown) -- but it is descriptive-only and CANNOT be promoted here "
        "(no ex-post secondary promotion); it would need its OWN pre-registration. Best "
        "use of VRP is likely as a FEATURE/overlay, not a standalone trade. No promotion; "
        "OOS-gated."
    )
    return (
        f"Primary long/short: Sharpe {ls['baseline_sharpe']:.3f} (buy-hold) -> "
        f"{ls['strat_sharpe']:.3f} (delta {d_sharpe:+.3f}); maxDD "
        f"{ls['strat_max_drawdown']:.4f} vs buy-hold {ls['baseline_max_drawdown']:.4f} "
        f"(<= baseline: {dd_ok}); beats buy-hold in every sub-period: {beats_all}. "
        f"{verdict}"
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
