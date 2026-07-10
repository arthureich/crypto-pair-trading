#!/usr/bin/env python3
"""TASK-FC-II-001 development run: risk-based position sizing vs equal weight.

Per `docs/pre_registers/TASK-FC-II-001.md` / ADR-0027. Reports risk-adjusted
metrics (Sharpe, max drawdown) of the inverse-vol + vol-targeting overlay
against the equal-weight K=5 baseline, on the EXISTING development window.

NO promotion verdict: the pre-registered gate is on untouched OOS. This run
is descriptive only -- if the overlay does not even improve risk-adjusted
metrics in development, the prior for it clearing the OOS gate is low.
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

from src.research.funding_carry import FundingCarryConfig  # noqa: E402
from src.research.position_sizing import (  # noqa: E402
    run_risk_sized_backtest,
    summarize_risk_sized,
)

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = (
    PROJECT_ROOT / "data/research/binance_public/cost_pilot/fc_position_sizing_dev_results.json"
)
REPORT_MD = PROJECT_ROOT / "reports/fc_position_sizing_dev.md"
PRIMARY_K = 5


def main() -> int:
    bars = pd.read_csv(
        BARS_CSV, usecols=["symbol", "open_time", "log_price", "quote_volume", "funding_rate_asof"]
    )
    config = FundingCarryConfig(k=PRIMARY_K)
    summary = summarize_risk_sized(run_risk_sized_backtest(bars, config), config)

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-FC-II-001",
        "phase": "DEVELOPMENT: risk-adjusted metrics only; NO verdict (gate blocked until OOS)",
        "primary_k": PRIMARY_K,
        "summary": asdict(summary),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(summary)

    print(
        f"baseline Sharpe={summary.baseline_sharpe:.3f} / sized Sharpe={summary.sized_sharpe:.3f}; "
        f"baseline maxDD={summary.baseline_max_drawdown_bps:.0f}bps / "
        f"sized maxDD={summary.sized_max_drawdown_bps:.0f}bps "
        f"({summary.n_rebalances} rebalances)",
        file=sys.stderr,
    )
    print("NO VERDICT -- development window; gate blocked until OOS (ADR-0027).", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _write_report(summary: object) -> None:
    s = summary  # type: ignore[assignment]
    lines = [
        "# TASK-FC-II-001 -- Risk-Based Position Sizing (development)",
        "",
        "Per `docs/pre_registers/TASK-FC-II-001.md` / ADR-0027. **Development "
        "window, NO verdict.** Inverse-vol weighting within side + whole-book "
        "vol-targeting (self-referential), overlay on the unchanged K=5 signal. "
        "Uniform vol-targeting is PF-invariant, so this targets Sharpe / max "
        "drawdown, not PF. The promotion gate is on untouched OOS.",
        "",
        "## Development metrics (equal-weight baseline vs sized)",
        "",
        "| Metric | Baseline (1/2K) | Sized (inverse-vol + vol-target) |",
        "|---|---:|---:|",
        f"| Net PnL (bps) | {s.baseline_net_pnl_bps:.1f} | {s.sized_net_pnl_bps:.1f} |",
        f"| Sharpe (annualized) | {s.baseline_sharpe:.3f} | {s.sized_sharpe:.3f} |",
        f"| Max drawdown (bps) | {s.baseline_max_drawdown_bps:.0f} | "
        f"{s.sized_max_drawdown_bps:.0f} |",
        f"| Rebalances | {s.n_rebalances} | {s.n_rebalances} |",
        "",
        "## Interpretation limits",
        "",
        "These are in-development numbers on the SAME window the K=5 near-miss "
        "was found on -- not evidence and not a gate. Sizing cannot create edge; "
        "if the base signal is noise, better sizing only reshapes the variance of "
        "losing. The admissible test is the pre-registered OOS gate: sized Sharpe "
        ">= baseline + 0.15 AND max drawdown not worse, on >= 500 untouched-OOS "
        "rebalances.",
        "",
    ]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, bool | str | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
