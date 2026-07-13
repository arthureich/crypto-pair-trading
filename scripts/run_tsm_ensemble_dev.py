#!/usr/bin/env python3
"""TASK-TSM-005: trend + carry ensemble dev run (ADR-0031, Line 5).

DEVELOPMENT ONLY -- no promotion verdict (OOS-gated; carry already printed a
negative first OOS month). Blends the vol-targeted TSM (trend) with the
funding-carry K=5 incremental (carry) as two return streams: aggregate each to
weekly P&L, standardize to unit risk, combine equal-risk (50/50), and compare
the blend's Sharpe to the TSM alone -- overall and per sub-period. The question
is strictly whether ADDING carry improves the TSM's risk-adjusted return.
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

from src.research.funding_carry import (  # noqa: E402
    FundingCarryConfig,
    run_incremental_funding_carry_backtest,
)
from src.research.tsm_ensemble import blend_diagnostic, weekly_pnl  # noqa: E402
from src.research.tsm_trend import TsmTrendConfig, run_tsm_trend_backtest  # noqa: E402

BARS = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/tsm_ensemble_dev.json"
REPORT_MD = PROJECT_ROOT / "reports/tsm_ensemble_dev.md"
_PERIOD_EDGES = ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
_PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")


def main() -> int:
    bars = pd.read_csv(BARS)
    tsm = run_tsm_trend_backtest(bars, TsmTrendConfig(include_funding=True))
    tsm_weekly = weekly_pnl(list(tsm.rebalance_times), list(tsm.tsm_net))

    carry = run_incremental_funding_carry_backtest(bars, FundingCarryConfig(k=5))
    carry_weekly = weekly_pnl([r.rebalance_time for r in carry], [r.net_pnl_bps for r in carry])

    overall = blend_diagnostic(tsm_weekly, carry_weekly)
    edges = _edges_ms()
    sub = []
    for i, label in enumerate(_PERIOD_LABELS):
        lo, hi = edges[i], edges[i + 1]
        t = _slice_weeks(tsm_weekly, lo, hi)
        c = _slice_weeks(carry_weekly, lo, hi)
        sub.append({"period": label, "summary": _try_blend(t, c)})

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-TSM-005 trend+carry ensemble dev run (ADR-0031) -- DEVELOPMENT",
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
        f"overall: tsm {overall.tsm_sharpe:.3f} | carry {overall.carry_sharpe:.3f} | "
        f"blend {overall.blend_sharpe:.3f} | corr {overall.correlation:+.3f} "
        f"(n={overall.n_weeks})",
        file=sys.stderr,
    )
    print(f"Wrote {OUTPUT_JSON}\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


def _edges_ms() -> tuple[int, ...]:
    return tuple(int(pd.Timestamp(d, tz="UTC").timestamp() * 1000) for d in _PERIOD_EDGES)


def _slice_weeks(weekly: pd.Series, lo_ms: int, hi_ms: int) -> pd.Series:
    lo = pd.Timestamp(lo_ms, unit="ms")
    hi = pd.Timestamp(hi_ms, unit="ms")
    return weekly[(weekly.index >= lo) & (weekly.index < hi)]


def _try_blend(tsm: pd.Series, carry: pd.Series) -> dict | None:
    try:
        return asdict(blend_diagnostic(tsm, carry))
    except Exception:  # noqa: BLE001 -- too few overlapping weeks in a sub-period
        return None


def _write_report(payload: dict) -> None:
    o = payload["overall"]
    lines = [
        "# TASK-TSM-005 -- Trend + Carry Ensemble Dev Run (DEVELOPMENT, no verdict)",
        "",
        "Per `docs/pre_registers/TASK-TSM-005.md` (ADR-0031, Line 5). Equal-risk "
        "50/50 blend of two weekly return streams -- the vol-targeted TSM (trend) and "
        "the funding-carry K=5 incremental (carry), the canonical diversifying CTA "
        "sources. Streams standardized to unit risk (scale-invariant). "
        "**Development-window result -- NOT a promotion; OOS-gated (carry already "
        "printed a negative first OOS month).** The question: does ADDING carry beat "
        "the TSM alone, consistently, with low stream correlation?",
        "",
        "## Overall (full dev window, weekly)",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Overlapping weeks | {o['n_weeks']} |",
        f"| TSM Sharpe | {o['tsm_sharpe']:.3f} |",
        f"| Carry Sharpe | {o['carry_sharpe']:.3f} |",
        f"| **Blend Sharpe** | **{o['blend_sharpe']:.3f}** |",
        f"| Stream correlation | {o['correlation']:+.3f} |",
        f"| TSM max drawdown (risk units) | {o['tsm_max_drawdown']:.3f} |",
        f"| Blend max drawdown (risk units) | {o['blend_max_drawdown']:.3f} |",
        "",
        "## Sub-period stability (Sharpe: TSM / Carry / Blend; corr)",
        "",
        "| Period | TSM | Carry | Blend | Corr |",
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
    dd_better = o["blend_max_drawdown"] <= o["tsm_max_drawdown"]
    verdict = (
        "CANDIDATE for OOS: the blend beats the TSM alone overall AND in every "
        "sub-period, with low stream correlation and no worse drawdown."
        if (d > 0 and beats_all and dd_better)
        else "REJECTED as a dev candidate: adding carry does not consistently improve "
        "the TSM's risk-adjusted return (blend Sharpe > TSM in every sub-period, low "
        "correlation, drawdown not worse). Documented and closed; proceed to Line 6 "
        "(execution). Gate BLOCKED until OOS regardless (carry's own OOS is negative)."
    )
    return (
        f"Blend vs TSM Sharpe: {o['tsm_sharpe']:.3f} -> {o['blend_sharpe']:.3f} "
        f"(delta {d:+.3f}); stream correlation {o['correlation']:+.3f}; carry Sharpe "
        f"{o['carry_sharpe']:.3f}. Blend beats TSM in every sub-period: {beats_all}; "
        f"drawdown not worse: {dd_better}. {verdict}"
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
