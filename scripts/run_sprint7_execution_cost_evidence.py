#!/usr/bin/env python3
"""Review Sprint 7 historical execution-cost evidence and cost-gate pairs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import numbers
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.execution_cost_evidence import (  # noqa: E402
    HOURLY_COST_COLUMNS,
    S3_LIST_ENDPOINT,
    ExecutionCostGateConfig,
    build_unavailable_source_review,
    evaluate_execution_cost_gate,
    parse_s3_list_objects,
    summarize_book_ticker_source,
)

DEFAULT_START_MONTH = "2023-06"
DEFAULT_END_MONTH_EXCLUSIVE = "2026-06"


def main() -> int:
    args = _parse_args()
    bars = pd.read_csv(args.bars_csv, low_memory=False)
    summary = json.loads(args.summary_json.read_text(encoding="utf-8"))
    candidate_pairs = _candidate_pairs(summary)
    symbols = _symbols_for_review(summary, candidate_pairs)
    source_review = _source_review(args, symbols)
    hourly_cost = (
        pd.read_csv(args.cost_hourly_csv, low_memory=False)
        if args.cost_hourly_csv is not None
        else pd.DataFrame(columns=HOURLY_COST_COLUMNS)
    )
    gate = evaluate_execution_cost_gate(
        bars,
        candidate_pairs,
        hourly_cost,
        config=ExecutionCostGateConfig(expected_bars=int(summary.get("expected_bars", 26_304))),
    )
    payload = _payload(args, summary, source_review, gate, hourly_cost)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    json_payload = _json_ready(payload)
    args.output_json.write_text(
        json.dumps(json_payload, allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_pair_csv(args.output_csv, gate["pair_cost_results"])
    print(json.dumps(json_payload, allow_nan=False, indent=2, sort_keys=True))
    return 0


def _source_review(args: argparse.Namespace, symbols: tuple[str, ...]) -> dict[str, Any]:
    if args.source_review_json is not None:
        return json.loads(args.source_review_json.read_text(encoding="utf-8"))
    if not args.probe_binance_source:
        return build_unavailable_source_review(
            symbols,
            start_month=args.start_month,
            end_month_exclusive=args.end_month_exclusive,
            reason="no historical execution-cost source review was supplied",
        )
    try:
        review = _probe_binance_book_ticker_source(
            symbols,
            start_month=args.start_month,
            end_month_exclusive=args.end_month_exclusive,
            timeout_seconds=args.timeout_seconds,
        )
    except OSError as exc:
        review = build_unavailable_source_review(
            symbols,
            start_month=args.start_month,
            end_month_exclusive=args.end_month_exclusive,
            reason=f"network probe failed: {exc}",
        )
    if args.source_review_output_json is not None:
        args.source_review_output_json.parent.mkdir(parents=True, exist_ok=True)
        args.source_review_output_json.write_text(
            json.dumps(_json_ready(review), allow_nan=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return review


def _probe_binance_book_ticker_source(
    symbols: tuple[str, ...],
    *,
    start_month: str,
    end_month_exclusive: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    monthly = {}
    daily = {}
    for symbol in symbols:
        monthly[symbol] = _fetch_s3_objects(
            f"data/futures/um/monthly/bookTicker/{symbol}/",
            timeout_seconds,
        )
        daily[symbol] = _fetch_s3_objects(
            f"data/futures/um/daily/bookTicker/{symbol}/",
            timeout_seconds,
        )
    return summarize_book_ticker_source(
        symbols,
        start_month=start_month,
        end_month_exclusive=end_month_exclusive,
        monthly_objects_by_symbol=monthly,
        daily_objects_by_symbol=daily,
    )


def _fetch_s3_objects(prefix: str, timeout_seconds: float) -> tuple[Any, ...]:
    query = urlencode({"list-type": "2", "prefix": prefix})
    with urlopen(f"{S3_LIST_ENDPOINT}?{query}", timeout=timeout_seconds) as response:
        return parse_s3_list_objects(response.read().decode("utf-8"))


def _payload(
    args: argparse.Namespace,
    summary: dict[str, Any],
    source_review: dict[str, Any],
    gate: dict[str, Any],
    hourly_cost: pd.DataFrame,
) -> dict[str, Any]:
    cost_source_complete = bool(source_review.get("complete_for_window"))
    return {
        "dataset_version": _dataset_version(summary, args.summary_json),
        "bars_csv": str(args.bars_csv),
        "summary_json": str(args.summary_json),
        "cost_hourly_csv": str(args.cost_hourly_csv) if args.cost_hourly_csv else None,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_review": source_review,
        "normalized_cost_rows": int(len(hourly_cost)),
        "cost_gated_pass": bool(gate["cost_gated_pass"] and cost_source_complete),
        "cost_gate_reason": _cost_gate_reason(gate, source_review, hourly_cost),
        "gate_note": (
            "Cost-gated Sprint 7 PASS requires complete verified historical "
            "top-of-book/bookTicker evidence. Missing or incomplete evidence fails closed."
        ),
        "join_policy": "hourly cost joins as-of with cost_available_time <= bar open_time",
        "hourly_cost_schema": list(HOURLY_COST_COLUMNS),
        **gate,
    }


def _dataset_version(summary: dict[str, Any], summary_path: Path) -> str:
    if summary.get("dataset_version"):
        return str(summary["dataset_version"])
    normalized_path = summary.get("normalized_path")
    if normalized_path:
        return Path(str(normalized_path)).stem.removesuffix("_bars")
    return summary_path.stem.removesuffix("_summary")


def _cost_gate_reason(
    gate: dict[str, Any],
    source_review: dict[str, Any],
    hourly_cost: pd.DataFrame,
) -> str:
    if not source_review.get("complete_for_window"):
        return "historical top-of-book/bookTicker source is incomplete for the Sprint 7 window"
    if hourly_cost.empty:
        return "normalized historical execution-cost data is absent"
    if not gate["cost_gated_pass"]:
        return "no candidate pair has complete execution-cost evidence within thresholds"
    return "at least one candidate pair has complete execution-cost evidence within thresholds"


def _candidate_pairs(summary: dict[str, Any]) -> tuple[str, ...]:
    pairs = []
    for item in summary.get("candidate_pairs", []):
        if isinstance(item, dict) and "pair" in item:
            pairs.append(str(item["pair"]).strip().upper())
        elif isinstance(item, str):
            pairs.append(item.strip().upper())
    return tuple(pair for pair in pairs if pair)


def _symbols_for_review(
    summary: dict[str, Any],
    candidate_pairs: tuple[str, ...],
) -> tuple[str, ...]:
    symbols = {str(symbol).strip().upper() for symbol in summary.get("accepted_symbols", [])}
    for pair in candidate_pairs:
        left, right = pair.split("/", maxsplit=1)
        symbols.add(left)
        symbols.add(right)
    return tuple(sorted(symbol for symbol in symbols if symbol))


def _write_pair_csv(path: Path, pair_results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = (
        "pair",
        "cost_gated_pass",
        "combined_median_spread_bps",
        "combined_p95_spread_bps",
        "combined_p99_spread_bps",
        "reasons",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for result in pair_results:
            row = result.copy()
            row["reasons"] = ";".join(str(reason) for reason in row["reasons"])
            writer.writerow({column: row.get(column) for column in columns})


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
    parser.add_argument("--bars-csv", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--cost-hourly-csv", type=Path)
    parser.add_argument("--source-review-json", type=Path)
    parser.add_argument("--source-review-output-json", type=Path)
    parser.add_argument("--probe-binance-source", action="store_true")
    parser.add_argument("--start-month", default=DEFAULT_START_MONTH)
    parser.add_argument("--end-month-exclusive", default=DEFAULT_END_MONTH_EXCLUSIVE)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
