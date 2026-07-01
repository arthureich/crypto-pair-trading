#!/usr/bin/env python3
"""Download/normalize Binance public data and run Sprint 7 pair selection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research import CorrelationMode, PairSelectionConfig, select_pairs  # noqa: E402
from src.research.historical_dataset import (  # noqa: E402
    build_archive_plan,
    download_archives,
    expected_hourly_bars,
    normalize_archive_plan,
)

FULL_DATASET_MIN_HISTORY_BARS = 26_000
DEFAULT_DOWNLOAD_WORKERS = 8


def main() -> int:
    args = _parse_args()
    data_root = args.data_root.resolve()
    specs = build_archive_plan(
        args.symbols,
        start_month=args.start_month,
        end_month_exclusive=args.end_month_exclusive,
    )

    if args.download:
        download_archives(
            specs,
            data_root,
            overwrite=args.overwrite,
            max_workers=args.download_workers,
        )

    bars = normalize_archive_plan(
        specs,
        data_root,
        dataset_version=args.dataset_version,
        verify_checksums=not args.skip_checksum,
    )
    normalized_path = data_root / "normalized" / f"{args.dataset_version}_bars.csv"
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    bars.to_csv(normalized_path, index=False)

    expected_bars = expected_hourly_bars(args.start_month, args.end_month_exclusive)
    min_history_bars = (
        FULL_DATASET_MIN_HISTORY_BARS
        if expected_bars >= FULL_DATASET_MIN_HISTORY_BARS
        else max(1, int(expected_bars * 0.99))
    )
    config = PairSelectionConfig(
        expected_bars=expected_bars,
        min_history_bars=min_history_bars,
        min_history_coverage=0.99,
        min_pair_joint_coverage=0.99,
        require_reference_price_columns=True,
        correlation_mode=CorrelationMode.ROLLING_NO_LOOKAHEAD,
        correlation_window=min(args.correlation_window, max(2, expected_bars - 1)),
        min_correlation_observations=min(
            args.correlation_window,
            max(2, expected_bars - 1),
        ),
    )
    selection = select_pairs(bars, config)
    summary = _selection_summary(
        symbols=args.symbols,
        dataset_version=args.dataset_version,
        start_month=args.start_month,
        end_month_exclusive=args.end_month_exclusive,
        expected_bars=expected_bars,
        normalized_path=normalized_path,
        selection=selection,
    )
    summary_path = data_root / "normalized" / f"{args.dataset_version}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _selection_summary(
    *,
    symbols: list[str],
    dataset_version: str,
    start_month: str,
    end_month_exclusive: str,
    expected_bars: int,
    normalized_path: Path,
    selection,
) -> dict[str, object]:
    return {
        "dataset_version": dataset_version,
        "symbols": symbols,
        "start_month": start_month,
        "end_month_exclusive": end_month_exclusive,
        "expected_bars": expected_bars,
        "normalized_path": str(normalized_path),
        "accepted_symbols": [item.symbol for item in selection.accepted_symbols],
        "rejected_symbols": [
            {
                "symbol": item.symbol,
                "reasons": [reason.value for reason in item.reasons],
            }
            for item in selection.rejected_symbols
        ],
        "candidate_pairs": [
            {
                "pair": item.pair_id,
                "score": item.score,
                "correlation": item.metrics.correlation,
                "cost_filters_applied": item.metrics.cost_filters_applied,
                "funding_carry_bps_per_day": item.metrics.funding_carry_bps_per_day,
            }
            for item in selection.candidate_pairs
        ],
        "rejected_pairs": [
            {
                "pair": item.pair_id,
                "reasons": [reason.value for reason in item.reasons],
                "correlation": item.metrics.correlation,
            }
            for item in selection.rejected_pairs
        ],
        "gate_note": (
            "Statistical-only run. Cost-gated Sprint 7 PASS still requires verified "
            "historical top-of-book/L2 execution-cost evidence."
        ),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    parser.add_argument("--start-month", default="2023-06")
    parser.add_argument("--end-month-exclusive", default="2026-06")
    parser.add_argument("--dataset-version", default="sprint7_binance_usdm_1h")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "research" / "binance_public",
    )
    parser.add_argument("--correlation-window", type=int, default=168)
    parser.add_argument("--download-workers", type=int, default=DEFAULT_DOWNLOAD_WORKERS)
    parser.add_argument("--no-download", dest="download", action="store_false")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-checksum", action="store_true")
    parser.set_defaults(download=True)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
