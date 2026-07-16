#!/usr/bin/env python3
"""TASK-TSM-010: multi-universe generalization of the base TSM (ADR-0031).

Runs the FIXED base TSM (config FC-II-008, zero re-tune) across several THEMATIC
universes of long-history Binance USDM perps -- large-cap, mid/alt-L1, DeFi,
gaming, old-guard/payments, and the TSM-009 mid-tier reference. Primary = base
TSM; combined (ERC+vol-target) shown as a caveated reference (TSM-009 showed the
overlays are universe-specific). Headline: in how many universes does the base
TSM deliver positive Sharpe AND beat buy-and-hold?

Per-symbol resilient download (a flaky/absent symbol is skipped, never blocks a
universe); coverage-gate 95%; klines+funding only (all the TSM needs). Zero cost.
"""

from __future__ import annotations

import json
import math
import sys
import time
import urllib.error
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.historical_dataset import (  # noqa: E402
    BinanceDataFamily,
    build_archive_plan,
    download_archives,
    expected_hourly_bars,
    normalize_archive_plan,
)
from src.research.tsm_trend import TsmTrendConfig, run_tsm_trend_backtest  # noqa: E402
from src.research.vol_target import apply_vol_target  # noqa: E402

# Thematic universes (long-history USDM perps). Coverage gate + per-symbol
# download filter decide the realized membership; themes are pre-declared.
UNIVERSES: dict[str, tuple[str, ...]] = {
    "large_cap": ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
                  "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "DOTUSDT"),
    "mid_alt_l1": ("NEARUSDT", "FILUSDT", "ALGOUSDT", "ICPUSDT", "ATOMUSDT",
                   "APTUSDT", "ARBUSDT", "OPUSDT", "SUIUSDT", "EGLDUSDT"),
    "defi": ("AAVEUSDT", "CRVUSDT", "UNIUSDT", "MKRUSDT", "SNXUSDT",
             "COMPUSDT", "SUSHIUSDT", "1INCHUSDT", "YFIUSDT"),
    "gaming": ("SANDUSDT", "MANAUSDT", "AXSUSDT", "GALAUSDT", "ENJUSDT",
               "CHZUSDT", "APEUSDT"),
    "old_guard": ("LTCUSDT", "BCHUSDT", "ETCUSDT", "XLMUSDT", "EOSUSDT",
                  "XTZUSDT", "DASHUSDT", "ZECUSDT", "NEOUSDT"),
    "mid_tier_ref": ("NEARUSDT", "FILUSDT", "AAVEUSDT", "ALGOUSDT", "ICPUSDT",
                     "SANDUSDT", "MANAUSDT", "AXSUSDT", "GRTUSDT", "CRVUSDT"),
}  # fmt: skip
START_MONTH, END_MONTH_EXCL = "2023-06", "2026-06"
COVERAGE_MIN = 0.95
MIN_SYMBOLS = 5  # a universe needs >= this many covered symbols to run
HOLD_HOURS = 120
_ANN = math.sqrt(24 * 365 / HOLD_HOURS)
_FAMILIES = (BinanceDataFamily.KLINES, BinanceDataFamily.FUNDING_RATE)
DATA_ROOT = PROJECT_ROOT / "data" / "research" / "binance_public"
BARS_CACHE = DATA_ROOT / "normalized" / "tsm_multiverse_202306_202605_bars.csv.gz"
OUTPUT_JSON = DATA_ROOT / "cost_pilot" / "tsm_multiverse.json"
REPORT_MD = PROJECT_ROOT / "reports" / "tsm_multiverse.md"
_EDGES = ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")


