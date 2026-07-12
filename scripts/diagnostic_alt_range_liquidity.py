#!/usr/bin/env python3
"""TASK-ALT-008: Family B (range-volatility shape) + Family C (Amihud illiquidity).

Pre-registered in `docs/pre_registers/TASK-ALT-008.md` (ADR-0028). Closes the
last un-run DIRECTIONAL diagnostics on free bar data: range-vol shape (Family B
was only tested as a risk/regime signal) and bar-derived Amihud illiquidity
(Family C was only tested via order-book depth). 6 causal features vs the 24h
and 4h forward return. Pure diagnostic: no economic gate, no strategy.

All features are causal -- known at the CLOSE of bar t; every z-score uses
shift(1) before rolling. The forward return is the only forward-looking term.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.info_content import evaluate_information_content  # noqa: E402

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = (
    PROJECT_ROOT / "data/research/binance_public/cost_pilot/alt_range_liquidity_results.json"
)
REPORT_MD = PROJECT_ROOT / "reports/alt_range_liquidity_diagnostic.md"
EXPECTED_SYMBOL_COUNT = 20
ROLLING_WINDOW_HOURS = 2160
MAGNITUDE_THRESHOLD = 0.03
TARGET_HORIZONS_HOURS = (24, 4)
_PARKINSON_COEF = 1.0 / (4.0 * math.log(2.0))

PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
PERIOD_BOUNDARIES = tuple(
    int(pd.Timestamp(d, tz="UTC").timestamp() * 1000)
    for d in ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
)


def main() -> int:
    bars = pd.read_csv(
        BARS_CSV,
        usecols=[
            "symbol",
            "open_time",
            "log_price",
            "open",
            "high",
            "low",
            "close",
            "quote_volume",
            "number_of_trades",
        ],
    )
    if bars["symbol"].nunique() != EXPECTED_SYMBOL_COUNT:
        raise ValueError(f"expected {EXPECTED_SYMBOL_COUNT} symbols in bars")

    price_wide, features = _build_features(bars)

    results: dict[str, dict] = {}
    for horizon in TARGET_HORIZONS_HOURS:
        forward_return = price_wide.shift(-horizon) - price_wide
        for name, feature_wide in features.items():
            panel = _stack(feature_wide, forward_return)
            res = evaluate_information_content(
                panel,
                name,
                PERIOD_BOUNDARIES,
                PERIOD_LABELS,
                magnitude_threshold=MAGNITUDE_THRESHOLD,
            )
            results[f"{name}@{horizon}h"] = asdict(res)

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-ALT-008 (ADR-0028): Family B range-vol shape + Family C Amihud",
        "target": "forward_return_h = log_price[t+h] - log_price[t]",
        "horizons_hours": list(TARGET_HORIZONS_HOURS),
        "magnitude_threshold": MAGNITUDE_THRESHOLD,
        "period_labels": PERIOD_LABELS,
        "results": results,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    for name, res in results.items():
        verdict = "TEM_INFORMACAO" if res["has_information"] else "sem"
        print(f"{name}: rho={res['full_sample_rho']:+.4f} {verdict}", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _build_features(bars: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    def wide(column: str) -> pd.DataFrame:
        return bars.pivot(index="open_time", columns="symbol", values=column).sort_index()

    price_wide = wide("log_price")
    high, low = wide("high"), wide("low")
    open_, close = wide("open"), wide("close")
    quote = wide("quote_volume")
    trades = wide("number_of_trades")

    # Family B: range-shape estimators (all use only bar t's OHLC).
    log_hl = np.log(high / low)
    parkinson = _PARKINSON_COEF * log_hl * log_hl
    rogers_satchell = np.log(high / close) * np.log(high / open_) + np.log(low / close) * np.log(
        low / open_
    )
    hl_span = (high - low).replace(0.0, np.nan)
    close_location = (close - low) / hl_span - 0.5  # -0.5..+0.5 intrabar pressure

    # Family C: Amihud illiquidity / turnover / trade size.
    hourly_return = price_wide.diff()  # log-return per hour, causal at close t
    amihud = hourly_return.abs() / quote.replace(0.0, np.nan)
    trade_size = quote / trades.replace(0.0, np.nan)

    features = {
        "parkinson_range_z": _zscore_causal(parkinson),
        "rogers_satchell_z": _zscore_causal(rogers_satchell),
        "close_location_in_range": close_location.reindex(price_wide.index),
        "amihud_illiq_z": _zscore_causal(amihud),
        "turnover_z": _zscore_causal(quote),
        "trade_size_z": _zscore_causal(trade_size),
    }
    return price_wide, features


def _zscore_causal(wide: pd.DataFrame) -> pd.DataFrame:
    mean = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).mean()
    std = wide.shift(1).rolling(ROLLING_WINDOW_HOURS).std()
    return (wide - mean) / std


def _stack(feature_wide: pd.DataFrame, target_wide: pd.DataFrame) -> pd.DataFrame:
    feature_long = feature_wide.stack(future_stack=True).rename("feature")
    target_long = target_wide.stack(future_stack=True).rename("target")
    combined = pd.concat([feature_long, target_long], axis=1).reset_index()
    return combined[["open_time", "feature", "target"]]


def _write_report(payload: dict) -> None:
    header = " | ".join(payload["period_labels"])
    lines = [
        "# TASK-ALT-008 -- Family B (Range-Vol Shape) + Family C (Amihud) Diagnostic",
        "",
        "Per `docs/pre_registers/TASK-ALT-008.md` (ADR-0028). The last un-run "
        "DIRECTIONAL diagnostics on free bar data: range-shape estimators (B was "
        "only tested as a risk/regime signal) and bar-derived Amihud illiquidity "
        "(C was only tested via order-book depth). 6 causal features vs 24h and 4h "
        "forward return. Pure diagnostic. Sign-consistency across 3 sub-periods is "
        "the pre-committed multiple-testing defense for the 12-cell grid.",
        "",
        f"Target: {payload['target']}, h in {payload['horizons_hours']}. "
        f"Threshold: |rho| >= {payload['magnitude_threshold']}.",
        "",
        "## Results",
        "",
        f"| Feature @ horizon | Full rho | Sub ({header}) | Sign consistent | Has info |",
        "|---|---:|---|---|---|",
    ]
    for name, res in payload["results"].items():
        sub = " | ".join(f"{sp['spearman_rho']:+.4f}" for sp in res["sub_periods"])
        lines.append(
            f"| {name} | {res['full_sample_rho']:+.4f} | {sub} | "
            f"{res['sign_consistent']} | {res['has_information']} |"
        )
    hits = [n for n, r in payload["results"].items() if r["has_information"]]
    verdict = (
        f"Features with information: {', '.join(hits)}. Each must pass the "
        "descriptive economic check (gross decile spread vs cost) before any "
        "strategy pre-registration -- information is not a tradeable edge."
        if hits
        else "No range-shape or liquidity feature carries directional information "
        "at 24h or 4h. Families B (Volatility) and C (Liquidity) move from "
        "~Concluida to CONCLUIDA on public data: no economically-relevant "
        "directional information in range-vol shape or bar-derived Amihud "
        "illiquidity in this universe/period. The public-data family sweep is "
        "complete; only external-data families (options VRP, on-chain, cross-venue "
        "flow) remain -- their acquisition is a user investment decision."
    )
    lines.extend(["", "## Reading", "", verdict, ""])
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, bool | str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
