#!/usr/bin/env python3
"""Run the Sprint 10 passive/maker execution variant against the Sprint 9 baseline.

Replays the exact same causal signals, the exact same 13 Sprint 8
backtest-approved pairs, and the exact same checksum-verified June-2023 raw
bookTicker data already used in Sprint 9 (no new data is downloaded) through
TWO execution styles:

- ``MARKET_IOC``: the Sprint 9 baseline, rerun here unchanged as a
  regression check against ``sprint9_replay_results.json``.
- ``LIMIT_MAKER_TTL``: the Sprint 10 passive/maker variant recommended by
  the Execution/Risk Agent in ``reports/backtest_executable_v1.md`` and
  scoped by ``project_control/DECISIONS.md`` ADR-0011 -- a resting order
  quoted at the touch that never crosses the spread at placement and only
  fills if the market later crosses to it within the TTL.

Neither variant changes signal generation, gate policy, or promotes any pair
to paper/live trading. Both are fail-closed in the same categories as
Sprint 9: NO_QUOTE, EXPIRED/PARTIALLY_FILLED, leg-fill mismatch, and
unclosed residual quantity are all reported explicitly, never masked as
PnL.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import math
import numbers
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest.execution_simulator import ExecutionStyle  # noqa: E402
from src.backtest.fill_model import FillModelConfig  # noqa: E402
from src.backtest.replay_engine import ReplayConfig, replay_pair  # noqa: E402
from src.research.sprint8 import (  # noqa: E402
    WalkForwardSplitConfig,
    build_walk_forward_splits,
    load_sprint8_universe_contract,
)

METRIC_TOLERANCE = 1e-6
BASELINE_REPRODUCTION_EXIT_CODE = 2
_STATUS_KEYS = ("FILLED", "PARTIALLY_FILLED", "EXPIRED", "NO_QUOTE")


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
    fill_config = FillModelConfig(
        latency_ms=args.latency_ms,
        limit_ttl_ms=args.limit_ttl_ms,
        ack_unknown_rate=args.ack_unknown_rate,
        reconciliation_latency_ms=args.reconciliation_latency_ms,
    )
    pairs = tuple(args.pairs) if args.pairs else _backtest_approved_pairs(args.sprint8_results_json)

    variants: dict[str, dict[str, Any]] = {}
    for style in (ExecutionStyle.MARKET_IOC, ExecutionStyle.LIMIT_MAKER_TTL):
        replay_config = ReplayConfig(
            raw_root=args.raw_root,
            holding_period_ms=args.holding_period_ms,
            fill_config=fill_config,
            day_cache_size=args.day_cache_size,
            execution_style=style,
        )
        pair_rows = []
        for pair in pairs:
            print(f"[{style.value}] replaying {pair}...", file=sys.stderr)
            results = replay_pair(pair, bars, contract, folds, replay_config)
            pair_rows.append(_summarize_pair(pair, results))
            del results
            gc.collect()
        variants[style.value] = _variant_payload(style, pair_rows)

    baseline_reproduction = _check_baseline_reproduction(
        variants[ExecutionStyle.MARKET_IOC.value], args.sprint9_results_json
    )
    if baseline_reproduction["pass"] is False:
        print(
            "Baseline (MARKET_IOC) reproduction failed against "
            f"{args.sprint9_results_json}: {baseline_reproduction}",
            file=sys.stderr,
        )
        return BASELINE_REPRODUCTION_EXIT_CODE

    comparison = _compare_variants(
        variants[ExecutionStyle.MARKET_IOC.value],
        variants[ExecutionStyle.LIMIT_MAKER_TTL.value],
    )
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "evidence_scope": contract.evidence_scope,
        "methodology": {
            "fill_model": "level-1 top-of-book consumption via estimate_slippage",
            "market_ioc": "aggressive, crosses the spread immediately (Sprint 9 baseline)",
            "limit_maker_ttl": (
                "resting order quoted at the touch (best bid for BUY, best ask for SELL), "
                "never crosses the spread at placement, fills only if the market later "
                "crosses to it before limit_ttl_ms elapses"
            ),
            "latency_ms": args.latency_ms,
            "limit_ttl_ms": args.limit_ttl_ms,
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
        "baseline_reproduction": baseline_reproduction,
        "comparison": comparison,
        "variants": variants,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_pair_csv(args.output_csv, variants)
    console_summary = {
        "baseline_reproduction": baseline_reproduction,
        "comparison": comparison,
        "market_ioc_summary": variants[ExecutionStyle.MARKET_IOC.value]["summary"],
        "limit_maker_ttl_summary": variants[ExecutionStyle.LIMIT_MAKER_TTL.value]["summary"],
    }
    print(json.dumps(_json_ready(console_summary), allow_nan=False, indent=2, sort_keys=True))
    return 0


def _backtest_approved_pairs(sprint8_results_json: Path) -> tuple[str, ...]:
    """Return the 13 Sprint 8 backtest-approved pairs (same universe as Sprint 9)."""

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

    entry_fills = [fill for r in results for fill in (r.entry_fill_a, r.entry_fill_b)]
    exit_fills = [
        fill for r in results for fill in (r.exit_fill_a, r.exit_fill_b) if fill is not None
    ]
    entry_status = _status_counts(entry_fills)
    exit_status = _status_counts(exit_fills)
    ack_unknown_entries = sum(
        1 for fill in entry_fills if fill.ack_status.value == "ACK_UNKNOWN_UNRESOLVED"
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
        "entry_filled_leg_count": entry_status["FILLED"],
        "entry_partially_filled_leg_count": entry_status["PARTIALLY_FILLED"],
        "entry_expired_leg_count": entry_status["EXPIRED"],
        "entry_no_quote_leg_count": entry_status["NO_QUOTE"],
        "exit_filled_leg_count": exit_status["FILLED"],
        "exit_partially_filled_leg_count": exit_status["PARTIALLY_FILLED"],
        "exit_expired_leg_count": exit_status["EXPIRED"],
        "exit_no_quote_leg_count": exit_status["NO_QUOTE"],
        "unclosed_residual_quantity": unclosed_residual_quantity,
        "net_pnl_quote": net_pnl_quote,
        "status": "REALISTIC_NET_POSITIVE" if net_pnl_quote > 0.0 else "REALISTIC_NET_NEGATIVE",
    }


def _status_counts(fills: list[Any]) -> dict[str, int]:
    counts = dict.fromkeys(_STATUS_KEYS, 0)
    for fill in fills:
        counts[fill.status.value] += 1
    return counts


def _variant_payload(style: ExecutionStyle, pair_rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_signals = sum(row["signal_count"] for row in pair_rows)
    total_executed = sum(row["executed_count"] for row in pair_rows)
    total_net_pnl_quote = float(sum(row["net_pnl_quote"] for row in pair_rows))
    positive_pairs = [row["pair"] for row in pair_rows if row["net_pnl_quote"] > 0.0]
    return {
        "execution_style": style.value,
        "pair_rows": pair_rows,
        "summary": {
            "pairs_evaluated": len(pair_rows),
            "pairs_realistic_net_positive": len(positive_pairs),
            "pairs_realistic_net_positive_list": positive_pairs,
            "total_signals": total_signals,
            "total_executed_trades": total_executed,
            "total_net_pnl_quote": total_net_pnl_quote,
            "total_leg_fill_mismatch_count": sum(
                row["leg_fill_mismatch_count"] for row in pair_rows
            ),
            "total_unclosed_residual_quantity": float(
                sum(row["unclosed_residual_quantity"] for row in pair_rows)
            ),
            "total_entry_expired_leg_count": sum(
                row["entry_expired_leg_count"] for row in pair_rows
            ),
            "total_exit_expired_leg_count": sum(row["exit_expired_leg_count"] for row in pair_rows),
            "portfolio_gate_pass": total_net_pnl_quote > 0.0,
        },
    }


def _check_baseline_reproduction(
    market_ioc_variant: dict[str, Any],
    sprint9_results_json: Path,
) -> dict[str, Any]:
    """Confirm rerunning MARKET_IOC through this script reproduces Sprint 9 exactly.

    A mismatch here would mean the ``ExecutionStyle`` refactor of
    ``execution_simulator.py``/``replay_engine.py`` silently changed the
    MARKET_IOC path, not just added a new LIMIT_MAKER_TTL path -- so this is
    a hard regression gate, not a soft comparison.
    """

    if not sprint9_results_json.exists():
        return {
            "pass": None,
            "reason": f"reference file not found: {sprint9_results_json}",
        }
    reference = json.loads(sprint9_results_json.read_text(encoding="utf-8"))["summary"]
    rerun = market_ioc_variant["summary"]
    integer_metrics = ("total_signals", "total_executed_trades", "pairs_realistic_net_positive")
    metric_deltas = {metric: rerun[metric] - reference[metric] for metric in integer_metrics}
    pnl_delta = rerun["total_net_pnl_quote"] - reference["total_net_pnl_quote"]
    pass_check = all(delta == 0 for delta in metric_deltas.values()) and (
        abs(pnl_delta) <= METRIC_TOLERANCE
    )
    return {
        "pass": pass_check,
        "metric_deltas": metric_deltas,
        "total_net_pnl_quote_delta": pnl_delta,
        "reference_file": str(sprint9_results_json),
    }


def _compare_variants(market_ioc: dict[str, Any], limit_maker: dict[str, Any]) -> dict[str, Any]:
    ioc = market_ioc["summary"]
    passive = limit_maker["summary"]
    return {
        "total_net_pnl_quote_delta": (passive["total_net_pnl_quote"] - ioc["total_net_pnl_quote"]),
        "pairs_realistic_net_positive_delta": (
            passive["pairs_realistic_net_positive"] - ioc["pairs_realistic_net_positive"]
        ),
        "total_executed_trades_delta": (
            passive["total_executed_trades"] - ioc["total_executed_trades"]
        ),
        "total_leg_fill_mismatch_count_delta": (
            passive["total_leg_fill_mismatch_count"] - ioc["total_leg_fill_mismatch_count"]
        ),
        "total_unclosed_residual_quantity_delta": (
            passive["total_unclosed_residual_quantity"] - ioc["total_unclosed_residual_quantity"]
        ),
        "limit_maker_ttl_still_net_negative": passive["total_net_pnl_quote"] <= 0.0,
        "limit_maker_ttl_improves_on_market_ioc": (
            passive["total_net_pnl_quote"] > ioc["total_net_pnl_quote"]
        ),
    }


def _write_pair_csv(path: Path, variants: dict[str, dict[str, Any]]) -> None:
    rows: list[dict[str, Any]] = []
    for style_name, variant in variants.items():
        for row in variant["pair_rows"]:
            rows.append({"execution_style": style_name, **row})
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
        "(the 13 Sprint 8 backtest-approved pairs, same universe as Sprint 9).",
    )
    parser.add_argument(
        "--sprint9-results-json",
        type=Path,
        default=PROJECT_ROOT
        / "data/research/binance_public/cost_pilot/sprint9_replay_results.json",
        help="Sprint 9 aggregate result used to confirm the MARKET_IOC rerun "
        "reproduces Sprint 9 exactly before trusting the LIMIT_MAKER_TTL comparison.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=PROJECT_ROOT
        / "data/research/binance_public/cost_pilot/sprint10_passive_execution_variant_results.json",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=PROJECT_ROOT
        / (
            "data/research/binance_public/cost_pilot/"
            "sprint10_passive_execution_variant_pair_results.csv"
        ),
    )
    parser.add_argument("--train-bars", type=int, default=336)
    parser.add_argument("--test-bars", type=int, default=168)
    parser.add_argument("--step-bars", type=int, default=168)
    parser.add_argument("--holding-period-ms", type=int, default=60 * 60 * 1000)
    parser.add_argument("--latency-ms", type=int, default=250)
    parser.add_argument(
        "--limit-ttl-ms",
        type=int,
        default=60_000,
        help="How long a passive LIMIT_MAKER_TTL order rests before expiring. "
        "60s is a documented assumption (not calibrated against real production "
        "order-placement/cancel-replace telemetry), longer than fill_model.py's "
        "own 5s unit-test default, chosen to give the market a realistic chance "
        "to trade through the resting price instead of trivially expiring almost "
        "every order.",
    )
    parser.add_argument("--ack-unknown-rate", type=float, default=0.02)
    parser.add_argument("--reconciliation-latency-ms", type=int, default=2_000)
    parser.add_argument(
        "--day-cache-size",
        type=int,
        default=4,
        help="Max unique (symbol, day) decompressed archives held in memory at once "
        "(same memory-safety bound as Sprint 9's run_sprint9_replay.py).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
