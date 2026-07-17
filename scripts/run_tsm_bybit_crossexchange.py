#!/usr/bin/env python3
"""TASK-TSM-011: cross-exchange generalization of the base TSM on Bybit (ADR-0031).

Fetches Bybit v5 public hourly klines + funding history (keyless), normalizes to
the SAME schema the TSM consumes (log_price, funding_rate_asof,
funding_interval_hours), and runs the FIXED base TSM (FC-II-008, zero re-tune) on
the SAME 20 symbols as the Binance dev universe -- then compares Bybit vs Binance
side by side with the same code. Cross-venue robustness evidence, not a live
promotion. Zero cost.
"""

from __future__ import annotations

import json
import math
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.tsm_trend import (  # noqa: E402
    TsmTrendConfig,
    TsmTrendResult,
    run_tsm_trend_backtest,
    summarize_tsm_trend,
)

BYBIT = "https://api.bybit.com/v5/market"
SYMBOLS = (
    "ADAUSDT", "APTUSDT", "ARBUSDT", "ATOMUSDT", "AVAXUSDT", "BCHUSDT", "BNBUSDT",
    "BTCUSDT", "DOGEUSDT", "DOTUSDT", "ETCUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT",
    "OPUSDT", "SOLUSDT", "SUIUSDT", "TRXUSDT", "UNIUSDT", "XRPUSDT",
)  # fmt: skip
START = "2023-06-01"
END = "2026-06-01"
FUNDING_INTERVAL_HOURS = 8.0
COVERAGE_MIN = 0.95
_MS_HOUR = 3_600_000
_TIMEOUT = 20
_MAX_RETRIES = 6
BINANCE_BARS = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
BARS_CACHE = PROJECT_ROOT / "data/research/binance_public/normalized/bybit_tsm_202306_202605.csv.gz"
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/tsm_bybit_crossexchange.json"
REPORT_MD = PROJECT_ROOT / "reports/tsm_bybit_crossexchange.md"
_PERIOD_EDGES = ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
_PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")


