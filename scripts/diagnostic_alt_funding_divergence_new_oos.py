#!/usr/bin/env python3
"""Run TASK-ALT-005 funding_price_divergence on genuine new OOS data.

This is a pure information-content diagnostic. It may promote the
near-miss from TASK-ALT-001 to a future feasibility task, but it does not
authorize strategy design, SignalIntent, execution, ledger, recovery, ML,
paper trading, or live trading changes. See docs/pre_registers/TASK-ALT-005.md
and project_control/DECISIONS.md ADR-0023.
"""

from __future__ import annotations

import argparse
import json
import math
import numbers
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.historical_dataset import (  # noqa: E402
    build_archive_plan,
    download_archives,
    expected_hourly_bars,
    month_range,
    normalize_archive_plan,
)
from src.research.info_content import (  # noqa: E402
    InformationContentResult,
    evaluate_information_content,
)

DEFAULT_SYMBOLS = (
    "ADAUSDT",
    "APTUSDT",
    "ARBUSDT",
    "ATOMUSDT",
    "AVAXUSDT",
    "BCHUSDT",
    "BNBUSDT",
    "BTCUSDT",
    "DOGEUSDT",
    "DOTUSDT",
    "ETCUSDT",
    "ETHUSDT",
    "LINKUSDT",
    "LTCUSDT",
    "OPUSDT",
    "SOLUSDT",
    "SUIUSDT",
    "TRXUSDT",
    "UNIUSDT",
    "XRPUSDT",
)
BASE_BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
DATA_ROOT = PROJECT_ROOT / "data/research/binance_public"
OUTPUT_JSON = (
    PROJECT_ROOT
    / "data/research/binance_public/cost_pilot/alt_info_funding_divergence_new_oos_results.json"
)
REPORT_MD = PROJECT_ROOT / "reports/alt_info_funding_divergence_new_oos.md"
HOUR_MS = 60 * 60 * 1000
FORWARD_HORIZON_HOURS = 24
ROLLING_WINDOW_HOURS = 2160
MAGNITUDE_THRESHOLD = 0.03
MIN_VALID_OBSERVATIONS = 10_000
MIN_SYMBOL_COVERAGE = 0.99
REQUIRED_COLUMNS = ("symbol", "open_time", "log_price", "funding_rate_asof")
PROMOTE = "PROMOVE_PARA_FEASIBILITY"
DO_NOT_PROMOTE = "NAO_PROMOVE"
DATA_GATE_FAIL = "DATA_GATE_FAIL_CLOSED"


@dataclass(frozen=True, slots=True)
class DataGateResult:
    status: str
    reasons: tuple[str, ...]
    expected_symbol_count: int
    actual_symbol_count: int
    expected_rows_per_symbol: int
    min_symbol_coverage: float
    duplicate_row_count: int
    full_sample_n: int


@dataclass(frozen=True, slots=True)
class NewOosDiagnostic:
    decision: str
    data_gate: DataGateResult
    information_result: InformationContentResult | None


