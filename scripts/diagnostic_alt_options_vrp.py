#!/usr/bin/env python3
"""TASK-ALT-011: Family F (Options) DVOL/VRP-as-predictor info-content diagnostic.

Pre-registered in `docs/pre_registers/TASK-ALT-011.md` (ADR-0032). Tests whether
free Deribit DVOL and DVOL-derived features (variance risk premium, DVOL shock,
IV/RV ratio) carry DIRECTIONAL information about forward BTC/ETH returns -- Angle
B (predictor for the existing perp strategy), no options-book pivot, zero spend.
4 causal daily features vs the 7d and 30d forward daily return. Pure diagnostic.

BTC/ETH only (options liquidity), so a 2-asset pooled panel -- low cross-sectional
breadth, flagged. Causal: DVOL is a market observable, but every feature still
gets an explicit outer shift(1) (prior-day value) on top of the causal rolling
z-score, for consistency with ALT-009. The forward return is the only
forward-looking term.
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

DVOL_CSV = (
    PROJECT_ROOT / "data/research/binance_public/normalized/sprint_alt_dvol_202306_202605.csv.gz"
)
BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/alt_options_vrp_results.json"
REPORT_MD = PROJECT_ROOT / "reports/alt_options_vrp_diagnostic.md"
ROLLING_WINDOW_DAYS = 90
RV_WINDOW_DAYS = 30
MAGNITUDE_THRESHOLD = 0.03
TARGET_HORIZONS_DAYS = (7, 30)
_ANNUALIZE = math.sqrt(365)
_ASSETS = ("btc", "eth")

PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
PERIOD_BOUNDARIES = tuple(
    int(pd.Timestamp(d, tz="UTC").timestamp() * 1000)
    for d in ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
)


def main() -> int:
    dvol = pd.read_csv(DVOL_CSV, parse_dates=["day"])
    daily_logprice = _daily_logprice(BARS_CSV)  # index=day, columns=base_asset

    features = _build_features(dvol, daily_logprice)

    results: dict[str, dict] = {}
    for horizon in TARGET_HORIZONS_DAYS:
        forward_return = daily_logprice.shift(-horizon) - daily_logprice
        for name, feature_wide in features.items():
            panel = _stack(feature_wide, forward_return)
            res = evaluate_information_content(
                panel,
                name,
                PERIOD_BOUNDARIES,
                PERIOD_LABELS,
                magnitude_threshold=MAGNITUDE_THRESHOLD,
            )
            results[f"{name}@{horizon}d"] = asdict(res)

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-ALT-011 (ADR-0032): Family F options DVOL/VRP-as-predictor",
        "target": "forward_return_h = daily_log_price[D+h] - daily_log_price[D]",
        "horizons_days": list(TARGET_HORIZONS_DAYS),
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
        rho = res["full_sample_rho"]
        rho_s = "None" if rho is None else f"{rho:+.4f}"
        print(f"{name}: rho={rho_s} n={res['full_sample_n']} {verdict}", file=sys.stderr)
    print(f"Wrote {OUTPUT_JSON}\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


def _daily_logprice(bars_csv: Path) -> pd.DataFrame:
    bars = pd.read_csv(bars_csv, usecols=["symbol", "base_asset", "open_time", "log_price"])
    bars["base_asset"] = bars["base_asset"].str.lower()
    bars = bars[bars["base_asset"].isin(_ASSETS)]
    bars["day"] = pd.to_datetime(bars["open_time"], unit="ms", utc=True).dt.floor("D")
    daily = (
        bars.sort_values("open_time", kind="mergesort")
        .groupby(["base_asset", "day"], as_index=False)
        .last()
    )
    return daily.pivot(index="day", columns="base_asset", values="log_price").sort_index()


def _build_features(dvol: pd.DataFrame, daily_logprice: pd.DataFrame) -> dict[str, pd.DataFrame]:
    dvol_wide = (
        dvol.pivot(index="day", columns="asset", values="dvol_close")
        .reindex(index=daily_logprice.index, columns=daily_logprice.columns)
        .sort_index()
    )
    iv = dvol_wide / 100.0  # DVOL is annualized vol in percent -> fraction
    daily_ret = daily_logprice.diff()
    rv = daily_ret.rolling(RV_WINDOW_DAYS).std() * _ANNUALIZE  # annualized realized vol
    vrp = iv**2 - rv**2  # variance risk premium
    iv_rv_ratio = iv / rv.replace(0.0, np.nan)

    return {
        "dvol_z": _causal_z(dvol_wide),
        "vrp_z": _causal_z(vrp),
        "dvol_change_z": _causal_z(dvol_wide.diff()),
        "iv_rv_ratio_z": _causal_z(iv_rv_ratio),
    }


def _causal_z(wide: pd.DataFrame) -> pd.DataFrame:
    mean = wide.shift(1).rolling(ROLLING_WINDOW_DAYS).mean()
    std = wide.shift(1).rolling(ROLLING_WINDOW_DAYS).std()
    z = (wide - mean) / std
    return z.shift(1)  # prior-day value (conservative causal lag, matches ALT-009)


def _stack(feature_wide: pd.DataFrame, target_wide: pd.DataFrame) -> pd.DataFrame:
    feature_long = feature_wide.stack(future_stack=True).rename("feature")
    target_long = target_wide.stack(future_stack=True).rename("target")
    combined = pd.concat([feature_long, target_long], axis=1).reset_index()
    combined.columns = ["day", "asset", "feature", "target"]
    day_utc = pd.to_datetime(combined["day"], utc=True)
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    combined["open_time"] = ((day_utc - epoch) // pd.Timedelta("1ms")).astype("int64")
    return combined[["open_time", "feature", "target"]]


def _write_report(payload: dict) -> None:
    header = " | ".join(payload["period_labels"])
    lines = [
        "# TASK-ALT-011 -- Family F (Options) DVOL/VRP-as-Predictor Diagnostic",
        "",
        "Per `docs/pre_registers/TASK-ALT-011.md` (ADR-0032). Free Deribit DVOL "
        "(keyless, ZERO cost) + DVOL-derived features vs 7d and 30d forward BTC/ETH "
        "return. Angle B (predictor for the perp strategy) -- NO options-book pivot. "
        "Pure diagnostic. BTC/ETH-only -> 2-asset pooled panel (low cross-sectional "
        "breadth, flagged). Sign-consistency across 3 sub-periods is the "
        "multiple-testing defense for the 8-cell grid.",
        "",
        f"Target: {payload['target']}, h in {payload['horizons_days']} days. "
        f"Threshold: |rho| >= {payload['magnitude_threshold']}.",
        "",
        "## Results",
        "",
        f"| Feature @ horizon | Full rho | n | Sub ({header}) | Sign consistent | Has info |",
        "|---|---:|---:|---|---|---|",
    ]
    for name, res in payload["results"].items():
        sub = " | ".join(
            "None" if sp["spearman_rho"] is None else f"{sp['spearman_rho']:+.4f}"
            for sp in res["sub_periods"]
        )
        rho = res["full_sample_rho"]
        rho_s = "None" if rho is None else f"{rho:+.4f}"
        lines.append(
            f"| {name} | {rho_s} | {res['full_sample_n']} | {sub} | "
            f"{res['sign_consistent']} | {res['has_information']} |"
        )
    hits = [n for n, r in payload["results"].items() if r["has_information"]]
    thr = payload["magnitude_threshold"]
    near = [
        n
        for n, r in payload["results"].items()
        if not r["has_information"]
        and r["full_sample_rho"] is not None
        and abs(r["full_sample_rho"]) >= thr
    ]
    verdict = (
        f"Features with information: {', '.join(hits)}. Each must pass the "
        "descriptive economic check (gross decile spread vs cost) before becoming a "
        "perp-strategy feature -- information is not a tradeable edge. A real edge "
        "would only THEN raise the larger Angle-A options-book decision."
        if hits
        else "No free-DVOL option-implied feature carries directional information at "
        "7d or 30d by the locked rule (|rho| >= 0.03 AND sign-consistent across the 3 "
        "sub-periods). The FREE options-signal angle closes: DVOL level, variance risk "
        "premium, DVOL shock, and IV/RV ratio do not predict BTC/ETH forward returns "
        "in this period. Pursuing options further would need paid surface/skew data or "
        "the Angle-A options-book pivot -- both user decisions. (Skew / 25-delta "
        "risk-reversal, needing the option chain, remains an untested free-ish "
        "follow-up.)"
    )
    lines.extend(["", "## Reading", "", verdict, ""])
    if near and not hits:
        lines.extend(
            [
                "### Documented near-miss (NOT a hit)",
                "",
                f"{', '.join(near)}: full-sample |rho| clears 0.03 but sign-consistency "
                "FAILS -- recorded, not promoted, no threshold adjustment. Note the "
                "2-asset (BTC/ETH) breadth: these are pooled daily obs, not a "
                "cross-sectional result.",
                "",
            ]
        )
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