def main() -> int:
    bybit = _load_or_build_bybit()
    expected = int((_ms(END) - _ms(START)) / _MS_HOUR)
    bybit = _coverage_filter(bybit, expected)
    kept = sorted(bybit["symbol"].unique())
    print(f"Bybit universe after coverage gate: {len(kept)} symbols", file=sys.stderr)

    # Same code on both venues; restrict Binance to the same kept symbols.
    binance = pd.read_csv(
        BINANCE_BARS,
        usecols=[
            "symbol",
            "base_asset",
            "open_time",
            "log_price",
            "funding_rate_asof",
            "funding_interval_hours",
        ],
    )
    binance = binance[binance["symbol"].isin(kept)].reset_index(drop=True)

    cfg = TsmTrendConfig(include_funding=True)
    edges = _edges_ms()
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-TSM-011 cross-exchange (Bybit) generalization of the base TSM",
        "kept_symbols": kept,
        "bybit": _venue_metrics(run_tsm_trend_backtest(bybit, cfg), cfg, edges),
        "binance": _venue_metrics(run_tsm_trend_backtest(binance, cfg), cfg, edges),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)
    by, bn = payload["bybit"]["headline"], payload["binance"]["headline"]
    print(
        f"Bybit base Sharpe {by['sharpe']:.3f} (maxDD {by['max_dd']:.3f}) vs "
        f"Binance {bn['sharpe']:.3f} (maxDD {bn['max_dd']:.3f})",
        file=sys.stderr,
    )
    print(f"Wrote {OUTPUT_JSON}\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


# --- Bybit client ---------------------------------------------------------------


def _load_or_build_bybit() -> pd.DataFrame:
    if BARS_CACHE.exists():
        print(f"Using cached {BARS_CACHE}", file=sys.stderr)
        return pd.read_csv(BARS_CACHE)
    frames = []
    for sym in SYMBOLS:
        df = _build_symbol(sym)
        if df is not None and not df.empty:
            frames.append(df)
            print(f"  {sym}: {len(df)} hourly bars", file=sys.stderr)
        else:
            print(f"  {sym}: skipped (no data)", file=sys.stderr)
    bars = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    BARS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    bars.to_csv(BARS_CACHE, index=False, compression="gzip")
    print(f"Wrote {BARS_CACHE} ({len(bars)} rows)", file=sys.stderr)
    return bars


def _build_symbol(sym: str) -> pd.DataFrame | None:
    try:
        klines = _paginate_klines(sym)
        funding = _paginate_funding(sym)
    except RuntimeError as err:
        print(f"  {sym}: download failed ({err})", file=sys.stderr)
        return None
    if not klines:
        return None
    kl = pd.DataFrame(klines, columns=["open_time", "close"]).drop_duplicates("open_time")
    kl = kl[(kl["open_time"] >= _ms(START)) & (kl["open_time"] < _ms(END))].sort_values("open_time")
    kl["log_price"] = np.log(kl["close"].astype(float))
    # backward as-of merge of funding onto hourly bars
    fund = pd.DataFrame(funding, columns=["funding_time", "funding_rate_asof"]).sort_values(
        "funding_time"
    )
    merged = pd.merge_asof(
        kl, fund, left_on="open_time", right_on="funding_time", direction="backward"
    )
    merged["symbol"] = sym
    merged["base_asset"] = sym[:-4].lower()
    merged["funding_interval_hours"] = FUNDING_INTERVAL_HOURS
    merged["funding_rate_asof"] = merged["funding_rate_asof"].astype(float).fillna(0.0)
    return merged[
        [
            "symbol",
            "base_asset",
            "open_time",
            "log_price",
            "funding_rate_asof",
            "funding_interval_hours",
        ]
    ]


def _paginate_klines(sym: str) -> list[list]:
    out: list[list] = []
    end = _ms(END)
    start = _ms(START)
    while end > start:
        url = f"{BYBIT}/kline?category=linear&symbol={sym}&interval=60" f"&end={end}&limit=1000"
        rows = _get(url)["result"]["list"]  # newest-first: [ts,o,h,l,c,vol,turnover]
        if not rows:
            break
        for r in rows:
            out.append([int(r[0]), float(r[4])])
        oldest = int(rows[-1][0])
        if oldest <= start:
            break
        end = oldest - 1
        time.sleep(0.15)
    return out


def _paginate_funding(sym: str) -> list[list]:
    out: list[list] = []
    end = _ms(END)
    start = _ms(START)
    while end > start:
        url = f"{BYBIT}/funding/history?category=linear&symbol={sym}" f"&endTime={end}&limit=200"
        rows = _get(url)["result"]["list"]  # newest-first
        if not rows:
            break
        for r in rows:
            out.append([int(r["fundingRateTimestamp"]), float(r["fundingRate"])])
        oldest = int(rows[-1]["fundingRateTimestamp"])
        if oldest <= start:
            break
        end = oldest - 1
        time.sleep(0.15)
    return out


def _get(url: str) -> dict:
    last: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research/1.0"})
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = json.load(resp)
            if data.get("retCode") not in (0, None):
                raise RuntimeError(f"bybit retCode {data.get('retCode')}: {data.get('retMsg')}")
            return data
        except (urllib.error.URLError, TimeoutError, OSError, ConnectionError) as err:
            last = err
            time.sleep(min(20, 2**attempt))
    raise RuntimeError(f"failed after {_MAX_RETRIES} retries: {last}")


# --- metrics / reporting --------------------------------------------------------


def _coverage_filter(bars: pd.DataFrame, expected: int) -> pd.DataFrame:
    counts = bars.dropna(subset=["log_price"]).groupby("symbol")["open_time"].count()
    keep = counts[counts >= COVERAGE_MIN * expected].index
    return bars[bars["symbol"].isin(keep)].reset_index(drop=True)


def _edges_ms() -> tuple[int, ...]:
    return tuple(_ms(d) for d in _PERIOD_EDGES)


def _ms(day: str) -> int:
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)


def _slice(result: TsmTrendResult, lo: int, hi: int) -> TsmTrendResult:
    idx = [i for i, t in enumerate(result.rebalance_times) if lo <= t < hi]

    def take(seq: tuple) -> tuple:
        return tuple(seq[i] for i in idx)

    return TsmTrendResult(
        take(result.rebalance_times),
        take(result.tsm_net),
        take(result.tsm_long_only_net),
        take(result.baseline),
        take(result.tsm_turnover),
        take(result.tsm_long_sleeve),
        take(result.tsm_short_sleeve),
    )


