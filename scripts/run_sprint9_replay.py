#!/usr/bin/env python3
"""Run the Sprint 9 executable backtest: realistic fill simulation replay.

Consumes only already-downloaded, checksum-verified raw bookTicker archives
(no new network access) and the same causal signals already reviewed in
Sprint 8. Writes per-pair and aggregate results comparing the realistic
execution outcome against the Sprint 8 idealized assumption.
"""

from __future__ import annotations

import argparse
import csv
import gc
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

from src.backtest.fill_model import FillModelConfig  # noqa: E402
from src.backtest.replay_engine import ReplayConfig, replay_pair  # noqa: E402
from src.research.sprint8 import (  # noqa: E402
    WalkForwardSplitConfig,
    build_walk_forward_splits,
    load_sprint8_universe_contract,
)


def main() -> int:
    args = _parse_args()
    contract = load_sprint8_universe_contract(args.contract_json)
    bars = pd.read_csv(args.bars_csv, low_memory=False)
    folds = build_walk_forward_splits(
        bars,
        WalkForwardSplitConfig(
            train_bars=args.train_bars,
            test_bars=args.test_bars,
            step_bars=args.step_bars,
        ),
    )
    replay_config = ReplayConfig(
        raw_root=args.raw_root,
        holding_period_ms=args.holding_period_ms,
        fill_config=FillModelConfig(
            latency_ms=args.latency_ms,
            limit_ttl_ms=args.limit_ttl_ms,
            ack_unknown_rate=args.ack_unknown_rate,
            reconciliation_latency_ms=args.reconciliation_latency_ms,
        ),
        day_cache_size=args.day_cache_size,
    )

    pairs = tuple(args.pairs) if args.pairs else _backtest_approved_pairs(args.sprint8_results_json)
    pair_rows = []
    for pair in pairs:
        print(f"replaying {pair}...", file=sys.stderr)
        results = replay_pair(pair, bars, contract, folds, replay_config)
        pair_rows.append(_summarize_pair(pair, results))
        del results
        gc.collect()

    payload = _payload(args=args, contract=contract, folds=folds, pair_rows=pair_rows)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_pair_csv(args.output_csv, pair_rows)
    print(json.dumps(_json_ready(payload["summary"]), allow_nan=False, indent=2, sort_keys=True))
    return 0


def _backtest_approved_pairs(sprint8_results_json: Path) -> tuple[str, ...]:
    """Return the 13 Sprint 8 backtest-approved pairs, not the full 31-pair cost-gated universe.

    Sprint 9 replays realistic execution for the pairs that already survived
    Sprint 8's idealized cost-aware backtest -- not every pair that merely
    passed the June-2023 cost gate. Defaulting to ``contract.approved_pairs``
    (31 pairs, including BTCUSDT/ETHUSDT and other high-volume symbols never
    intended for this replay) caused an out-of-memory kill in an earlier run.
    """

    if not sprint8_results_json.exists():
        raise FileNotFoundError(
            f"Sprint 8 backtest results not found: {sprint8_results_json}. "
            "Pass --pairs explicitly or --sprint8-results-json with a valid path."
        )
    payload = json.loads(sprint8_results_json.read_text(encoding="utf-8"))
    pairs = tuple(payload["summary"]["backtest_approved_pairs"])
    if not pairs:
        raise ValueError(f"no backtest_approved_pairs found in {sprint8_results_json}")
    return pairs


def _summarize_pair(pair: str, results: tuple[Any, ...]) -> dict[str, Any]:
    trade_count = len(results)
    executed = [r for r in results if r.status.value == "EXECUTED"]
    no_entry_fill = [r for r in results if r.status.value == "NO_ENTRY_FILL"]
    no_exit_fill = [r for r in results if r.status.value == "NO_EXIT_FILL"]
    leg_mismatch = [r for r in results if r.leg_fill_mismatch]
    ack_unknown_entries = sum(
        1
        for r in results
        for fill in (r.entry_fill_a, r.entry_fill_b)
        if fill.ack_status.value == "ACK_UNKNOWN_UNRESOLVED"
    )
    partial_entry = sum(
        1
        for r in results
        for fill in (r.entry_fill_a, r.entry_fill_b)
        if fill.status.value == "PARTIALLY_FILLED"
    )
    no_quote_entry = sum(
        1
        for r in results
        for fill in (r.entry_fill_a, r.entry_fill_b)
        if fill.status.value == "NO_QUOTE"
    )
    # A partially-filled EXIT leg leaves a residual, un-marked-to-market open
    # position (see reports/backtest_executable_v1.md "Leg Risk"): the entry
    # leg's full quantity was not actually closed out, so net_pnl_quote for
    # that trade understates real exposure. Track this separately from entry
    # partial fills so it is never invisible in the aggregate summary.
    partial_exit = sum(
        1
        for r in results
        for fill in (r.exit_fill_a, r.exit_fill_b)
        if fill is not None and fill.status.value == "PARTIALLY_FILLED"
    )
    leg_pairs = [
        (entry, exit_fill)
        for r in results
        for entry, exit_fill in ((r.entry_fill_a, r.exit_fill_a), (r.entry_fill_b, r.exit_fill_b))
    ]
    unclosed_residual_quantity = float(
        sum(
            max(0.0, entry.filled_quantity - (exit_fill.filled_quantity if exit_fill else 0.0))
            for entry, exit_fill in leg_pairs
        )
    )
    net_pnl_quote = float(sum(r.net_pnl_quote for r in executed))
    return {
        "pair": pair,
        "signal_count": trade_count,
        "executed_count": len(executed),
        "no_entry_fill_count": len(no_entry_fill),
        "no_exit_fill_count": len(no_exit_fill),
        "leg_fill_mismatch_count": len(leg_mismatch),
        "ack_unknown_entry_leg_count": ack_unknown_entries,
        "partially_filled_entry_leg_count": partial_entry,
        "partially_filled_exit_leg_count": partial_exit,
        "unclosed_residual_quantity": unclosed_residual_quantity,
        "no_quote_entry_leg_count": no_quote_entry,
        "net_pnl_quote": net_pnl_quote,
        "status": "REALISTIC_NET_POSITIVE" if net_pnl_quote > 0.0 else "REALISTIC_NET_NEGATIVE",
    }


