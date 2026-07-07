#!/usr/bin/env python3
"""Run the Family G (Funding Structure) information-content diagnostic (TASK-ALT-001).

Pure diagnostic, per project_control/DECISIONS.md ADR-0019 -- no
strategy, no economic gate. Measures whether 4 formalized funding-derived
features show a stable, non-trivial Spearman correlation with 24h
forward returns, causal by construction, on the EXISTING normalized
dataset (no new download). See docs/pre_registers/TASK-ALT-001.md.
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
OUTPUT_JSON = (
    PROJECT_ROOT / "data/research/binance_public/cost_pilot/alt_info_funding_structure_results.json"
)
REPORT_MD = PROJECT_ROOT / "reports/alt_info_funding_structure_diagnostic.md"
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
    bars = pd.read_csv(BARS_CSV, usecols=["symbol", "open_time", "log_price", "funding_rate_asof"])
    symbol_count = bars["symbol"].nunique()
    if symbol_count != EXPECTED_SYMBOL_COUNT:
        raise ValueError(
            f"expected {EXPECTED_SYMBOL_COUNT} symbols in {BARS_CSV}, got {symbol_count}"
        )

    panels = _build_feature_panels(bars)

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


def _build_feature_panels(bars: pd.DataFrame) -> dict[str, pd.DataFrame]:
    funding_wide = bars.pivot(
        index="open_time", columns="symbol", values="funding_rate_asof"
    ).sort_index()
    price_wide = bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()

    forward_return = price_wide.shift(-FORWARD_HORIZON_HOURS) - price_wide

    funding_mean_90d = funding_wide.shift(1).rolling(ROLLING_WINDOW_HOURS).mean()
    funding_std_90d = funding_wide.shift(1).rolling(ROLLING_WINDOW_HOURS).std()
    funding_extreme = (funding_wide - funding_mean_90d) / funding_std_90d

    funding_reversal = funding_wide.diff(FORWARD_HORIZON_HOURS)
    funding_acceleration = funding_reversal.diff(FORWARD_HORIZON_HOURS)

    price_return_24h = price_wide.diff(FORWARD_HORIZON_HOURS)
    z_funding_reversal = _zscore_causal(funding_reversal)
    z_price_return = _zscore_causal(price_return_24h)
    funding_price_divergence = z_funding_reversal - z_price_return

    features = {
        "funding_extreme": funding_extreme,
        "funding_reversal": funding_reversal,
        "funding_acceleration": funding_acceleration,
        "funding_price_divergence": funding_price_divergence,
    }

    panels = {}
    for name, wide_feature in features.items():
        stacked = _stack_panel(wide_feature, forward_return)
        panels[name] = stacked
    return panels


def _zscore_causal(wide: pd.DataFrame) -> pd.DataFrame:
    mean = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).mean()
    std = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).std()
    return (wide - mean) / std


def _stack_panel(feature_wide: pd.DataFrame, target_wide: pd.DataFrame) -> pd.DataFrame:
    feature_long = feature_wide.stack(future_stack=True).rename("feature")
    target_long = target_wide.stack(future_stack=True).rename("target")
    combined = pd.concat([feature_long, target_long], axis=1).reset_index()
    combined = combined.rename(columns={"open_time": "open_time"})
    return combined[["open_time", "feature", "target"]]


def _write_report(payload: dict[str, Any]) -> None:
    header_periods = " | ".join(payload["period_labels"])
    header_dashes = "---:|" * len(payload["period_labels"])
    lines = [
        "# Family G (Funding Structure) Information-Content Diagnostic",
        "",
        "Research Phase II, TASK-ALT-001. Status: pure diagnostic, per "
        "`project_control/DECISIONS.md` ADR-0019. No strategy, no economic "
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
