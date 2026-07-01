#!/usr/bin/env python3
"""Run Sprint 7 stationarity, Kalman, and OU checks on real normalized bars."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research import (  # noqa: E402
    AnalysisScope,
    KalmanFilterConfig,
    assess_stationarity,
    estimate_ou,
    fit_kalman_filter,
    rolling_zscore,
)

DEFAULT_ZSCORE_WINDOW = 168
MAX_OPERATIONAL_HALF_LIFE_HOURS = 240.0
MIN_PAIR_OBSERVATIONS = 500


def main() -> int:
    args = _parse_args()
    bars = pd.read_csv(args.bars_csv, low_memory=False)
    summary = json.loads(args.summary_json.read_text(encoding="utf-8"))
    candidate_pairs = summary.get("candidate_pairs", [])
    if args.max_pairs is not None:
        candidate_pairs = candidate_pairs[: args.max_pairs]

    results = [
        _evaluate_pair(
            bars=bars,
            pair_id=str(candidate["pair"]),
            pair_selection_score=_finite_float(candidate.get("score")),
            pair_selection_correlation=_finite_float(candidate.get("correlation")),
            funding_carry_bps_per_day=_finite_float(candidate.get("funding_carry_bps_per_day")),
            zscore_window=args.zscore_window,
        )
        for candidate in candidate_pairs
    ]
    accepted = [result for result in results if result["statistical_status"] == "ACCEPT"]
    rejected = [result for result in results if result["statistical_status"] == "REJECT"]
    cost_gate_reason = (
        "verified historical top-of-book/L2 execution-cost evidence is unavailable"
    )
    payload = {
        "bars_csv": str(args.bars_csv),
        "summary_json": str(args.summary_json),
        "dataset_version": summary.get(
            "dataset_version",
            args.summary_json.stem.removesuffix("_summary"),
        ),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "candidate_pairs_evaluated": len(results),
        "statistical_pairs_accepted": len(accepted),
        "statistical_pairs_rejected": len(rejected),
        "cost_gated_pass": False,
        "cost_gate_reason": cost_gate_reason,
        "gate_note": (
            "Statistical-only Sprint 7 research gate. Cost-gated PASS remains false "
            "until verified historical top-of-book/L2 execution-cost evidence exists."
        ),
        "accepted_pairs": accepted,
        "rejected_pairs": rejected,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _write_csv(args.output_csv, results)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _evaluate_pair(
    *,
    bars: pd.DataFrame,
    pair_id: str,
    pair_selection_score: float,
    pair_selection_correlation: float,
    funding_carry_bps_per_day: float,
    zscore_window: int,
) -> dict[str, Any]:
    symbol_a, symbol_b = pair_id.split("/", maxsplit=1)
    pair_bars = _pair_frame(bars, symbol_a=symbol_a, symbol_b=symbol_b)
    kalman = fit_kalman_filter(
        y=pair_bars["log_price_a"].to_numpy(dtype=float),
        x=pair_bars["log_price_b"].to_numpy(dtype=float),
        config=KalmanFilterConfig(initial_beta=1.0),
    )
    spread = pd.Series(kalman.spread, name="spread")
    stationarity = assess_stationarity(
        spread,
        max_half_life=MAX_OPERATIONAL_HALF_LIFE_HOURS,
        min_observations=MIN_PAIR_OBSERVATIONS,
        stability_window=min(zscore_window, max(24, len(spread) // 4)),
        scope=AnalysisScope.FULL_SAMPLE_EXPLORATORY,
    )
    ou = estimate_ou(spread, min_observations=MIN_PAIR_OBSERVATIONS)
    zscore = rolling_zscore(
        spread,
        window=min(zscore_window, len(spread)),
        min_periods=min(zscore_window, len(spread)),
    )
    latest_zscore = _last_finite(zscore)
    statistical_accept = (
        stationarity.accepted
        and ou.mean_reverting
        and not kalman.beta_unstable
        and math.isfinite(ou.half_life)
        and ou.half_life <= MAX_OPERATIONAL_HALF_LIFE_HOURS
    )
    reasons = list(stationarity.reasons)
    if not ou.mean_reverting:
        reasons.append("OU_NOT_MEAN_REVERTING")
    if ou.mean_reverting and ou.half_life > MAX_OPERATIONAL_HALF_LIFE_HOURS:
        reasons.append("OU_HALF_LIFE_TOO_LONG")
    if kalman.beta_unstable:
        reasons.extend(kalman.unstable_reasons)

    return {
        "pair": pair_id,
        "statistical_status": "ACCEPT" if statistical_accept else "REJECT",
        "cost_gated_pass": False,
        "observations": int(len(pair_bars)),
        "pair_selection_score": pair_selection_score,
        "pair_selection_correlation": pair_selection_correlation,
        "funding_carry_bps_per_day": funding_carry_bps_per_day,
        "kalman_beta_latest": float(kalman.beta[-1]),
        "kalman_alpha_latest": float(kalman.alpha[-1]),
        "kalman_beta_unstable": bool(kalman.beta_unstable),
        "adf_p_value": float(stationarity.adf.p_value),
        "kpss_p_value": float(stationarity.kpss.p_value),
        "stationarity_status": stationarity.status.value,
        "preliminary_half_life": float(stationarity.half_life.half_life),
        "ou_status": ou.status.value,
        "ou_theta": float(ou.theta),
        "ou_mu": float(ou.mu),
        "ou_sigma": float(ou.sigma),
        "ou_half_life": float(ou.half_life),
        "latest_rolling_zscore": latest_zscore,
        "reasons": reasons,
    }


def _pair_frame(bars: pd.DataFrame, *, symbol_a: str, symbol_b: str) -> pd.DataFrame:
    required = {"symbol", "open_time", "log_price"}
    missing = required.difference(bars.columns)
    if missing:
        raise ValueError(f"bars CSV missing required columns: {sorted(missing)}")
    left = (
        bars.loc[bars["symbol"] == symbol_a, ["open_time", "log_price"]]
        .rename(columns={"log_price": "log_price_a"})
        .copy()
    )
    right = (
        bars.loc[bars["symbol"] == symbol_b, ["open_time", "log_price"]]
        .rename(columns={"log_price": "log_price_b"})
        .copy()
    )
    joined = left.merge(right, on="open_time", how="inner", sort=True).dropna()
    if len(joined) < MIN_PAIR_OBSERVATIONS:
        raise ValueError(f"{symbol_a}/{symbol_b} has only {len(joined)} aligned observations")
    return joined.reset_index(drop=True)


def _write_csv(path: Path, results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = (
        "pair",
        "statistical_status",
        "cost_gated_pass",
        "observations",
        "pair_selection_score",
        "pair_selection_correlation",
        "funding_carry_bps_per_day",
        "kalman_beta_latest",
        "kalman_alpha_latest",
        "kalman_beta_unstable",
        "adf_p_value",
        "kpss_p_value",
        "stationarity_status",
        "preliminary_half_life",
        "ou_status",
        "ou_theta",
        "ou_mu",
        "ou_sigma",
        "ou_half_life",
        "latest_rolling_zscore",
        "reasons",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for result in results:
            row = result.copy()
            row["reasons"] = ";".join(str(reason) for reason in row["reasons"])
            writer.writerow({column: row.get(column) for column in columns})


def _finite_float(value: object) -> float:
    numeric = float(value)
    return numeric if math.isfinite(numeric) else math.nan


def _last_finite(values: pd.Series) -> float:
    finite = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if finite.empty:
        return math.nan
    return float(finite.iloc[-1])


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bars-csv", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--max-pairs", type=int)
    parser.add_argument("--zscore-window", type=int, default=DEFAULT_ZSCORE_WINDOW)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
