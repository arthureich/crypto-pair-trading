#!/usr/bin/env python3
"""TASK-ALT-013: VRP-as-overlay on the TSM -- equal-risk blend dev run (ADR-0032).

DEVELOPMENT ONLY -- promotion OOS-gated. Tests the ALT-012 conclusion that VRP is
best used as a FEATURE/overlay: blends the TSM (trend, 20 perps) weekly return
stream with the VRP-timing (BTC/ETH, primary long/short) weekly stream, equal-
risk, and asks whether adding VRP improves the TSM's risk-adjusted return --
reusing the Line-5 (trend+carry) blend diagnostic.
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

from src.research.tsm_ensemble import blend_diagnostic, weekly_pnl  # noqa: E402
from src.research.tsm_trend import TsmTrendConfig, run_tsm_trend_backtest  # noqa: E402
from src.research.vrp_timing import (  # noqa: E402
    VrpTimingConfig,
    compute_vrp_z,
    run_vrp_timing_backtest,
)

DVOL_CSV = (
    PROJECT_ROOT / "data/research/binance_public/normalized/sprint_alt_dvol_202306_202605.csv.gz"
)
BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/alt_vrp_tsm_overlay_dev.json"
REPORT_MD = PROJECT_ROOT / "reports/alt_vrp_tsm_overlay_dev.md"
_PERIOD_EDGES = ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
_PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
_ASSETS = ("btc", "eth")


def main() -> int:
    bars = pd.read_csv(
        BARS_CSV,
        usecols=[
            "symbol",
            "base_asset",
            "open_time",
            "log_price",
            "funding_rate_asof",
            "funding_interval_hours",
        ],
    )
    tsm = run_tsm_trend_backtest(bars, TsmTrendConfig(include_funding=True))
    tsm_weekly = weekly_pnl(list(tsm.rebalance_times), list(tsm.tsm_net))

    price, vrp_z = _vrp_panels(bars)
    vrp = run_vrp_timing_backtest(price, vrp_z, VrpTimingConfig())
    vrp_weekly = weekly_pnl(list(vrp.rebalance_times), list(vrp.strat_net))

    overall = blend_diagnostic(tsm_weekly, vrp_weekly)
    edges = _edges_ms()
    sub = []
    for i, label in enumerate(_PERIOD_LABELS):
        lo, hi = edges[i], edges[i + 1]
        sub.append({"period": label, "summary": _try(tsm_weekly, vrp_weekly, lo, hi)})

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-ALT-013 VRP-as-overlay on TSM dev run (ADR-0032) -- DEVELOPMENT",
        "overall": asdict(overall),
        "sub_periods": sub,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)
    print(
        f"tsm {overall.tsm_sharpe:.3f} | vrp {overall.carry_sharpe:.3f} | "
        f"blend {overall.blend_sharpe:.3f} | corr {overall.correlation:+.3f} "
        f"(n={overall.n_weeks})",
        file=sys.stderr,
    )
    print(f"Wrote {OUTPUT_JSON}\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


def _vrp_panels(bars: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    b = bars[bars["base_asset"].str.lower().isin(_ASSETS)].copy()
    b["base_asset"] = b["base_asset"].str.lower()
    b["day"] = pd.to_datetime(b["open_time"], unit="ms", utc=True).dt.floor("D")
    daily = (
        b.sort_values("open_time", kind="mergesort")
        .groupby(["base_asset", "day"], as_index=False)
        .last()
    )
    price = daily.pivot(index="day", columns="base_asset", values="log_price").sort_index()
    price.index = [int(pd.Timestamp(d).timestamp() * 1000) for d in price.index]

    dvol = pd.read_csv(DVOL_CSV, parse_dates=["day"])
    dvol_wide = dvol.pivot(index="day", columns="asset", values="dvol_close")
    dvol_wide.index = [int(pd.Timestamp(d).timestamp() * 1000) for d in dvol_wide.index]
    dvol_wide = dvol_wide.reindex(index=price.index, columns=price.columns)
    return price, compute_vrp_z(dvol_wide, price, VrpTimingConfig())


def _edges_ms() -> tuple[int, ...]:
    return tuple(int(pd.Timestamp(d, tz="UTC").timestamp() * 1000) for d in _PERIOD_EDGES)


def _try(tsm_weekly: pd.Series, vrp_weekly: pd.Series, lo: int, hi: int) -> dict | None:
    def win(s: pd.Series) -> pd.Series:
        idx = [pd.Timestamp(lo, unit="ms"), pd.Timestamp(hi, unit="ms")]
        return s[(s.index >= idx[0]) & (s.index < idx[1])]

    try:
        return asdict(blend_diagnostic(win(tsm_weekly), win(vrp_weekly)))
    except Exception:  # noqa: BLE001 -- too few overlapping weeks in a sub-period
        return None


def _write_report(payload: dict) -> None:
    o = payload["overall"]
    lines = [
        "# TASK-ALT-013 -- VRP-as-Overlay on the TSM (DEVELOPMENT, no verdict)",
        "",
        "Per `docs/pre_registers/TASK-ALT-013.md` (ADR-0032). Equal-risk 50/50 blend of "
        "the TSM (trend, 20 perps) and VRP-timing (BTC/ETH, primary long/short) weekly "
        "return streams -- testing the ALT-012 conclusion that VRP is best used as a "
        "diversifying FEATURE/overlay, not a standalone trade. **Development result -- "
        "NOT a promotion; OOS-gated.**",
        "",
        "## Overall (full dev window, weekly)",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Overlapping weeks | {o['n_weeks']} |",
        f"| TSM Sharpe | {o['tsm_sharpe']:.3f} |",
        f"| VRP Sharpe | {o['carry_sharpe']:.3f} |",
        f"| **Blend Sharpe** | **{o['blend_sharpe']:.3f}** |",
        f"| Stream correlation | {o['correlation']:+.3f} |",
        f"| TSM max drawdown (risk units) | {o['tsm_max_drawdown']:.3f} |",
        f"| Blend max drawdown (risk units) | {o['blend_max_drawdown']:.3f} |",
        "",
        "## Sub-period (Sharpe: TSM / VRP / Blend; corr)",
        "",
        "| Period | TSM | VRP | Blend | Corr |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in payload["sub_periods"]:
        s = row["summary"]
        if s is None:
            lines.append(f"| {row['period']} | n/a | n/a | n/a | n/a |")
        else:
            lines.append(
                f"| {row['period']} | {s['tsm_sharpe']:.3f} | {s['carry_sharpe']:.3f} | "
                f"{s['blend_sharpe']:.3f} | {s['correlation']:+.3f} |"
            )
    lines += ["", "## Reading", "", _reading(payload), ""]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _reading(payload: dict) -> str:
    o = payload["overall"]
    d = o["blend_sharpe"] - o["tsm_sharpe"]
    subs = [r["summary"] for r in payload["sub_periods"] if r["summary"] is not None]
    beats_all = bool(subs) and all(s["blend_sharpe"] > s["tsm_sharpe"] for s in subs)
    dd_ok = o["blend_max_drawdown"] <= o["tsm_max_drawdown"]
    verdict = (
        "CANDIDATE for OOS: adding VRP as an equal-risk overlay improves the TSM's "
        "Sharpe overall AND in every sub-period, low correlation, drawdown not worse."
        if (d > 0 and beats_all and dd_ok)
        else "REJECTED as a dev candidate: adding VRP as an overlay does not "
        "consistently improve the TSM's risk-adjusted return. The VRP signal is real "
        "(ALT-011) but does not lift the perp book as a diversifying sleeve either. "
        "Closes the free VRP exploration; remaining options avenues (skew/surface, "
        "Angle-A options book) are user decisions. No promotion; OOS-gated."
    )
    return (
        f"Blend vs TSM Sharpe: {o['tsm_sharpe']:.3f} -> {o['blend_sharpe']:.3f} "
        f"(delta {d:+.3f}); VRP sleeve Sharpe {o['carry_sharpe']:.3f}; correlation "
        f"{o['correlation']:+.3f}. Blend beats TSM in every sub-period: {beats_all}; "
        f"drawdown not worse: {dd_ok}. {verdict}"
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