def _payload(
    *,
    args: argparse.Namespace,
    contract: Any,
    folds: tuple[Any, ...],
    pair_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    total_signals = sum(row["signal_count"] for row in pair_rows)
    total_executed = sum(row["executed_count"] for row in pair_rows)
    total_net_pnl_quote = float(sum(row["net_pnl_quote"] for row in pair_rows))
    positive_pairs = [row["pair"] for row in pair_rows if row["net_pnl_quote"] > 0.0]
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "evidence_scope": contract.evidence_scope,
        "methodology": {
            "fill_model": "level-1 top-of-book consumption via estimate_slippage",
            "order_type": "MARKET_IOC",
            "latency_ms": args.latency_ms,
            "ack_unknown_rate": args.ack_unknown_rate,
            "reconciliation_latency_ms": args.reconciliation_latency_ms,
            "holding_period_ms": args.holding_period_ms,
            "walk_forward": {
                "fold_count": len(folds),
                "train_bars": args.train_bars,
                "test_bars": args.test_bars,
                "step_bars": args.step_bars,
            },
        },
        "summary": {
            "pairs_evaluated": len(pair_rows),
            "pairs_realistic_net_positive": len(positive_pairs),
            "pairs_realistic_net_positive_list": positive_pairs,
            "total_signals": total_signals,
            "total_executed_trades": total_executed,
            "total_net_pnl_quote": total_net_pnl_quote,
            "portfolio_gate_pass": total_net_pnl_quote > 0.0,
        },
        "folds": [asdict(fold) for fold in folds],
        "pair_results": pair_rows,
    }


def _write_pair_csv(path: Path, pair_rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = tuple(pair_rows[0].keys()) if pair_rows else ()
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in pair_rows:
            writer.writerow(row)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
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
        "--contract-json",
        type=Path,
        default=PROJECT_ROOT / "project_control/SPRINT8_UNIVERSE.json",
    )
    parser.add_argument(
        "--bars-csv",
        type=Path,
        default=PROJECT_ROOT
        / "data/research/binance_public/cost_pilot/all_candidates_202306_bars.csv",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=PROJECT_ROOT / "data/research/binance_public/cost_pilot/raw",
    )
    parser.add_argument("--pairs", nargs="*", default=None)
    parser.add_argument(
        "--sprint8-results-json",
        type=Path,
        default=PROJECT_ROOT
        / "data/research/binance_public/cost_pilot/sprint8_backtest_results.json",
        help="Source of the default pair list when --pairs is omitted "
        "(the 13 Sprint 8 backtest-approved pairs, not the full 31-pair cost-gated universe).",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PROJECT_ROOT
        / "data/research/binance_public/cost_pilot/sprint9_replay_results.json",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=PROJECT_ROOT
        / "data/research/binance_public/cost_pilot/sprint9_replay_pair_results.csv",
    )
    parser.add_argument("--train-bars", type=int, default=336)
    parser.add_argument("--test-bars", type=int, default=168)
    parser.add_argument("--step-bars", type=int, default=168)
    parser.add_argument("--holding-period-ms", type=int, default=60 * 60 * 1000)
    parser.add_argument("--latency-ms", type=int, default=250)
    parser.add_argument("--limit-ttl-ms", type=int, default=5_000)
    parser.add_argument("--ack-unknown-rate", type=float, default=0.02)
    parser.add_argument("--reconciliation-latency-ms", type=int, default=2_000)
    parser.add_argument(
        "--day-cache-size",
        type=int,
        default=4,
        help="Max unique (symbol, day) decompressed archives held in memory at once. "
        "Keep this small: a single busy day for a symbol like ETHUSDT can be "
        "several million tick rows.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