def main() -> int:
    args = _parse_args()
    data_root = args.data_root.resolve()
    symbols = tuple(args.symbols)
    specs = build_archive_plan(
        symbols,
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

    extension = normalize_archive_plan(
        specs,
        data_root,
        dataset_version=args.dataset_version,
        verify_checksums=not args.skip_checksum,
    )
    extension_path = data_root / "normalized" / f"{args.dataset_version}_bars.csv.gz"
    extension_path.parent.mkdir(parents=True, exist_ok=True)
    extension.to_csv(extension_path, index=False)

    base = pd.read_csv(args.base_bars_csv, usecols=list(REQUIRED_COLUMNS))
    diagnostic = run_new_oos_diagnostic(
        base,
        extension[list(REQUIRED_COLUMNS)],
        symbols=symbols,
        start_month=args.start_month,
        end_month_exclusive=args.end_month_exclusive,
    )
    payload = _build_payload(
        diagnostic,
        symbols=symbols,
        base_bars_csv=args.base_bars_csv,
        extension_bars_csv=extension_path,
        dataset_version=args.dataset_version,
        start_month=args.start_month,
        end_month_exclusive=args.end_month_exclusive,
        archive_count=len(specs),
        checksums_verified=not args.skip_checksum,
    )
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    print(
        f"{diagnostic.decision}: "
        f"data_gate={diagnostic.data_gate.status} "
        f"n={diagnostic.data_gate.full_sample_n}"
    )
    if diagnostic.information_result is not None:
        print(f"rho={diagnostic.information_result.full_sample_rho:.6f}")
    print(f"Wrote {extension_path}", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def run_new_oos_diagnostic(
    base_bars: pd.DataFrame,
    extension_bars: pd.DataFrame,
    *,
    symbols: tuple[str, ...],
    start_month: str,
    end_month_exclusive: str,
    min_observations: int = MIN_VALID_OBSERVATIONS,
) -> NewOosDiagnostic:
    start_ms = _month_start_ms(start_month)
    end_ms = _month_start_ms(end_month_exclusive)
    expected_rows = expected_hourly_bars(start_month, end_month_exclusive)

    precheck = _precheck_extension_bars(
        extension_bars,
        symbols=symbols,
        start_ms=start_ms,
        end_ms=end_ms,
        expected_rows_per_symbol=expected_rows,
    )
    if precheck.reasons:
        return NewOosDiagnostic(DATA_GATE_FAIL, precheck, None)

    panel = build_funding_price_divergence_panel(
        base_bars,
        extension_bars,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    labels, boundaries = month_periods(start_month, end_month_exclusive)
    result = evaluate_information_content(
        panel,
        "funding_price_divergence",
        boundaries,
        labels,
        magnitude_threshold=MAGNITUDE_THRESHOLD,
    )

    reasons = list(precheck.reasons)
    if result.full_sample_n < min_observations:
        reasons.append(
            f"full_sample_n {result.full_sample_n} below minimum {min_observations}"
        )
    data_gate = DataGateResult(
        status="PASS" if not reasons else DATA_GATE_FAIL,
        reasons=tuple(reasons),
        expected_symbol_count=precheck.expected_symbol_count,
        actual_symbol_count=precheck.actual_symbol_count,
        expected_rows_per_symbol=precheck.expected_rows_per_symbol,
        min_symbol_coverage=precheck.min_symbol_coverage,
        duplicate_row_count=precheck.duplicate_row_count,
        full_sample_n=result.full_sample_n,
    )
    if data_gate.status != "PASS":
        return NewOosDiagnostic(DATA_GATE_FAIL, data_gate, result)

    monthly_signs_positive = all(
        not math.isnan(period.spearman_rho) and period.spearman_rho > 0
        for period in result.sub_periods
    )
    decision = (
        PROMOTE
        if result.full_sample_rho >= MAGNITUDE_THRESHOLD and monthly_signs_positive
        else DO_NOT_PROMOTE
    )
    return NewOosDiagnostic(decision, data_gate, result)


def build_funding_price_divergence_panel(
    base_bars: pd.DataFrame,
    extension_bars: pd.DataFrame,
    *,
    start_ms: int,
    end_ms: int,
) -> pd.DataFrame:
    """Build the exact TASK-ALT-001 feature, then keep only new-OOS rows."""

    _require_columns(base_bars, REQUIRED_COLUMNS, "base_bars")
    _require_columns(extension_bars, REQUIRED_COLUMNS, "extension_bars")
    combined = pd.concat(
        [base_bars[list(REQUIRED_COLUMNS)], extension_bars[list(REQUIRED_COLUMNS)]],
        ignore_index=True,
    )
    duplicated = combined.duplicated(["symbol", "open_time"], keep=False)
    if duplicated.any():
        keys = combined.loc[duplicated, ["symbol", "open_time"]].drop_duplicates()
        raise ValueError(f"combined bars have duplicate keys: {keys.head(3).to_dict('records')}")

    combined = combined.sort_values(["symbol", "open_time"], kind="mergesort")
    funding_wide = combined.pivot(
        index="open_time",
        columns="symbol",
        values="funding_rate_asof",
    ).sort_index()
    price_wide = combined.pivot(
        index="open_time",
        columns="symbol",
        values="log_price",
    ).sort_index()

    forward_return = price_wide.shift(-FORWARD_HORIZON_HOURS) - price_wide
    funding_reversal = funding_wide.diff(FORWARD_HORIZON_HOURS)
    price_return_24h = price_wide.diff(FORWARD_HORIZON_HOURS)
    feature_wide = _zscore_causal(funding_reversal) - _zscore_causal(price_return_24h)

    feature_long = feature_wide.stack(future_stack=True).rename("feature")
    target_long = forward_return.stack(future_stack=True).rename("target")
    panel = pd.concat([feature_long, target_long], axis=1).reset_index()
    panel = panel.rename(columns={"open_time": "open_time"})
    decision_mask = (panel["open_time"] >= start_ms) & (panel["open_time"] < end_ms)
    return panel.loc[decision_mask, ["open_time", "feature", "target"]].reset_index(drop=True)


def month_periods(
    start_month: str,
    end_month_exclusive: str,
) -> tuple[tuple[str, ...], tuple[int, ...]]:
    labels = month_range(start_month, end_month_exclusive)
    boundaries = [_month_start_ms(month) for month in labels]
    boundaries.append(_month_start_ms(end_month_exclusive))
    return labels, tuple(boundaries)


def _zscore_causal(wide: pd.DataFrame) -> pd.DataFrame:
    mean = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).mean()
    std = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).std()
    return (wide - mean) / std


def _precheck_extension_bars(
    extension_bars: pd.DataFrame,
    *,
    symbols: tuple[str, ...],
    start_ms: int,
    end_ms: int,
    expected_rows_per_symbol: int,
) -> DataGateResult:
    reasons: list[str] = []
    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in extension_bars.columns
    ]
    if missing_columns:
        reasons.append(f"missing required columns: {missing_columns}")
        return DataGateResult(
            DATA_GATE_FAIL,
            tuple(reasons),
            len(symbols),
            0,
            expected_rows_per_symbol,
            0.0,
            0,
            0,
        )

    window = extension_bars[
        (extension_bars["open_time"] >= start_ms) & (extension_bars["open_time"] < end_ms)
    ].copy()
    expected_symbols = set(symbols)
    actual_symbols = set(window["symbol"].astype(str).unique())
    missing_symbols = sorted(expected_symbols - actual_symbols)
    extra_symbols = sorted(actual_symbols - expected_symbols)
    if missing_symbols:
        reasons.append(f"missing symbols: {missing_symbols}")
    if extra_symbols:
        reasons.append(f"unexpected symbols: {extra_symbols}")

    duplicate_count = int(window.duplicated(["symbol", "open_time"], keep=False).sum())
    if duplicate_count:
        reasons.append(f"duplicate (symbol, open_time) rows: {duplicate_count}")

    min_coverage = 0.0
    if expected_rows_per_symbol > 0 and expected_symbols:
        counts = window.groupby("symbol", sort=False)["open_time"].nunique()
        coverages = [
            float(counts.get(symbol, 0) / expected_rows_per_symbol)
            for symbol in sorted(expected_symbols)
        ]
        min_coverage = min(coverages) if coverages else 0.0
        low_coverage = [
            symbol
            for symbol in sorted(expected_symbols)
            if float(counts.get(symbol, 0) / expected_rows_per_symbol) < MIN_SYMBOL_COVERAGE
        ]
        if low_coverage:
            reasons.append(f"coverage below {MIN_SYMBOL_COVERAGE:.2%}: {low_coverage}")

    return DataGateResult(
        status="PASS" if not reasons else DATA_GATE_FAIL,
        reasons=tuple(reasons),
        expected_symbol_count=len(symbols),
        actual_symbol_count=len(actual_symbols),
        expected_rows_per_symbol=expected_rows_per_symbol,
        min_symbol_coverage=min_coverage,
        duplicate_row_count=duplicate_count,
        full_sample_n=0,
    )


