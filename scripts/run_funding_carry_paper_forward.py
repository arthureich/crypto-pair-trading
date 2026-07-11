#!/usr/bin/env python3
"""Funding-carry K=5 forward paper-validation track (ADR-0027).

Runs the FIXED, pre-registered incremental K=5 policy on data that accrues
AFTER the development cutoff (2026-05-31) and records its genuine out-of-
sample performance. As more monthly files are downloaded they are appended
and the track grows.

This is MONITORING, not a verdict: a promotion decision follows the pre-
registered gate only once >= 500 OOS rebalances have accrued. A single short
window is noisy on its own; the value is the accumulating record.
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
from src.research.paper_forward import (  # noqa: E402
    assemble_oos_bars,
    summarize_forward_track,
)

NORMALIZED_DIR = PROJECT_ROOT / "data/research/binance_public/normalized"
# Post-cutoff monthly OOS files (add more here as they are downloaded).
OOS_BAR_FILES = (NORMALIZED_DIR / "sprint_alt_funding_divergence_202606_bars.csv.gz",)
OUTPUT_JSON = (
    PROJECT_ROOT / "data/research/binance_public/cost_pilot/funding_carry_paper_forward.json"
)
REPORT_MD = PROJECT_ROOT / "reports/funding_carry_paper_forward.md"
PRIMARY_K = 5
_USECOLS = ["symbol", "open_time", "log_price", "quote_volume", "funding_rate_asof"]


def main() -> int:
    present = [path for path in OOS_BAR_FILES if path.exists()]
    if not present:
        print("No post-cutoff OOS bar files found yet; nothing to record.", file=sys.stderr)
        return 0

    frames = [pd.read_csv(path, usecols=_USECOLS) for path in present]
    bars = assemble_oos_bars(frames)
    summary = summarize_forward_track(bars, FundingCarryConfig(k=PRIMARY_K))

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "funding-carry K=5 forward paper track (ADR-0027)",
        "phase": "MONITORING: genuine OOS accruing; verdict only at >= trigger rebalances",
        "primary_k": PRIMARY_K,
        "oos_files": [str(p) for p in present],
        "summary": asdict(summary),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(summary)

    verdict = (
        "MEETS TRIGGER (run the pre-registered gate)"
        if summary.meets_trigger
        else (
            f"accruing -- {summary.rebalances_remaining_to_trigger} rebalances to the "
            f"{summary.trigger_rebalances} trigger"
        )
    )
    print(
        f"OOS funding carry K=5: PF={summary.profit_factor:.4f}, "
        f"net={summary.net_pnl_bps:.1f}bps, hit={summary.hit_rate:.3f}, "
        f"{summary.resolved_rebalances} rebalances [{verdict}]",
        file=sys.stderr,
    )
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _write_report(summary: object) -> None:
    s = summary  # type: ignore[assignment]
    status = "MEETS TRIGGER" if s.meets_trigger else "ACCRUING (below trigger)"
    lines = [
        "# Funding Carry K=5 -- Forward Paper Track (genuine OOS)",
        "",
        "Per ADR-0027. The FIXED, pre-registered incremental K=5 policy run on "
        "data AFTER the 2026-05-31 development cutoff -- genuine out-of-sample, "
        "since the signal was frozen before this data existed. **Monitoring, not "
        "a verdict**: the pre-registered gate is evaluated only once the trigger "
        "count of OOS rebalances has accrued.",
        "",
        "## OOS track so far",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Resolved OOS rebalances | {s.resolved_rebalances} |",
        f"| Trigger (for a verdict) | {s.trigger_rebalances} |",
        f"| Remaining to trigger | {s.rebalances_remaining_to_trigger} |",
        f"| Net PnL (bps) | {s.net_pnl_bps:.1f} |",
        f"| Profit factor | {s.profit_factor:.4f} |",
        f"| Hit rate | {s.hit_rate:.4f} |",
        f"| Status | {status} |",
        "",
        "## Reading this honestly",
        "",
        "A single short window is noisy: a real edge can miss it and a fake one "
        "can pass it. Do NOT read the current PF as a verdict -- it is one small "
        "sample. The point is the accumulating record: survive a growing sequence "
        "of independent OOS periods and the 'it was just luck' explanation gets "
        "progressively harder. The base-signal gate stays at profit factor "
        ">= 1.10 on the accrued OOS once the trigger count is reached.",
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
