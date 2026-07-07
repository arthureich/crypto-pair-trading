#!/usr/bin/env python3
"""Diagnostic-only time-series momentum (trend-following) scan.

Autonomous pivot per this session's decision: cross-sectional momentum
(12h-7d) and cross-sectional Z-score micro-reversion (1h-4h) both aborted
at the diagnostic stage (see reports/momentum_diagnostic-equivalent
discussion in conversation and reports/zscore_diagnostic_tails.md). This
script tests a different mechanism: TIME-SERIES momentum -- does a
SINGLE asset's OWN trailing return predict its OWN forward return (trend
continuation), rather than ranking assets against each other. The
motivating idea: if a real trend exists at longer horizons (4h-24h), the
absolute size of the move captured could be large enough (hundreds of
bps) to dilute this project's fixed 6.0bps round-trip cost assumption to
a small fraction of the target, unlike the short-horizon signals already
tested.

Diagnostic only, not a pre-registered backtest. No new data.
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
REPORT_MD = PROJECT_ROOT / "reports/tsmom_diagnostic.md"
WINDOWS_HOURS = {"4h": 4, "8h": 8, "12h": 12, "24h": 24}
MIN_VALID_OBSERVATIONS = 100


def analyze_window(wide: pd.DataFrame, hours: int) -> dict:
    trailing = wide.diff(hours)
    forward = wide.shift(-hours).sub(wide)

    per_symbol_rows = []
    pooled_trailing = []
    pooled_forward = []
    for symbol in wide.columns:
        r = trailing[symbol]
        f = forward[symbol]
        valid = r.notna() & f.notna()
        r_valid = r[valid]
        f_valid = f[valid]
        if len(r_valid) < MIN_VALID_OBSERVATIONS:
            continue
        corr = r_valid.corr(f_valid)
        nonzero = r_valid != 0
        sign_persistence = float((np.sign(r_valid[nonzero]) == np.sign(f_valid[nonzero])).mean())
        per_symbol_rows.append(
            {
                "symbol": symbol,
                "n": int(valid.sum()),
                "corr": corr,
                "sign_persistence": sign_persistence,
            }
        )
        pooled_trailing.append(r_valid)
        pooled_forward.append(f_valid)

    per_symbol_df = pd.DataFrame(per_symbol_rows)
    pooled_r = pd.concat(pooled_trailing)
    pooled_f = pd.concat(pooled_forward)
    pooled_corr = pooled_r.corr(pooled_f)
    nonzero_mask = pooled_r != 0
    pooled_sign_persistence = float(
        (np.sign(pooled_r[nonzero_mask]) == np.sign(pooled_f[nonzero_mask])).mean()
    )

    # Conditional magnitude: when the trend DOES continue vs reverses, how big (bps) is the move?
    continued_mask = np.sign(pooled_r) == np.sign(pooled_f)
    reversed_mask = ~continued_mask
    continued_abs_bps = float((pooled_f[continued_mask].abs() * 10_000.0).mean())
    reversed_abs_bps = float((pooled_f[reversed_mask].abs() * 10_000.0).mean())

    # Extreme-decile trailing move: does a big trailing move predict a big, continued forward move?
    abs_r = pooled_r.abs()
    top_decile_cutoff = abs_r.quantile(0.90)
    extreme_mask = abs_r >= top_decile_cutoff
    extreme_sign_persistence = float(
        (np.sign(pooled_r[extreme_mask]) == np.sign(pooled_f[extreme_mask])).mean()
    )
    extreme_directional = pooled_f[extreme_mask] * np.sign(pooled_r[extreme_mask]) * 10_000.0
    extreme_forward_bps = float(extreme_directional.mean())

    return {
        "window": f"{hours}h",
        "per_symbol": per_symbol_df,
        "pooled_corr": pooled_corr,
        "pooled_sign_persistence": pooled_sign_persistence,
        "continued_abs_bps": continued_abs_bps,
        "reversed_abs_bps": reversed_abs_bps,
        "extreme_decile_cutoff_bps": float(top_decile_cutoff * 10_000.0),
        "extreme_sign_persistence": extreme_sign_persistence,
        "extreme_forward_directional_bps": extreme_forward_bps,
        "n_pooled": len(pooled_r),
    }


def main() -> int:
    df = pd.read_csv(BARS_CSV, usecols=["symbol", "open_time", "log_price"])
    wide = df.pivot(index="open_time", columns="symbol", values="log_price").sort_index()

    summaries = []
    per_symbol_tables = {}
    for name, hours in WINDOWS_HOURS.items():
        result = analyze_window(wide, hours)
        per_symbol_tables[name] = result.pop("per_symbol")
        summaries.append(result)
        print(f"-- window={name} --")
        for key, value in result.items():
            if key != "window":
                print(f"  {key}: {value}")
        print()

    _write_report(summaries, per_symbol_tables)
    print(f"Wrote {REPORT_MD}")
    return 0


def _write_report(summaries: list[dict], per_symbol_tables: dict[str, pd.DataFrame]) -> None:
    lines = [
        "# Time-Series Momentum (Trend Following) Diagnostic",
        "",
        "Diagnostic only, not a pre-registered backtest. Autonomous pivot after",
        "cross-sectional momentum (12h-7d) and cross-sectional Z-score",
        "micro-reversion (1h-4h) both aborted at the diagnostic stage this",
        "session (see reports/zscore_diagnostic_tails.md). Tests whether an",
        "asset's OWN trailing return predicts its OWN forward return",
        "(time-series momentum), matched formation/holding horizon, on the",
        "existing 20-symbol Sprint 7 dataset. No new data.",
        "",
        "## Summary by window",
        "",
        "| Window | Pooled corr(trailing, forward) | Pooled sign persistence | "
        "Continued move avg (bps) | Reversed move avg (bps) | Extreme-decile "
        "cutoff (bps) | Extreme-decile sign persistence | Extreme-decile "
        "directional forward (bps) | n |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summaries:
        lines.append(
            f"| {s['window']} | {s['pooled_corr']:.4f} | {s['pooled_sign_persistence']:.4f} | "
            f"{s['continued_abs_bps']:.2f} | {s['reversed_abs_bps']:.2f} | "
            f"{s['extreme_decile_cutoff_bps']:.2f} | {s['extreme_sign_persistence']:.4f} | "
            f"{s['extreme_forward_directional_bps']:.2f} | {s['n_pooled']} |"
        )
    lines += [
        "",
        "`Pooled sign persistence`: fraction of all (symbol, time) observations",
        "where the forward return has the SAME sign as the trailing return",
        "(trend continuation). 0.50 = coin flip (no time-series momentum or",
        "reversal); >0.50 = momentum; <0.50 = reversal.",
        "",
        "`Extreme-decile`: restricted to the top 10% largest |trailing return|",
        'observations (pooled across symbols) -- the "real trend" subset the',
        "TSMOM hypothesis actually targets, not small/noisy moves.",
        "`Extreme-decile directional forward (bps)`: mean of "
        "sign(trailing_return) * forward_return for that subset -- positive",
        "means the extreme trend, on average, continued in the same direction",
        "by that many bps (this is the metric to compare against the 6.0bps",
        'round-trip cost floor and the "300-500bps target" framing).',
        "",
        "## Per-symbol detail (24h window)",
        "",
        "```text",
        per_symbol_tables.get("24h", pd.DataFrame()).to_string(index=False),
        "```",
        "",
    ]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