def _venue_metrics(result: TsmTrendResult, cfg: TsmTrendConfig, edges: tuple[int, ...]) -> dict:
    s = summarize_tsm_trend(result, cfg)
    subs = {}
    for i, lbl in enumerate(_PERIOD_LABELS):
        sub = _slice(result, edges[i], edges[i + 1])
        subs[lbl] = (
            summarize_tsm_trend(sub, cfg).tsm_sharpe if len(sub.rebalance_times) >= 2 else None  # noqa: PLR2004
        )
    return {
        "headline": {
            "sharpe": s.tsm_sharpe,
            "max_dd": s.tsm_max_drawdown,
            "net": s.tsm_net_pnl,
            "mean_turnover": s.mean_turnover,
            "baseline_sharpe": s.baseline_sharpe,
            "n_rebalances": s.n_rebalances,
        },
        "sub_period_sharpe": subs,
    }


def _write_report(payload: dict) -> None:
    by, bn = payload["bybit"], payload["binance"]
    bh, nh = by["headline"], bn["headline"]
    lines = [
        "# TASK-TSM-011 -- Cross-Exchange Generalization (Bybit vs Binance)",
        "",
        "Per `docs/pre_registers/TASK-TSM-011.md` (ADR-0031). The FIXED base TSM "
        "(FC-II-008, zero re-tune) run with the SAME code on Bybit and Binance, SAME "
        f"{len(payload['kept_symbols'])} symbols. Cross-venue robustness, not a live "
        "promotion. Bybit funding is 8h (same as Binance).",
        "",
        "## Headline (full window, same symbols both venues)",
        "",
        "| Metric | Bybit | Binance |",
        "|---|---:|---:|",
        f"| Base Sharpe | {_f(bh['sharpe'])} | {_f(nh['sharpe'])} |",
        f"| Max drawdown | {_f(bh['max_dd'])} | {_f(nh['max_dd'])} |",
        f"| Net PnL | {_f(bh['net'])} | {_f(nh['net'])} |",
        f"| Mean turnover | {_f(bh['mean_turnover'])} | {_f(nh['mean_turnover'])} |",
        f"| Buy-hold Sharpe | {_f(bh['baseline_sharpe'])} | {_f(nh['baseline_sharpe'])} |",
        f"| Rebalances | {bh['n_rebalances']} | {nh['n_rebalances']} |",
        "",
        "## Sub-period base Sharpe",
        "",
        "| Period | Bybit | Binance |",
        "|---|---:|---:|",
    ]
    for lbl in _PERIOD_LABELS:
        b_s, n_s = _f(by["sub_period_sharpe"][lbl]), _f(bn["sub_period_sharpe"][lbl])
        lines.append(f"| {lbl} | {b_s} | {n_s} |")
    lines += ["", "## Reading", "", _reading(payload), ""]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _reading(payload: dict) -> str:
    bh, nh = payload["bybit"]["headline"], payload["binance"]["headline"]
    subs = payload["bybit"]["sub_period_sharpe"]
    pos_all = all(v is not None and v > 0 for v in subs.values())
    generalizes = bh["sharpe"] > 0 and bh["sharpe"] > bh["baseline_sharpe"] and pos_all
    verdict = (
        f"GENERALIZES CROSS-EXCHANGE: on Bybit the base TSM Sharpe {bh['sharpe']:.3f} is "
        f"positive, beats buy-hold ({bh['baseline_sharpe']:.3f}), positive in every "
        f"sub-period, and comparable to Binance ({nh['sharpe']:.3f}). The edge is not an "
        "artifact of Binance microstructure -- it is a venue-independent trend property."
        if generalizes
        else f"DOES NOT cleanly generalize on Bybit: base Sharpe {bh['sharpe']:.3f} vs "
        f"Binance {nh['sharpe']:.3f}; positive every sub-period: {pos_all}. Documented "
        "honestly; characterize the structural difference (liquidity/funding/listing dates)."
    )
    caveat = (
        " CAVEAT on strength: same-symbol prices are tightly ARBITRAGED across venues, "
        "so near-identical results are EXPECTED -- this test mainly rules out "
        "Binance-specific data/microstructure artifacts; the cross-UNIVERSE tests "
        "(TSM-009/010, different assets) remain the stronger diversity evidence."
    )
    return (
        f"Bybit base Sharpe {bh['sharpe']:.3f} (buy-hold {bh['baseline_sharpe']:.3f}) vs "
        f"Binance {nh['sharpe']:.3f}. {verdict}{caveat}"
    )


def _f(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.4f}"


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, bool | str | int) or value is None:
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
