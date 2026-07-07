#!/usr/bin/env python3
"""Diagnostic-only tail analysis for cross-sectional Z-score micro-reversion.

Not a pre-registered backtest -- a cheap, honest diagnostic to decide
whether the Z-score cross-sectional reversion hypothesis (proposed this
session) is worth a full pre-registration and implementation, before
spending that effort. Slices the reversion metric already explored
informally (see reports/funding_carry_incremental_backtest.md's sibling
diagnostics in conversation) by |Z| threshold and by long/short side, on
the existing Sprint 7 normalized dataset (no new data).

Reversion metric: for a symbol with cross-sectional return Z-score Z at
time t (formation window W), reversion_bps = -sign(Z) * forward_return(H) *
10000. Positive means the extreme move reverted; negative means it
continued (or reprice-and-stay).

Prints a single machine-readable decision line at the end:
    DECISION: PROCEED
or
    DECISION: ABORT
based on the mean reversion_bps for the (formation=1h, forward=1h,
threshold=|Z|>3.0, combined long+short) slice versus a 10.0 bps bar.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
REPORT_MD = PROJECT_ROOT / "reports/zscore_diagnostic_tails.md"
THRESHOLDS = (2.0, 2.5, 3.0, 3.5)
FORMATION_WINDOWS = {"1h": 1, "2h": 2}
FORWARD_HOURS = 1  # forward=1h showed the best mean in the prior informal scan
DECISION_FORMATION = "1h"
DECISION_THRESHOLD = 3.0
DECISION_BAR_BPS = 10.0
VOL_LOOKBACK_HOURS = 720  # 30 days, same convention already used for residual momentum


def build_merged_frame(
    wide: pd.DataFrame, formation_hours: int, forward_hours: int
) -> pd.DataFrame:
    ret = wide.diff(formation_hours)
    cross_mean = ret.mean(axis=1)
    cross_std = ret.std(axis=1)
    z = ret.sub(cross_mean, axis=0).div(cross_std, axis=0)
    forward_ret = wide.shift(-forward_hours).sub(wide)

    z_long = z.stack().rename("z")
    fwd_long = forward_ret.stack().rename("fwd")
    merged = pd.concat([z_long, fwd_long], axis=1).dropna()
    merged["reversion_bps"] = -np.sign(merged["z"]) * merged["fwd"] * 10_000.0
    merged["side"] = np.where(merged["z"] > 0, "SHORT", "LONG")
    return merged


def slice_stats(merged: pd.DataFrame, threshold: float, side_mask: pd.Series) -> dict:
    subset = merged.loc[side_mask, "reversion_bps"]
    n = len(subset)
    return {
        "n": n,
        "mean_bps": float(subset.mean()) if n > 0 else float("nan"),
        "median_bps": float(subset.median()) if n > 0 else float("nan"),
        "frac_positive": float((subset > 0).mean()) if n > 0 else float("nan"),
    }


def main() -> int:
    df = pd.read_csv(BARS_CSV, usecols=["symbol", "open_time", "log_price"])
    wide = df.pivot(index="open_time", columns="symbol", values="log_price").sort_index()

    rows = []
    merged_by_formation = {}
    for formation_name, w in FORMATION_WINDOWS.items():
        merged = build_merged_frame(wide, w, FORWARD_HOURS)
        merged_by_formation[formation_name] = merged
        for threshold in THRESHOLDS:
            combined_mask = merged["z"].abs() > threshold
            long_mask = merged["z"] < -threshold
            short_mask = merged["z"] > threshold
            for side_label, mask in (
                ("COMBINED", combined_mask),
                ("LONG", long_mask),
                ("SHORT", short_mask),
            ):
                stats = slice_stats(merged, threshold, mask)
                rows.append(
                    {
                        "formation": formation_name,
                        "forward": f"{FORWARD_HOURS}h",
                        "threshold": threshold,
                        "side": side_label,
                        **stats,
                    }
                )
    results_df = pd.DataFrame(rows)
    print(results_df.to_string(index=False))

    # Point 3: is the extreme-Z tail dominated by a handful of high-idiosyncratic-vol symbols?
    decision_merged = merged_by_formation[DECISION_FORMATION]
    hourly_ret = wide.diff(1)
    hist_vol = hourly_ret.rolling(VOL_LOOKBACK_HOURS, min_periods=168).std()
    tail_mask = decision_merged["z"].abs() > DECISION_THRESHOLD
    tail_symbols = decision_merged.loc[tail_mask].index.get_level_values(1)
    tail_symbol_counts = tail_symbols.value_counts()
    print(f"\nSymbol frequency in |Z| > {DECISION_THRESHOLD:.1f} tail (top 8):")
    print(tail_symbol_counts.head(8).to_string())

    formation_hours = FORMATION_WINDOWS[DECISION_FORMATION]
    formation_ret = wide.diff(formation_hours)
    vol_scaled_metric = formation_ret / hist_vol
    vol_scaled_long = vol_scaled_metric.stack().rename("vol_scaled")
    corr_frame = pd.concat([decision_merged["z"], vol_scaled_long], axis=1).dropna()
    corr = corr_frame["z"].corr(corr_frame["vol_scaled"])
    print(f"\ncorr(cross-sectional Z, asset's-own-vol-scaled return) = {corr:.4f}")

    # Primary decision test
    decision_row = results_df[
        (results_df["formation"] == DECISION_FORMATION)
        & (results_df["threshold"] == DECISION_THRESHOLD)
        & (results_df["side"] == "COMBINED")
    ].iloc[0]
    decision_mean_bps = decision_row["mean_bps"]
    decision = "PROCEED" if decision_mean_bps >= DECISION_BAR_BPS else "ABORT"

    _write_report(results_df, tail_symbol_counts, corr, decision_mean_bps, decision)

    print(
        f"\nDecision test: formation={DECISION_FORMATION}, forward={FORWARD_HOURS}h, "
        f"|Z|>{DECISION_THRESHOLD}, COMBINED long+short mean reversion = "
        f"{decision_mean_bps:.3f} bps (bar = {DECISION_BAR_BPS} bps)"
    )
    print(f"DECISION: {decision}")
    return 0


def _write_report(
    results_df: pd.DataFrame,
    tail_symbol_counts: pd.Series,
    vol_scaled_corr: float,
    decision_mean_bps: float,
    decision: str,
) -> None:
    lines = [
        "# Z-Score Cross-Sectional Reversion: Tail Diagnostic",
        "",
        "Diagnostic only, not a pre-registered backtest. Answers whether the",
        "reversion signal observed informally this session strengthens at more",
        "extreme |Z| thresholds, whether long/short sides are asymmetric, and",
        "whether the extreme tail is dominated by a handful of high-vol symbols.",
        "",
        "## Full slice table",
        "",
        "```text",
        results_df.to_string(index=False),
        "```",
        "",
        f"## Symbol concentration in the |Z| > {DECISION_THRESHOLD} tail "
        f"(formation={DECISION_FORMATION})",
        "",
        "```text",
        tail_symbol_counts.head(8).to_string(),
        "```",
        "",
        "## Volatility-scaling check",
        "",
        f"corr(cross-sectional Z, asset's-own-30d-vol-scaled return) = {vol_scaled_corr:.4f}",
        "",
        "## Decision",
        "",
        f"Primary test: formation={DECISION_FORMATION}, forward={FORWARD_HOURS}h, "
        f"|Z|>{DECISION_THRESHOLD}, COMBINED long+short mean reversion = "
        f"{decision_mean_bps:.3f} bps (bar = {DECISION_BAR_BPS} bps).",
        "",
        f"**DECISION: {decision}**",
        "",
    ]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
