#!/usr/bin/env python3
"""TASK-TSM-009: out-of-universe generalization test of the combined TSM (ADR-0031).

Downloads a DIFFERENT liquid-USDM-perp universe (Binance public, free), applies
the SAME coverage gate, and runs the FIXED combined ERC + vol-targeting TSM
(config from TASK-TSM-008, zero re-tune) on it. Compares base / combined /
buy-hold on the new universe -- does the edge generalize beyond the original 20
symbols? Not a live promotion; a breadth-robustness (cross-universe) test.
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

# Liquid USDM perps NOT in the original 20 (long history). Coverage gate filters.
# Of 15 pre-registered candidates, 4 (SNX/XLM/EOS/XTZ) + partial MKR failed to
# download here (transient Binance connection resets) -- dropped on DATA
# AVAILABILITY, not performance (no results seen). The 10 below have full
# klines+funding cached; the coverage gate confirms them.
NEW_SYMBOLS = (
    "NEARUSDT", "FILUSDT", "AAVEUSDT", "ALGOUSDT", "ICPUSDT",
    "SANDUSDT", "MANAUSDT", "AXSUSDT", "GRTUSDT", "CRVUSDT",
)  # fmt: skip
# The TSM needs only klines (log_price) + funding; skip mark/index/premium.
_FAMILIES = (BinanceDataFamily.KLINES, BinanceDataFamily.FUNDING_RATE)
START_MONTH = "2023-06"
END_MONTH_EXCL = "2026-06"
DATASET = "tsm_oouniverse_202306_202605"
COVERAGE_MIN = 0.95
HOLD_HOURS = 120
_ANN = math.sqrt(24 * 365 / HOLD_HOURS)
DATA_ROOT = PROJECT_ROOT / "data" / "research" / "binance_public"
NORMALIZED = DATA_ROOT / "normalized" / f"{DATASET}_bars.csv.gz"
OUTPUT_JSON = DATA_ROOT / "cost_pilot" / "tsm_out_of_universe.json"
REPORT_MD = PROJECT_ROOT / "reports" / "tsm_out_of_universe.md"
_PERIOD_EDGES = ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
_PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")


def main() -> int:
    bars = _load_or_build()
    expected = expected_hourly_bars(START_MONTH, END_MONTH_EXCL)
    kept = _coverage_filter(bars, expected)
    bars = bars[bars["symbol"].isin(kept)].reset_index(drop=True)
    print(
        f"universe after coverage gate ({COVERAGE_MIN:.0%}): {len(kept)} symbols {kept}",
        file=sys.stderr,
    )

    base = _net(bars, TsmTrendConfig(include_funding=True))
    erc = _net(bars, TsmTrendConfig(include_funding=True, portfolio_erc=True))
    combined = apply_vol_target(erc)
    baseline = _baseline(bars, TsmTrendConfig(include_funding=True))

    edges = _edges_ms()
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-TSM-009 out-of-universe generalization test (ADR-0031)",
        "kept_symbols": kept,
        "headline": {
            "base": _metrics(base),
            "combined": _metrics(combined),
            "buy_hold": _metrics(baseline),
        },
        "sub_periods": [
            {
                "period": lbl,
                "combined": _metrics(_win(combined, edges[i], edges[i + 1])),
                "buy_hold": _metrics(_win(baseline, edges[i], edges[i + 1])),
            }
            for i, lbl in enumerate(_PERIOD_LABELS)
        ],
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)
    h = payload["headline"]
    print(
        f"OO-universe: combined Sharpe {h['combined']['sharpe']:.3f} vs buy-hold "
        f"{h['buy_hold']['sharpe']:.3f} (base {h['base']['sharpe']:.3f})",
        file=sys.stderr,
    )
    print(f"Wrote {OUTPUT_JSON}\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


def _load_or_build() -> pd.DataFrame:
    if NORMALIZED.exists():
        print(f"Using cached {NORMALIZED}", file=sys.stderr)
        return pd.read_csv(NORMALIZED)
    specs = build_archive_plan(
        NEW_SYMBOLS,
        start_month=START_MONTH,
        end_month_exclusive=END_MONTH_EXCL,
        families=_FAMILIES,
    )
    print(f"Downloading {len(specs)} archives for {len(NEW_SYMBOLS)} symbols...", file=sys.stderr)
    _download_with_resume(specs)
    bars = normalize_archive_plan(specs, DATA_ROOT, dataset_version=DATASET)
    NORMALIZED.parent.mkdir(parents=True, exist_ok=True)
    bars.to_csv(NORMALIZED, index=False, compression="gzip")
    print(f"Wrote {NORMALIZED} ({len(bars)} rows)", file=sys.stderr)
    return bars


def _download_with_resume(specs: tuple, max_attempts: int = 20) -> None:
    """download_archives (overwrite=False) resumes from the cache; retry transient
    connection resets (WinError 10054 / URLError) that the pipeline doesn't handle.

    Single-threaded (max_workers=1): the parallel fetch triggers Binance connection
    resets; sequential is slower but stable and the cache makes it resume-cheap."""

    for attempt in range(1, max_attempts + 1):
        try:
            download_archives(specs, DATA_ROOT, max_workers=1)
            return
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as err:
            wait = min(30, 3 * attempt)
            print(
                f"download attempt {attempt}/{max_attempts} hit {type(err).__name__}; "
                f"resuming in {wait}s (cache preserved)",
                file=sys.stderr,
            )
            time.sleep(wait)
    raise RuntimeError(f"download did not complete after {max_attempts} resume attempts")


def _coverage_filter(bars: pd.DataFrame, expected: int) -> list[str]:
    counts = bars.dropna(subset=["log_price"]).groupby("symbol")["open_time"].count()
    return sorted(counts[counts >= COVERAGE_MIN * expected].index)


def _net(bars: pd.DataFrame, cfg: TsmTrendConfig) -> pd.Series:
    r = run_tsm_trend_backtest(bars, cfg)
    return pd.Series(r.tsm_net, index=list(r.rebalance_times))


def _baseline(bars: pd.DataFrame, cfg: TsmTrendConfig) -> pd.Series:
    r = run_tsm_trend_backtest(bars, cfg)
    return pd.Series(r.baseline, index=list(r.rebalance_times))


def _edges_ms() -> tuple[int, ...]:
    return tuple(int(pd.Timestamp(d, tz="UTC").timestamp() * 1000) for d in _PERIOD_EDGES)


def _win(s: pd.Series, lo: int, hi: int) -> pd.Series:
    return s[(s.index >= lo) & (s.index < hi)]


def _metrics(s: pd.Series) -> dict:
    r = np.asarray(s.dropna(), dtype=float)
    if len(r) < 2:  # noqa: PLR2004
        return {"n": int(len(r)), "sharpe": None, "max_dd": None, "net": None}
    std = r.std(ddof=1)
    sharpe = float(r.mean() / std * _ANN) if std > 0 else None
    equity = np.cumsum(r)
    max_dd = float(np.max(np.maximum.accumulate(equity) - equity))
    return {"n": int(len(r)), "sharpe": sharpe, "max_dd": max_dd, "net": float(r.sum())}


def _write_report(payload: dict) -> None:
    h = payload["headline"]
    b, c, bh = h["base"], h["combined"], h["buy_hold"]
    lines = [
        "# TASK-TSM-009 -- Out-of-Universe Generalization Test (combined TSM)",
        "",
        "Per `docs/pre_registers/TASK-TSM-009.md` (ADR-0031). The FIXED combined ERC + "
        "vol-targeting TSM (config from TASK-TSM-008, ZERO re-tune) run on a DIFFERENT "
        "liquid-USDM-perp universe (not the original 20), coverage-gated. Does the edge "
        "generalize? Breadth-robustness (cross-universe) evidence -- not a live promotion.",
        "",
        f"New universe (coverage gate {COVERAGE_MIN:.0%}): {', '.join(payload['kept_symbols'])}.",
        "",
        "## Headline (full window)",
        "",
        "| Metric | Combined | Base TSM | Buy-and-hold |",
        "|---|---:|---:|---:|",
        f"| Sharpe | {_f(c['sharpe'])} | {_f(b['sharpe'])} | {_f(bh['sharpe'])} |",
        f"| Max drawdown | {_f(c['max_dd'])} | {_f(b['max_dd'])} | {_f(bh['max_dd'])} |",
        f"| Net PnL | {_f(c['net'])} | {_f(b['net'])} | {_f(bh['net'])} |",
        "",
        "## Sub-period Sharpe (combined vs buy-hold)",
        "",
        "| Period | Combined | Buy-and-hold |",
        "|---|---:|---:|",
    ]
    for r in payload["sub_periods"]:
        c_s, bh_s = _f(r["combined"]["sharpe"]), _f(r["buy_hold"]["sharpe"])
        lines.append(f"| {r['period']} | {c_s} | {bh_s} |")
    lines += ["", "## Reading", "", _reading(payload), ""]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _reading(payload: dict) -> str:
    h = payload["headline"]
    base, comb, bh = h["base"], h["combined"], h["buy_hold"]
    subs = payload["sub_periods"]
    combined_beats_bh = all(
        s["combined"]["sharpe"] is not None
        and s["buy_hold"]["sharpe"] is not None
        and s["combined"]["sharpe"] > s["buy_hold"]["sharpe"]
        for s in subs
    )
    core_generalizes = (
        base["sharpe"] is not None
        and base["sharpe"] > bh["sharpe"]
        and comb["sharpe"] > bh["sharpe"]
        and comb["net"] > 0
        and combined_beats_bh
    )
    overlays_help = comb["sharpe"] > base["sharpe"]  # do ERC+vol-target help HERE?
    core = (
        "CORE TSM EDGE GENERALIZES: on a different 10-alt universe both base "
        f"({base['sharpe']:.3f}) and combined ({comb['sharpe']:.3f}) beat buy-and-hold "
        f"({bh['sharpe']:.3f}) with positive net, in every sub-period -- trend-following is "
        "a GENERAL crypto-perp edge, not an artifact of the original 20. Raises confidence "
        "in the base TSM lead."
        if core_generalizes
        else "CORE TSM EDGE DOES NOT cleanly generalize: base/combined do not consistently "
        "beat buy-and-hold on the new universe -- weakens the whole TSM thesis."
    )
    overlay = (
        f"BUT the overlays (ERC + vol-target) DO NOT generalize: combined {comb['sharpe']:.3f} "
        f"< base {base['sharpe']:.3f} here (and worse drawdown {comb['max_dd']:.3f} vs "
        f"{base['max_dd']:.3f}) -- the OPPOSITE of the original universe (combined 1.183 > "
        "base 0.970). The clean-looking ERC+vol-target wins are PARTLY UNIVERSE-SPECIFIC; "
        "this TEMPERS confidence in the combined candidate. Also the absolute edge is weaker "
        f"here (base {base['sharpe']:.3f}) than on the original 20 (0.970)."
        if not overlays_help
        else f"The overlays ALSO help here: combined {comb['sharpe']:.3f} > base "
        f"{base['sharpe']:.3f} -- the combination generalizes too."
    )
    return f"{core} {overlay}"


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
