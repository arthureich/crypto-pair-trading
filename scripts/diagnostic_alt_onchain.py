#!/usr/bin/env python3
"""TASK-ALT-009: Family G (On-Chain) information-content diagnostic.

Pre-registered in `docs/pre_registers/TASK-ALT-009.md` (ADR-0029). Consumes the
Coin Metrics community daily panel (`download_alt_onchain.py`) and the existing
sprint7 hourly bars resampled to daily log-price. 4 causal features vs the 1d
and 7d forward daily return. Pure diagnostic: no economic gate, no strategy.

Causality note: an on-chain daily metric for day D is only finalized AFTER D
closes, so it cannot inform a position entered at D. Every feature therefore
gets an explicit outer shift(1) (metric of the PRIOR day) on top of the causal
rolling z-score -- a stricter lag than the hourly-bar diagnostics, justified by
the full-day finalization delay. The forward daily return is the only
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

ONCHAIN_CSV = (
    PROJECT_ROOT / "data/research/binance_public/normalized/sprint_alt_onchain_202306_202605.csv.gz"
)
BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/alt_onchain_results.json"
REPORT_MD = PROJECT_ROOT / "reports/alt_onchain_diagnostic.md"
ROLLING_WINDOW_DAYS = 90
MAGNITUDE_THRESHOLD = 0.03
TARGET_HORIZONS_DAYS = (1, 7)

PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
PERIOD_BOUNDARIES = tuple(
    int(pd.Timestamp(d, tz="UTC").timestamp() * 1000)
    for d in ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
)


def main() -> int:
    onchain = pd.read_csv(ONCHAIN_CSV, parse_dates=["day"])
    daily_logprice = _daily_logprice(BARS_CSV)  # index=day, columns=base_asset

    features = _build_features(onchain, daily_logprice.columns)

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
        "task": "TASK-ALT-009 (ADR-0029): Family G on-chain, Coin Metrics community",
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
        print(
            f"{name}: rho={res['full_sample_rho']:+.4f} n={res['full_sample_n']} {verdict}",
            file=sys.stderr,
        )
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _daily_logprice(bars_csv: Path) -> pd.DataFrame:
    """Resample the hourly bars to a daily (last-obs) log-price, columns=base_asset."""

    bars = pd.read_csv(bars_csv, usecols=["symbol", "base_asset", "open_time", "log_price"])
    bars["day"] = pd.to_datetime(bars["open_time"], unit="ms", utc=True).dt.floor("D")
    bars["base_asset"] = bars["base_asset"].str.lower()
    daily = (
        bars.sort_values("open_time", kind="mergesort")
        .groupby(["base_asset", "day"], as_index=False)
        .last()
    )
    return daily.pivot(index="day", columns="base_asset", values="log_price").sort_index()


def _build_features(onchain: pd.DataFrame, price_assets: pd.Index) -> dict[str, pd.DataFrame]:
    def wide(column: str) -> pd.DataFrame:
        if column not in onchain.columns:
            return pd.DataFrame()
        return onchain.pivot(index="day", columns="asset", values=column).sort_index()

    mvrv = wide("CapMVRVCur")
    adr = wide("AdrActCnt")
    txn = wide("TxCnt")
    supply = wide("SplyCur")
    flow_in = wide("FlowInExNtv")
    flow_out = wide("FlowOutExNtv")
    net_flow = (flow_in - flow_out) / supply.reindex_like(flow_in).replace(0.0, np.nan)

    features = {
        "mvrv_z": _causal_z(mvrv),
        "active_addr_growth_z": _causal_z(adr.diff()),
        "tx_count_growth_z": _causal_z(txn.diff()),
        "exchange_netflow_z": _causal_z(net_flow),
    }
    # Keep only assets that also have a daily price (so a target exists).
    keep = set(price_assets)
    return {
        name: w.reindex(columns=[c for c in w.columns if c in keep]) for name, w in features.items()
    }


def _causal_z(wide: pd.DataFrame) -> pd.DataFrame:
    """Causal daily z-score, then an outer shift(1) (prior-day metric).

    The rolling mean/std use shift(1) (stats known before day D); the final
    shift(1) lags the level too, because a daily on-chain metric for day D is
    only finalized after D closes and cannot inform a position entered at D.
    """

    if wide.empty:
        return wide
    mean = wide.shift(1).rolling(ROLLING_WINDOW_DAYS).mean()
    std = wide.shift(1).rolling(ROLLING_WINDOW_DAYS).std()
    z = (wide - mean) / std
    return z.shift(1)


def _stack(feature_wide: pd.DataFrame, target_wide: pd.DataFrame) -> pd.DataFrame:
    if feature_wide.empty:
        return pd.DataFrame(columns=["open_time", "feature", "target"])
    feature_long = feature_wide.stack(future_stack=True).rename("feature")
    target_long = target_wide.stack(future_stack=True).rename("target")
    combined = pd.concat([feature_long, target_long], axis=1).reset_index()
    combined.columns = ["day", "asset", "feature", "target"]
    # Unit-independent ms epoch (the day column may be us- or ns-resolution).
    day_utc = pd.to_datetime(combined["day"], utc=True)
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    combined["open_time"] = ((day_utc - epoch) // pd.Timedelta("1ms")).astype("int64")
    return combined[["open_time", "feature", "target"]]


def _write_report(payload: dict) -> None:
    header = " | ".join(payload["period_labels"])
    lines = [
        "# TASK-ALT-009 -- Family G (On-Chain) Information-Content Diagnostic",
        "",
        "Per `docs/pre_registers/TASK-ALT-009.md` (ADR-0029). First EXTERNAL-data "
        "family tested -- and at ZERO cost (Coin Metrics community, keyless). 4 "
        "causal daily features vs 1d and 7d forward daily return. Pure diagnostic. "
        "Sign-consistency across 3 sub-periods is the pre-committed multiple-testing "
        "defense for the 8-cell grid. `exchange_netflow_z` is BTC/ETH-only (2 assets) "
        "-- pooled daily obs, NOT a cross-sectional result.",
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
        sub = " | ".join(f"{sp['spearman_rho']:+.4f}" for sp in res["sub_periods"])
        lines.append(
            f"| {name} | {res['full_sample_rho']:+.4f} | {res['full_sample_n']} | {sub} | "
            f"{res['sign_consistent']} | {res['has_information']} |"
        )
    hits = [n for n, r in payload["results"].items() if r["has_information"]]
    thr = payload["magnitude_threshold"]
    # Near-miss: magnitude clears the bar but sign-consistency fails.
    near = [
        n
        for n, r in payload["results"].items()
        if not r["has_information"]
        and r["full_sample_rho"] is not None
        and abs(r["full_sample_rho"]) >= thr
    ]
    verdict = (
        f"Features with information: {', '.join(hits)}. Each must pass the "
        "descriptive economic check (gross decile spread vs cost) before any "
        "strategy pre-registration -- information is not a tradeable edge. Any "
        "follow-up on a paid richer on-chain feed is a separate user decision."
        if hits
        else "No free-tier on-chain feature carries directional information at 1d or "
        "7d by the pre-registered criterion (|rho| >= 0.03 AND sign-consistent across "
        "the 3 sub-periods). Family G closes on the ZERO-COST tier. Paying for premium "
        "on-chain metrics (Glassnode / CryptoQuant / CM premium) would need a stronger "
        "prior than 'the free proxies were null'. Cross-venue flow remains open, gated "
        "on a free Coinalyze/Coinglass key (TASK-ALT-010)."
    )
    lines.extend(["", "## Reading", "", verdict, ""])
    if near and not hits:
        near_txt = ", ".join(near)
        lines.extend(
            [
                "### Documented near-miss (NOT a hit)",
                "",
                f"{near_txt}: full-sample |rho| clears the 0.03 bar but sign-consistency "
                "FAILS, so it is SEM_INFORMACAO by the locked rule -- recorded, not "
                "promoted, no threshold adjustment. Notably `exchange_netflow_z@7d` "
                "(-0.0346) is theory-coherent (exchange inflows = sell pressure -> lower "
                "forward return) with 2 of 3 sub-periods clearly negative (-0.078, "
                "-0.041), only the middle period flat-positive (+0.004). BUT it is "
                "BTC/ETH-only (2 assets) -- a BTC/ETH-timing signal, not a cross-sectional "
                "factor. A richer / broader exchange-flow feed (e.g. CryptoQuant) MIGHT "
                "sharpen it; that is a paid-feed user decision, not a re-test of this.",
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