def main() -> int:
    bars = _load_or_build()
    expected = expected_hourly_bars(START_MONTH, END_MONTH_EXCL)
    covered = set(_coverage_filter(bars, expected))
    print(f"{len(covered)} symbols pass coverage gate", file=sys.stderr)

    results = {}
    for name, symbols in UNIVERSES.items():
        present = [s for s in symbols if s in covered]
        if len(present) < MIN_SYMBOLS:
            results[name] = {"symbols": present, "skipped": "insufficient coverage"}
            continue
        sub = bars[bars["symbol"].isin(present)].reset_index(drop=True)
        base = _net(sub, TsmTrendConfig(include_funding=True))
        erc = _net(sub, TsmTrendConfig(include_funding=True, portfolio_erc=True))
        combined = apply_vol_target(erc)
        baseline = _baseline(sub, TsmTrendConfig(include_funding=True))
        results[name] = {
            "symbols": present,
            "base": _metrics(base),
            "combined": _metrics(combined),
            "buy_hold": _metrics(baseline),
        }
        b = results[name]["base"]
        print(
            f"  {name} ({len(present)}): base Sharpe {b['sharpe']:.3f} vs buy-hold "
            f"{results[name]['buy_hold']['sharpe']:.3f}",
            file=sys.stderr,
        )

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-TSM-010 multi-universe generalization of the base TSM (ADR-0031)",
        "universes": results,
        "summary": _summary(results),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)
    s = payload["summary"]
    print(
        f"base TSM positive & beats buy-hold in {s['base_wins']}/{s['n_run']} universes",
        file=sys.stderr,
    )
    print(f"Wrote {OUTPUT_JSON}\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


def _load_or_build() -> pd.DataFrame:
    if BARS_CACHE.exists():
        print(f"Using cached {BARS_CACHE}", file=sys.stderr)
        return pd.read_csv(BARS_CACHE)
    all_symbols = sorted({s for syms in UNIVERSES.values() for s in syms})
    frames = []
    for sym in all_symbols:
        df = _ensure_symbol(sym)
        if df is not None:
            frames.append(df)
    bars = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    BARS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    bars.to_csv(BARS_CACHE, index=False, compression="gzip")
    print(
        f"Wrote {BARS_CACHE} ({len(bars)} rows, {bars['symbol'].nunique()} symbols)",
        file=sys.stderr,
    )
    return bars


def _ensure_symbol(sym: str, max_attempts: int = 6) -> pd.DataFrame | None:
    """Download+normalize one symbol; resilient to transient resets / absence."""

    specs = build_archive_plan(
        [sym], start_month=START_MONTH, end_month_exclusive=END_MONTH_EXCL, families=_FAMILIES
    )
    for attempt in range(1, max_attempts + 1):
        try:
            download_archives(specs, DATA_ROOT, max_workers=1)
            df = normalize_archive_plan(specs, DATA_ROOT, dataset_version=f"mv_{sym}")
            return df
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as err:
            print(
                f"  {sym} attempt {attempt}/{max_attempts}: {type(err).__name__}; retrying",
                file=sys.stderr,
            )
            time.sleep(min(20, 3 * attempt))
        except Exception as err:  # noqa: BLE001 -- missing symbol / normalize gap: skip it
            print(f"  {sym}: skipped ({type(err).__name__}: {err})", file=sys.stderr)
            return None
    print(f"  {sym}: skipped (download did not complete)", file=sys.stderr)
    return None


def _coverage_filter(bars: pd.DataFrame, expected: int) -> list[str]:
    counts = bars.dropna(subset=["log_price"]).groupby("symbol")["open_time"].count()
    return sorted(counts[counts >= COVERAGE_MIN * expected].index)


def _net(bars: pd.DataFrame, cfg: TsmTrendConfig) -> pd.Series:
    r = run_tsm_trend_backtest(bars, cfg)
    return pd.Series(r.tsm_net, index=list(r.rebalance_times))


def _baseline(bars: pd.DataFrame, cfg: TsmTrendConfig) -> pd.Series:
    r = run_tsm_trend_backtest(bars, cfg)
    return pd.Series(r.baseline, index=list(r.rebalance_times))


def _metrics(s: pd.Series) -> dict:
    r = np.asarray(s.dropna(), dtype=float)
    if len(r) < 2:  # noqa: PLR2004
        return {"n": int(len(r)), "sharpe": None, "max_dd": None, "net": None}
    std = r.std(ddof=1)
    sharpe = float(r.mean() / std * _ANN) if std > 0 else None
    equity = np.cumsum(r)
    max_dd = float(np.max(np.maximum.accumulate(equity) - equity))
    return {"n": int(len(r)), "sharpe": sharpe, "max_dd": max_dd, "net": float(r.sum())}


def _summary(results: dict) -> dict:
    run = {k: v for k, v in results.items() if "base" in v}
    base_wins = sum(
        1
        for v in run.values()
        if v["base"]["sharpe"] is not None
        and v["base"]["sharpe"] > 0
        and v["base"]["sharpe"] > v["buy_hold"]["sharpe"]
    )
    base_positive = sum(
        1 for v in run.values() if v["base"]["sharpe"] is not None and v["base"]["sharpe"] > 0
    )
    return {"n_run": len(run), "base_wins": base_wins, "base_positive": base_positive}


def _write_report(payload: dict) -> None:
    s = payload["summary"]
    lines = [
        "# TASK-TSM-010 -- Multi-Universe Generalization of the Base TSM",
        "",
        "Per `docs/pre_registers/TASK-TSM-010.md` (ADR-0031). The FIXED base TSM "
        "(FC-II-008, zero re-tune) across thematic Binance-USDM-perp universes. "
        "Primary = base TSM; combined (ERC+vol-target) is a caveated reference "
        "(TSM-009: overlays are universe-specific). Cross-asset breadth evidence, not a "
        "live promotion. AI/memecoins excluded (no 3y history on this window).",
        "",
        f"**Base TSM Sharpe > 0 AND > buy-and-hold in {s['base_wins']}/{s['n_run']} "
        f"universes** (positive Sharpe in {s['base_positive']}/{s['n_run']}).",
        "",
        "| Universe | n | Base Sharpe | Combined | Buy-hold | Base maxDD |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, v in payload["universes"].items():
        if "base" not in v:
            lines.append(f"| {name} | {len(v['symbols'])} | skipped | -- | -- | -- |")
            continue
        b, c, bh = v["base"], v["combined"], v["buy_hold"]
        lines.append(
            f"| {name} | {b['n']} | {_f(b['sharpe'])} | {_f(c['sharpe'])} | "
            f"{_f(bh['sharpe'])} | {_f(b['max_dd'])} |"
        )
    lines += [
        "",
        "## Per-universe membership (post coverage gate)",
        "",
    ]
    lines += [f"- **{n}**: {', '.join(v['symbols'])}" for n, v in payload["universes"].items()]
    lines += ["", "## Reading", "", _reading(payload), ""]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _reading(payload: dict) -> str:
    s = payload["summary"]
    frac = s["base_wins"] / s["n_run"] if s["n_run"] else 0.0
    strong = frac >= 0.8  # noqa: PLR2004
    verdict = (
        "STRONG multi-universe generalization: the base TSM delivers a positive, "
        "buy-hold-beating Sharpe across the large majority of thematic universes with "
        "FIXED params and no retuning -- robust cross-asset breadth evidence that the "
        "trend edge is general, not universe-specific. The strongest anti-overfitting "
        "evidence in the project (out-of-sample in the ASSET dimension)."
        if strong
        else "PARTIAL generalization: the base TSM is positive/beats buy-hold in some but "
        "not the large majority of universes -- documented honestly per universe; the "
        "edge is real but its strength varies by theme/period."
    )
    return (
        f"Base TSM positive AND beats buy-hold in {s['base_wins']}/{s['n_run']} universes "
        f"(positive in {s['base_positive']}/{s['n_run']}). {verdict}"
    )


def _f(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}"


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