def _build_payload(
    diagnostic: NewOosDiagnostic,
    *,
    symbols: tuple[str, ...],
    base_bars_csv: Path,
    extension_bars_csv: Path,
    dataset_version: str,
    start_month: str,
    end_month_exclusive: str,
    archive_count: int,
    checksums_verified: bool,
) -> dict[str, Any]:
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-ALT-005",
        "dataset_version": dataset_version,
        "base_bars_csv": str(base_bars_csv),
        "extension_bars_csv": str(extension_bars_csv),
        "start_month": start_month,
        "end_month_exclusive": end_month_exclusive,
        "symbols": list(symbols),
        "archive_count": archive_count,
        "checksums_verified": checksums_verified,
        "forward_horizon_hours": FORWARD_HORIZON_HOURS,
        "rolling_window_hours": ROLLING_WINDOW_HOURS,
        "magnitude_threshold": MAGNITUDE_THRESHOLD,
        "decision": diagnostic.decision,
        "data_gate": asdict(diagnostic.data_gate),
        "information_result": (
            asdict(diagnostic.information_result)
            if diagnostic.information_result is not None
            else None
        ),
    }


def _write_report(payload: dict[str, Any]) -> None:
    result = payload["information_result"]
    lines = [
        "# Funding Price Divergence New-OOS Diagnostic",
        "",
        "TASK-ALT-005 / ADR-0023. Pure information-content validation on "
        "genuine new OOS data. No strategy, no economic gate, no SignalIntent, "
        "no Execution/Ledger/Recovery/ML/live change.",
        "",
        f"Window: {payload['start_month']} through {payload['end_month_exclusive']} "
        "(end exclusive).",
        f"Symbols: {len(payload['symbols'])}. Archives planned: {payload['archive_count']}. "
        f"Checksums verified: {payload['checksums_verified']}.",
        "",
        "## Decision",
        "",
        f"`{payload['decision']}`",
        "",
        "## Data Gate",
        "",
        f"Status: `{payload['data_gate']['status']}`",
        f"Reasons: {payload['data_gate']['reasons']}",
        f"Valid observations: {payload['data_gate']['full_sample_n']}",
        "",
    ]
    if result is not None:
        lines.extend(
            [
                "## Information Result",
                "",
                f"Full-sample rho: {result['full_sample_rho']:.6f}",
                f"Full-sample N: {result['full_sample_n']}",
                "",
                "| Period | Rho | N |",
                "|---|---:|---:|",
            ]
        )
        for period in result["sub_periods"]:
            lines.append(
                f"| {period['period_label']} | {period['spearman_rho']:.6f} | "
                f"{period['n_obs']} |"
            )
        lines.append("")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...], label: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} missing required columns: {missing}")


def _month_start_ms(month: str) -> int:
    return int(pd.Timestamp(f"{month}-01", tz="UTC").timestamp() * 1000)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, bool | str) or value is None:
        return value
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--start-month", default="2026-06")
    parser.add_argument("--end-month-exclusive", default="2026-07")
    parser.add_argument("--dataset-version", default="sprint_alt_funding_divergence_202606")
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--base-bars-csv", type=Path, default=BASE_BARS_CSV)
    parser.add_argument("--download-workers", type=int, default=4)
    parser.add_argument("--no-download", dest="download", action="store_false")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-checksum", action="store_true")
    parser.set_defaults(download=True)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
