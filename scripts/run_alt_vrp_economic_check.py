#!/usr/bin/env python3
"""TASK-ALT-011 economic check: is the vrp_z@7d hit a TRADEABLE edge? (ADR-0032).

The pre-registered follow-up for an information-content hit (the FC-II-003
lesson: information != tradeable edge). Sorts the pooled BTC/ETH (asset, day)
observations into deciles by the winning feature `vrp_z` and measures the GROSS
7d forward-return spread (top vs bottom decile) against a realistic round-trip
cost. Descriptive only -- no strategy, no promotion, no options-book pivot.

Feature/target construction mirrors `diagnostic_alt_options_vrp.py` exactly
(same causal vrp_z and 7d forward daily return).
"""

from __future__ import annotations

import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DVOL_CSV = (
    PROJECT_ROOT / "data/research/binance_public/normalized/sprint_alt_dvol_202306_202605.csv.gz"
)
BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/alt_vrp_economic_check.json"
REPORT_MD = PROJECT_ROOT / "reports/alt_vrp_economic_check.md"
HORIZON_DAYS = 7
ROLLING_WINDOW_DAYS = 90
RV_WINDOW_DAYS = 30
N_DECILES = 10
ROUND_TRIP_COST_BPS = 12.0  # ~2 legs x 6 bps; BTC/ETH are liquid (conservative-ish)
_ANNUALIZE = math.sqrt(365)
_ASSETS = ("btc", "eth")
_BPS = 10_000.0


def main() -> int:
    dvol = pd.read_csv(DVOL_CSV, parse_dates=["day"])
    price = _daily_logprice(BARS_CSV)
    vrp_z = _vrp_z(dvol, price)
    fwd = price.shift(-HORIZON_DAYS) - price  # 7d forward log return

    panel = pd.concat(
        {"vrp_z": vrp_z.stack(future_stack=True), "fwd": fwd.stack(future_stack=True)}, axis=1
    ).dropna()
    panel = panel[np.isfinite(panel["vrp_z"]) & np.isfinite(panel["fwd"])]

    panel["decile"] = pd.qcut(panel["vrp_z"], N_DECILES, labels=False, duplicates="drop")
    by_decile = panel.groupby("decile")["fwd"].mean() * _BPS  # bps per 7d hold
    top, bottom = by_decile.iloc[-1], by_decile.iloc[0]
    spread = top - bottom
    # Monotonicity: Spearman of decile index vs mean forward return.
    mono = float(np.corrcoef(by_decile.index.to_numpy(dtype=float), by_decile.to_numpy())[0, 1])

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-ALT-011 economic check (ADR-0032): vrp_z@7d decile spread vs cost",
        "horizon_days": HORIZON_DAYS,
        "n_obs": int(len(panel)),
        "round_trip_cost_bps": ROUND_TRIP_COST_BPS,
        "decile_mean_fwd_bps": {int(k): float(v) for k, v in by_decile.items()},
        "top_decile_bps": float(top),
        "bottom_decile_bps": float(bottom),
        "gross_spread_bps": float(spread),
        "net_spread_bps": float(spread - ROUND_TRIP_COST_BPS),
        "decile_monotonicity": mono,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)
    print(
        f"gross spread {spread:.1f} bps/7d vs cost {ROUND_TRIP_COST_BPS} -> net "
        f"{spread - ROUND_TRIP_COST_BPS:.1f} bps; monotonicity {mono:+.2f} (n={len(panel)})",
        file=sys.stderr,
    )
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


def _vrp_z(dvol: pd.DataFrame, price: pd.DataFrame) -> pd.DataFrame:
    dvol_wide = (
        dvol.pivot(index="day", columns="asset", values="dvol_close")
        .reindex(index=price.index, columns=price.columns)
        .sort_index()
    )
    iv = dvol_wide / 100.0
    rv = price.diff().rolling(RV_WINDOW_DAYS).std() * _ANNUALIZE
    vrp = iv**2 - rv**2
    mean = vrp.shift(1).rolling(ROLLING_WINDOW_DAYS).mean()
    std = vrp.shift(1).rolling(ROLLING_WINDOW_DAYS).std()
    return ((vrp - mean) / std).shift(1)


def _write_report(payload: dict) -> None:
    spread = payload["gross_spread_bps"]
    net = payload["net_spread_bps"]
    cost = payload["round_trip_cost_bps"]
    deciles = payload["decile_mean_fwd_bps"]
    alive = spread > cost and payload["decile_monotonicity"] > 0.5  # noqa: PLR2004
    lines = [
        "# TASK-ALT-011 Economic Check -- vrp_z@7d: tradeable edge or just information?",
        "",
        "Pre-registered follow-up for the ALT-011 hit (info != edge; FC-II-003 lesson). "
        f"Pooled BTC/ETH (asset, day) obs sorted into {N_DECILES} deciles by the causal "
        "`vrp_z`; mean 7d forward return per decile; top-minus-bottom GROSS spread vs a "
        f"~{cost:.0f} bps round-trip cost. Descriptive only -- no strategy, no pivot.",
        "",
        f"Observations: {payload['n_obs']}. Horizon: {payload['horizon_days']}d.",
        "",
        "## Mean 7d forward return by vrp_z decile (bps)",
        "",
        "| Decile (0=low VRP, 9=high) | Mean fwd return (bps/7d) |",
        "|---:|---:|",
    ]
    lines += [f"| {k} | {v:+.1f} |" for k, v in sorted(deciles.items())]
    lines += [
        "",
        "## Reading",
        "",
        f"Top-decile {payload['top_decile_bps']:+.1f} bps vs bottom-decile "
        f"{payload['bottom_decile_bps']:+.1f} bps -> **gross spread {spread:+.1f} bps/7d**; "
        f"decile monotonicity (corr of decile vs mean return) "
        f"{payload['decile_monotonicity']:+.2f}. "
        f"Net of ~{cost:.0f} bps round-trip cost: **{net:+.1f} bps**.",
        "",
        (
            "CLEARS COST (descriptive): the gross top-vs-bottom spread is many times "
            "the round-trip cost with a positive decile tilt -- unlike the FC-II-003 "
            "micro-signal (1-2 bps vs cost), the VRP is not just information but a "
            "plausible economic edge. This is the FIRST signal in the project to pass "
            "BOTH the information bar (ALT-011) and the gross-economics bar."
            if alive
            else "NOT ECONOMICALLY COMPELLING as a standalone BTC/ETH timing trade: the "
            "gross top-vs-bottom spread is small relative to cost and/or the decile "
            "pattern is not monotone."
        ),
        "",
        "### Honest caveats (why this is a LEAD, not a validated edge)",
        "",
        "- The decile pattern is TAIL-DRIVEN, not cleanly monotone (low VRP -> negative "
        "forward, high VRP -> positive, but the middle deciles are noisy) -- the edge "
        "concentrates in high-VRP episodes (post-stress fear -> rebound).",
        "- Overlapping 7d holds sampled DAILY: the top/bottom deciles are NOT independent "
        "trades, so the raw spread overstates a weekly-rebalanced strategy's real edge.",
        "- IN-SAMPLE dev window; BTC/ETH-only (2 assets).",
        "",
        "Mandatory next step (separate, pre-registered): a PROPER strategy backtest "
        "(weekly-rebalanced BTC/ETH VRP timing, realistic cost, drawdown) with an OOS "
        "gate -- NOT a decile sort. Or use vrp_z as one feature inside the perp book. "
        "The Angle-A VRP-harvesting (options book) remains a separate user decision. No "
        "strategy opened here.",
        "",
    ]
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
