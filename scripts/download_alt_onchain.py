#!/usr/bin/env python3
"""TASK-ALT-009: pull Family G (on-chain) metrics from Coin Metrics community.

Keyless, zero-cost community tier at 1d frequency. Pre-registered in
`docs/pre_registers/TASK-ALT-009.md` (ADR-0029). Coverage was established by
catalog reconnaissance: exchange flows (BTC/ETH only), MVRV / active addresses
/ tx count / supply (~12-13 of our 20 base assets). Writes a tidy daily panel;
the diagnostic (`diagnostic_alt_onchain.py`) consumes it.

The pure parse/normalize functions (`tidy_rows`, `build_panel`) are unit-tested
against a fixture in `tests/test_download_alt_onchain.py`; only `_fetch_metric`
touches the network (no network mock, same accepted precedent as the S3
downloaders).
"""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from functools import reduce
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import json  # noqa: E402

API_ROOT = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
START = "2023-06-01"
END = "2026-05-31"
OUTPUT = (
    PROJECT_ROOT / "data/research/binance_public/normalized/sprint_alt_onchain_202306_202605.csv.gz"
)
PAGE_SIZE = 10_000
_MAX_RETRIES = 4
_TIMEOUT_S = 30

# Asset coverage groups (from ADR-0029 catalog reconnaissance, 1d community).
_VALUATION = ("ada", "bch", "bnb", "btc", "doge", "dot", "etc", "eth", "link", "ltc", "uni", "xrp")
_ACTIVITY = (*_VALUATION[:9], "ltc", "trx", "uni", "xrp")  # + trx, same order otherwise
_FLOW = ("btc", "eth")

# Metric -> assets with 1d community coverage.
COVERAGE: dict[str, tuple[str, ...]] = {
    "CapMVRVCur": _VALUATION,
    "AdrActCnt": _ACTIVITY,
    "TxCnt": _ACTIVITY,
    "SplyCur": _VALUATION,
    "FlowInExNtv": _FLOW,
    "FlowOutExNtv": _FLOW,
}


def main() -> int:
    frames = []
    for metric, assets in COVERAGE.items():
        rows = _fetch_metric(metric, assets)
        tidy = tidy_rows(rows, metric)
        print(f"{metric}: {len(tidy)} rows, {tidy['asset'].nunique()} assets", file=sys.stderr)
        frames.append(tidy)

    panel = build_panel(frames)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(OUTPUT, index=False, compression="gzip")
    print(f"Wrote {OUTPUT}: {len(panel)} (asset,day) rows", file=sys.stderr)
    return 0


def _fetch_metric(metric: str, assets: tuple[str, ...]) -> list[dict]:
    """Fetch one metric across its covered assets, following pagination."""

    url = (
        f"{API_ROOT}?assets={','.join(assets)}&metrics={metric}"
        f"&frequency=1d&start_time={START}&end_time={END}&page_size={PAGE_SIZE}"
    )
    collected: list[dict] = []
    while url:
        payload = _get_json(url)
        collected.extend(payload.get("data", []))
        url = payload.get("next_page_url", "")
    return collected


def _get_json(url: str) -> dict:
    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=_TIMEOUT_S) as response:
                return json.load(response)
        except urllib.error.HTTPError:
            raise  # 4xx/5xx are real; do not silently swallow (ALT-007 lesson)
        except (urllib.error.URLError, TimeoutError) as err:
            last_err = err
            time.sleep(2**attempt)  # transient network: backoff and retry
    raise RuntimeError(f"failed to fetch after {_MAX_RETRIES} retries: {last_err}")


def tidy_rows(rows: list[dict], metric: str) -> pd.DataFrame:
    """Coin Metrics data rows -> tidy [asset, day, <metric>] frame (pure)."""

    if not rows:
        return pd.DataFrame(columns=["asset", "day", metric])
    frame = pd.DataFrame(rows)
    frame = frame[frame[metric].notna()].copy()
    frame["day"] = pd.to_datetime(frame["time"], utc=True).dt.floor("D")
    frame[metric] = pd.to_numeric(frame[metric], errors="coerce")
    frame = frame.dropna(subset=[metric])
    return frame[["asset", "day", metric]].reset_index(drop=True)


def build_panel(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Outer-merge per-metric tidy frames on (asset, day); sort deterministically."""

    non_empty = [f for f in frames if not f.empty]
    if not non_empty:
        return pd.DataFrame(columns=["asset", "day"])
    merged = reduce(
        lambda left, right: left.merge(right, on=["asset", "day"], how="outer"),
        non_empty,
    )
    return merged.sort_values(["asset", "day"], kind="mergesort").reset_index(drop=True)


if __name__ == "__main__":
    raise SystemExit(main())
