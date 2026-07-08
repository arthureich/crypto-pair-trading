#!/usr/bin/env python3
"""Run the Family H (Order Flow / Book Depth) information-content diagnostic (TASK-ALT-007).

Pure diagnostic, per project_control/DECISIONS.md ADR-0025 -- no
strategy, no economic gate. Measures whether 5 formalized bookDepth-
derived features show a stable, non-trivial Spearman correlation with
24h forward returns, causal by construction. Joins the newly
downloaded/normalized book-depth dataset
(scripts/download_alt_book_depth.py) with the existing OHLCV bars
dataset (log_price) by (symbol, open_time). See
docs/pre_registers/TASK-ALT-007.md.
"""

from __future__ import annotations

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

from src.research.info_content import (  # noqa: E402
    InformationContentResult,
    evaluate_information_content,
)

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
BOOK_DEPTH_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint_alt_book_depth_202306_202605.csv.gz"
)
OUTPUT_JSON = (
    PROJECT_ROOT / "data/research/binance_public/cost_pilot/alt_info_order_flow_results.json"
)
REPORT_MD = PROJECT_ROOT / "reports/alt_info_order_flow_diagnostic.md"
EXPECTED_SYMBOL_COUNT = 20
FORWARD_HORIZON_HOURS = 24
ROLLING_WINDOW_HOURS = 2160  # 90 days, causal (shift(1) before rolling)
MAGNITUDE_THRESHOLD = 0.03

PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
PERIOD_BOUNDARIES = tuple(
    int(pd.Timestamp(d, tz="UTC").timestamp() * 1000)
    for d in ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
)


def main() -> int:
    bars = pd.read_csv(BARS_CSV, usecols=["symbol", "open_time", "log_price"])
    if bars["symbol"].nunique() != EXPECTED_SYMBOL_COUNT:
        raise ValueError(f"expected {EXPECTED_SYMBOL_COUNT} symbols in {BARS_CSV}")

    depth = pd.read_csv(BOOK_DEPTH_CSV)
    if depth["symbol"].nunique() != EXPECTED_SYMBOL_COUNT:
        raise ValueError(f"expected {EXPECTED_SYMBOL_COUNT} symbols in {BOOK_DEPTH_CSV}")

    panels = _build_feature_panels(bars, depth)

    results: dict[str, InformationContentResult] = {}
    for feature_name, panel in panels.items():
        results[feature_name] = evaluate_information_content(
            panel,
            feature_name,
            PERIOD_BOUNDARIES,
            PERIOD_LABELS,
            magnitude_threshold=MAGNITUDE_THRESHOLD,
        )

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "bars_csv": str(BARS_CSV),
        "book_depth_csv": str(BOOK_DEPTH_CSV),
        "forward_horizon_hours": FORWARD_HORIZON_HOURS,
        "rolling_window_hours": ROLLING_WINDOW_HOURS,
        "magnitude_threshold": MAGNITUDE_THRESHOLD,
        "period_labels": PERIOD_LABELS,
        "period_boundaries_ms": PERIOD_BOUNDARIES,
        "results": {name: asdict(result) for name, result in results.items()},
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    for name, result in results.items():
        verdict = "TEM_INFORMACAO" if result.has_information else "SEM_INFORMACAO"
        print(f"{name}: rho={result.full_sample_rho:.4f} n={result.full_sample_n} {verdict}")
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _build_feature_panels(bars: pd.DataFrame, depth: pd.DataFrame) -> dict[str, pd.DataFrame]:
    price_wide = bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()

    bid_1pct = depth.pivot(index="open_time", columns="symbol", values="notional_-1.00")
    ask_1pct = depth.pivot(index="open_time", columns="symbol", values="notional_1.00")
    bid_5pct = depth.pivot(index="open_time", columns="symbol", values="notional_-5.00")
    ask_5pct = depth.pivot(index="open_time", columns="symbol", values="notional_5.00")

    # Align the book-depth panels onto the exact same hourly index as the
    # bars dataset (the canonical index) -- book-depth coverage can start
    # slightly later per symbol, and any rows outside the bars index are
    # simply dropped by reindexing.
    bid_1pct = bid_1pct.reindex(price_wide.index)
    ask_1pct = ask_1pct.reindex(price_wide.index)
    bid_5pct = bid_5pct.reindex(price_wide.index)
    ask_5pct = ask_5pct.reindex(price_wide.index)

    forward_return = price_wide.shift(-FORWARD_HORIZON_HOURS) - price_wide
    price_return_24h = price_wide.diff(FORWARD_HORIZON_HOURS)

    book_imbalance_1pct = (bid_1pct - ask_1pct) / (bid_1pct + ask_1pct)
    book_imbalance_5pct = (bid_5pct - ask_5pct) / (bid_5pct + ask_5pct)
    depth_concentration = (bid_1pct + ask_1pct) / (bid_5pct + ask_5pct)

    total_near_depth = bid_1pct + ask_1pct
    depth_change_24h = total_near_depth.diff(FORWARD_HORIZON_HOURS)

    z_imbalance = _zscore_causal(book_imbalance_1pct)
    z_price_return = _zscore_causal(price_return_24h)
    imbalance_price_divergence = z_imbalance - z_price_return

    features = {
        "book_imbalance_1pct": book_imbalance_1pct,
        "book_imbalance_5pct": book_imbalance_5pct,
        "depth_concentration": depth_concentration,
        "depth_change_24h": depth_change_24h,
        "imbalance_price_divergence": imbalance_price_divergence,
    }
    return {name: _stack_panel(wide, forward_return) for name, wide in features.items()}


def _zscore_causal(wide: pd.DataFrame) -> pd.DataFrame:
    mean = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).mean()
    std = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).std()
    return (wide - mean) / std


def _stack_panel(feature_wide: pd.DataFrame, target_wide: pd.DataFrame) -> pd.DataFrame:
    feature_long = feature_wide.stack(future_stack=True).rename("feature")
    target_long = target_wide.stack(future_stack=True).rename("target")
    combined = pd.concat([feature_long, target_long], axis=1).reset_index()
    return combined[["open_time", "feature", "target"]]


def _write_report(payload: dict[str, Any]) -> None:
    header_periods = " | ".join(payload["period_labels"])
    header_dashes = "---:|" * len(payload["period_labels"])
    lines = [
        "# Family H (Order Flow / Book Depth) Information-Content Diagnostic",
        "",
        "Research Phase II, TASK-ALT-007. Status: pure diagnostic, per "
        "`project_control/DECISIONS.md` ADR-0025. No strategy, no economic "
        "gate -- measures whether each feature shows a stable, non-trivial "
        "Spearman correlation with 24h forward returns.",
        "",
        f"Forward horizon: {payload['forward_horizon_hours']}h. "
        f"Rolling causal window: {payload['rolling_window_hours']}h (90 days). "
        f"Magnitude threshold: {payload['magnitude_threshold']}.",
        "",
        "## Results",
        "",
        f"| Feature | Full rho | Full N | {header_periods} | Sign consistent | Has information |",
        f"|---|---:|---:|{header_dashes}---|---|",
    ]
    for name, result in payload["results"].items():
        sub_cells = " | ".join(
            f"{sp['spearman_rho']:.4f} (n={sp['n_obs']})" for sp in result["sub_periods"]
        )
        lines.append(
            f"| {name} | {result['full_sample_rho']:.4f} | {result['full_sample_n']} | "
            f"{sub_cells} | {result['sign_consistent']} | {result['has_information']} |"
        )
    lines.append("")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


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


if __name__ == "__main__":
    raise SystemExit(main())
