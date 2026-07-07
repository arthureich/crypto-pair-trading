#!/usr/bin/env python3
"""Run the incremental (yield-threshold) funding-rate carry backtest (TASK-FUND-003).

Implements the hypothesis pre-registered in
`tasks/funding_carry/TASK-FUND-003-incremental-rebalancing.md`: same
universe, signal, and PnL sign convention as TASK-FUND-002 (fase 1), but a
held leg is only replaced when the swap's funding-rate improvement clears
`cost_bps_per_leg_roundtrip` -- no new tunable parameter beyond what
TASK-FUND-001 already pre-registered. Runs the same K grid (K=5 primary,
K=3/K=8 descriptive) on the same existing dataset -- no new data download.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import numbers
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.funding_carry import (  # noqa: E402
    FundingCarryConfig,
    run_incremental_funding_carry_backtest,
    summarize_funding_carry_backtest,
)

PRIMARY_K = 5
SECONDARY_KS = (3, 8)
EXPECTED_SYMBOL_COUNT = 20


def main() -> int:
    args = _parse_args()
    bars = pd.read_csv(
        args.bars_csv,
        usecols=["symbol", "open_time", "funding_rate_asof", "log_price"],
    )
    symbol_count = bars["symbol"].nunique()
    if symbol_count != EXPECTED_SYMBOL_COUNT:
        raise ValueError(
            f"expected {EXPECTED_SYMBOL_COUNT} symbols in {args.bars_csv}, got {symbol_count}"
        )

    variants = {}
    for k in (PRIMARY_K, *SECONDARY_KS):
        config = FundingCarryConfig(k=k)
        results = run_incremental_funding_carry_backtest(bars, config)
        summary = summarize_funding_carry_backtest(results, config)
        total_swaps = sum(r.swap_count for r in results)
        variants[k] = {
            "config": asdict(config),
            "summary": asdict(summary),
            "total_swap_count": total_swaps,
            "results": results,
        }

    primary = variants[PRIMARY_K]["summary"]
    gate_decision = "PASSA" if primary["profit_factor_gate_pass"] else "NAO_PASSA"

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "bars_csv": str(args.bars_csv),
        "primary_k": PRIMARY_K,
        "secondary_ks": list(SECONDARY_KS),
        "gate_decision": gate_decision,
        "variants": {
            str(k): {
                "config": v["config"],
                "summary": v["summary"],
                "total_swap_count": v["total_swap_count"],
            }
            for k, v in variants.items()
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_rebalance_csv(args.output_csv, variants)
    print(json.dumps(_json_ready(payload["variants"]), allow_nan=False, indent=2, sort_keys=True))
    print(f"gate_decision (K={PRIMARY_K}, primary): {gate_decision}", file=sys.stderr)
    print(f"Wrote {args.output_json}", file=sys.stderr)
    print(f"Wrote {args.output_csv}", file=sys.stderr)
    return 0


def _write_rebalance_csv(path: Path, variants: dict[int, dict[str, Any]]) -> None:
    rows = []
    for k, variant in variants.items():
        for result in variant["results"]:
            rows.append(
                {
                    "k": k,
                    "rebalance_time": result.rebalance_time,
                    "status": result.status.value,
                    "held_long": "|".join(result.held_long),
                    "held_short": "|".join(result.held_short),
                    "swap_count": result.swap_count,
                    "funding_pnl_bps": result.funding_pnl_bps,
                    "price_pnl_bps": result.price_pnl_bps,
                    "cost_bps": result.cost_bps,
                    "gross_pnl_bps": result.gross_pnl_bps,
                    "net_pnl_bps": result.net_pnl_bps,
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = tuple(rows[0].keys()) if rows else ()
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, bool | str):
        return value
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bars-csv",
        type=Path,
        default=PROJECT_ROOT
        / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PROJECT_ROOT
        / "data/research/binance_public/cost_pilot/funding_carry_incremental_results.json",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=PROJECT_ROOT
        / "data/research/binance_public/cost_pilot/funding_carry_incremental_rebalance_results.csv",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
