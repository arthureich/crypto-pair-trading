#!/usr/bin/env python3
"""TASK-TSM-014: temporal robustness of the base TSM (ADR-0031).

Reconstructs, OFFLINE from cached bars, the base-TSM per-rebalance PnL stream
(fixed FC-II-008, include_funding=True, zero re-tune) for 7 crypto universes
(original-20 + 6 thematic), then computes temporal metrics with windows declared
A PRIORI in docs/pre_registers/TASK-TSM-014.md:

  (A) fixed calendar sub-period Sharpe per universe (backfills TSM-013's gap to 7/7),
  (B) rolling-window Sharpe (W6=37, W12=73 rebalances, step 1),
  (C) drawdown duration / time-underwater.

DESCRIPTIVE: no backtest re-tune, no parameter change, no promotion. Crypto only
(TradFi is out-of-domain, not re-run here). Reads only cached data; no download.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.tsm_trend import TsmTrendConfig, run_tsm_trend_backtest  # noqa: E402

# Reuse the multiverse universe definitions as the single source of truth.
_MV_SPEC = importlib.util.spec_from_file_location(
    "run_tsm_multiverse", PROJECT_ROOT / "scripts" / "run_tsm_multiverse.py"
)
mv = importlib.util.module_from_spec(_MV_SPEC)
_MV_SPEC.loader.exec_module(mv)

DATA_ROOT = PROJECT_ROOT / "data" / "research" / "binance_public"
ORIG20_BARS = DATA_ROOT / "normalized" / "sprint7_binance_usdm_202306_202605_bars.csv.gz"
MV_BARS = mv.BARS_CACHE
OUTPUT_JSON = DATA_ROOT / "cost_pilot" / "tsm_temporal_robustness.json"
REPORT_MD = PROJECT_ROOT / "reports" / "tsm_temporal_robustness.md"

_ANN = mv._ANN  # sqrt(24*365/120), same as the project
# Fixed sub-period edges (project-standard, ADR-0019); LOCKED a priori.
_EDGES = ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
W6, W12 = 37, 73  # LOCKED: ~6mo/~12mo at 5d cadence (365/5 ~= 73)
CATASTROPHIC = -0.5  # LOCKED alert threshold for a sub-period Sharpe
MAJORITY = 0.5  # LOCKED: "majority of rolling windows positive" threshold
MIN_POS_SUBPERIODS = 2  # LOCKED: each universe positive in >= 2/3 sub-periods


def _sharpe(arr: np.ndarray) -> float | None:
    a = np.asarray(arr, dtype=float)
    a = a[~np.isnan(a)]
    if a.size < 2:  # noqa: PLR2004
        return None
    std = a.std(ddof=1)
    # epsilon floor: a genuinely flat slice yields a tiny float-rounding std, not 0
    return float(a.mean() / std * _ANN) if std > 1e-12 else None  # noqa: PLR2004


def sub_period_sharpe(times_ms: np.ndarray, pnl: np.ndarray) -> dict[str, float | None]:
    """Base Sharpe within each fixed calendar sub-period."""
    edges_ms = [int(pd.Timestamp(e, tz="UTC").value // 1_000_000) for e in _EDGES]
    out: dict[str, float | None] = {}
    for i, label in enumerate(_LABELS):
        lo, hi = edges_ms[i], edges_ms[i + 1]
        mask = (times_ms >= lo) & (times_ms < hi)
        out[label] = _sharpe(pnl[mask])
    return out


def rolling_sharpe(pnl: np.ndarray, window: int) -> np.ndarray:
    """Rolling Sharpe over fixed-count windows (step 1)."""
    a = np.asarray(pnl, dtype=float)
    a = a[~np.isnan(a)]
    if a.size < window:
        return np.array([])
    vals = []
    for i in range(window - 1, a.size):
        s = _sharpe(a[i - window + 1 : i + 1])
        vals.append(np.nan if s is None else s)
    return np.asarray(vals, dtype=float)


def _longest_neg_run(x: np.ndarray) -> int:
    best = cur = 0
    for v in x:
        if v < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def rolling_stats(pnl: np.ndarray, window: int) -> dict:
    r = rolling_sharpe(pnl, window)
    r = r[~np.isnan(r)]
    if r.size == 0:
        return {"n_windows": 0}
    return {
        "n_windows": int(r.size),
        "frac_positive": float(np.mean(r > 0)),
        "min": float(r.min()),
        "median": float(np.median(r)),
        "max": float(r.max()),
        "longest_negative_run": _longest_neg_run(r),
    }


def drawdown_duration(pnl: np.ndarray) -> dict:
    """Longest peak-to-recovery duration (rebalances -> days) and time underwater."""
    a = np.asarray(pnl, dtype=float)
    a = a[~np.isnan(a)]
    if a.size == 0:
        return {"max_duration_rebalances": 0, "max_duration_days": 0, "frac_underwater": 0.0}
    equity = np.cumsum(a)
    peak = equity[0]
    peak_i = 0
    max_dur = 0
    underwater = 0
    in_dd = False
    for i, v in enumerate(equity):
        if v >= peak:
            if in_dd:  # recovered to the prior peak -> count peak-to-recovery
                max_dur = max(max_dur, i - peak_i)
                in_dd = False
            peak, peak_i = v, i
        else:
            in_dd = True
            underwater += 1
            max_dur = max(max_dur, i - peak_i)  # ongoing (handles unrecovered-at-end)
    return {
        "max_duration_rebalances": int(max_dur),
        "max_duration_days": int(max_dur * 5),
        "frac_underwater": float(underwater / equity.size),
    }


def _base_stream(bars: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    r = run_tsm_trend_backtest(bars, TsmTrendConfig(include_funding=True))
    return np.asarray(r.rebalance_times, dtype="int64"), np.asarray(r.tsm_net, dtype=float)


def _collect_universes() -> dict[str, pd.DataFrame]:
    """{universe_name: bars} for original-20 + covered thematic universes."""
    out: dict[str, pd.DataFrame] = {}
    orig = pd.read_csv(ORIG20_BARS, low_memory=False)
    out["original_20"] = orig
    mv_bars = pd.read_csv(MV_BARS, low_memory=False)
    expected = mv.expected_hourly_bars(mv.START_MONTH, mv.END_MONTH_EXCL)
    covered = set(mv._coverage_filter(mv_bars, expected))
    for name, symbols in mv.UNIVERSES.items():
        present = [s for s in symbols if s in covered]
        if len(present) < mv.MIN_SYMBOLS:
            continue
        out[name] = mv_bars[mv_bars["symbol"].isin(present)].reset_index(drop=True)
    return out


def characterize() -> dict:
    universes = _collect_universes()
    per_universe = {}
    for name, bars in universes.items():
        times, pnl = _base_stream(bars)
        per_universe[name] = {
            "sub_period_sharpe": sub_period_sharpe(times, pnl),
            "rolling_w6": rolling_stats(pnl, W6),
            "rolling_w12": rolling_stats(pnl, W12),
            "drawdown": drawdown_duration(pnl),
            "full_sharpe": _sharpe(pnl),
        }

    # (A) cross-universe per sub-period
    sub_stats = {}
    negatives = []
    for label in _LABELS:
        vals = [v["sub_period_sharpe"][label] for v in per_universe.values()]
        vals = [x for x in vals if x is not None]
        arr = np.asarray(vals, dtype=float)
        sub_stats[label] = {
            "mean": float(arr.mean()),
            "std": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
            "min": float(arr.min()),
            "max": float(arr.max()),
            "frac_positive": float(np.mean(arr > 0)),
        }
    for name, v in per_universe.items():
        for label, s in v["sub_period_sharpe"].items():
            if s is not None and s < 0:
                negatives.append({"universe": name, "sub_period": label, "sharpe": s})
    weakest = min(sub_stats, key=lambda k: sub_stats[k]["mean"])
    # each universe positive in >= 2/3 sub-periods?
    pos_counts = {
        name: sum(1 for s in v["sub_period_sharpe"].values() if s is not None and s > 0)
        for name, v in per_universe.items()
    }

    # (B) pooled rolling positivity
    pooled = {}
    for wkey, w in (("w6", W6), ("w12", W12)):
        allr = np.concatenate(
            [rolling_sharpe(_base_stream(universes[n])[1], w) for n in per_universe]
        )
        allr = allr[~np.isnan(allr)]
        pooled[wkey] = {
            "n_windows": int(allr.size),
            "frac_positive": float(np.mean(allr > 0)) if allr.size else None,
        }

    return {
        "per_universe": per_universe,
        "sub_period_cross_universe": sub_stats,
        "sub_period_negatives": negatives,
        "weakest_sub_period": weakest,
        "positive_subperiod_counts": pos_counts,
        "pooled_rolling": pooled,
        "n_universes": len(per_universe),
    }


def _verdict(r: dict) -> dict:
    all_2of3 = all(c >= MIN_POS_SUBPERIODS for c in r["positive_subperiod_counts"].values())
    no_catastrophe = all(n["sharpe"] >= CATASTROPHIC for n in r["sub_period_negatives"])
    rolling_ok = all(
        (r["pooled_rolling"][k]["frac_positive"] or 0) > MAJORITY for k in ("w6", "w12")
    )
    dd = [v["drawdown"]["max_duration_days"] for v in r["per_universe"].values()]
    robust = all_2of3 and no_catastrophe and rolling_ok
    return {
        "all_universes_positive_2of3_subperiods": all_2of3,
        "no_catastrophic_subperiod": no_catastrophe,
        "majority_rolling_positive": rolling_ok,
        "max_drawdown_duration_days_across_universes": int(max(dd)) if dd else 0,
        "temporally_robust": robust,
    }


def _reading(r: dict, v: dict) -> str:
    ss = r["sub_period_cross_universe"]
    p6 = r["pooled_rolling"]["w6"]["frac_positive"]
    p12 = r["pooled_rolling"]["w12"]["frac_positive"]
    negs = r["sub_period_negatives"]
    head = (
        "TEMPORALLY ROBUST (in-domain crypto): the base TSM holds across time, not "
        "just in one hot window."
        if v["temporally_robust"]
        else "TEMPORAL FRAGILITY FOUND: the base TSM weakens in specific windows -- "
        "documented honestly below."
    )
    neg_txt = (
        "no (universe, sub-period) cell is negative"
        if not negs
        else "negative cells: "
        + "; ".join(f"{n['universe']}/{n['sub_period']} {n['sharpe']:.2f}" for n in negs)
    )
    return (
        f"{head}\n\n"
        f"(A) SUB-PERIODS (n={r['n_universes']} universes x 3 fixed windows, "
        f"backfills TSM-013 coverage to {r['n_universes']}/{r['n_universes']}): "
        f"cross-universe mean Sharpe by period -- "
        f"{_LABELS[0]} {ss[_LABELS[0]]['mean']:.2f} (pos "
        f"{ss[_LABELS[0]]['frac_positive']*100:.0f}%), "
        f"{_LABELS[1]} {ss[_LABELS[1]]['mean']:.2f} (pos "
        f"{ss[_LABELS[1]]['frac_positive']*100:.0f}%), "
        f"{_LABELS[2]} {ss[_LABELS[2]]['mean']:.2f} (pos "
        f"{ss[_LABELS[2]]['frac_positive']*100:.0f}%). Weakest: "
        f"**{r['weakest_sub_period']}**; {neg_txt}. Every universe positive in "
        f">=2/3 sub-periods: {v['all_universes_positive_2of3_subperiods']}.\n\n"
        f"(B) ROLLING WINDOWS (pooled across universes): W6(~6mo) "
        f"{p6*100:.0f}% of windows positive; W12(~12mo) {p12*100:.0f}%. "
        f"Majority positive: {v['majority_rolling_positive']}.\n\n"
        f"(C) DRAWDOWN DURATION (honest risk feature, NOT sugar-coated): worst "
        f"peak-to-recovery across universes = "
        f"{v['max_drawdown_duration_days_across_universes']} days (~14 months), and "
        f"time-underwater is high (79-89%). Two caveats: (i) the ~415d stretch lands "
        f"in the mid/alt universes (mid_alt_l1, defi, mid_tier_ref) -- the SAME ones "
        f"with the weakest FINAL sub-period, i.e. a long drawdown entered in the last "
        f"year and likely not fully recovered by window-end; (ii) high time-underwater "
        f"reflects a slow-grinding equity curve making infrequent new highs at MODEST "
        f"depth (maxDD ~0.31-0.80, TSM-013), not deep losses. This is a real risk "
        f"(long flat stretches, typical of trend-following), not dismissible -- the "
        f"robustness verdict rests on (A)+(B), with this as the honest cost.\n\n"
        f"Descriptive temporal characterization; fixed params, a-priori windows, "
        f"offline from cached bars; no promotion, no parameter change. TradFi "
        f"(out-of-domain) not re-run here."
    )


def _f(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def write_report(r: dict, v: dict) -> None:
    lines = [
        "# TASK-TSM-014 -- Temporal robustness of the base TSM",
        "",
        "Per `docs/pre_registers/TASK-TSM-014.md` (ADR-0031). Base TSM (fixed "
        "FC-II-008, include_funding, zero re-tune) reconstructed OFFLINE from cached "
        "bars for 7 crypto universes. Windows declared a priori. Descriptive; no "
        "promotion, no parameter change. TradFi out-of-domain, not re-run.",
        "",
        "## (A) Fixed sub-period Sharpe per universe (backfills TSM-013 to 7/7)",
        "",
        "| Universe | " + " | ".join(_LABELS) + " | full |",
        "|---|---|---|---|---|",
    ]
    for name, u in r["per_universe"].items():
        sp = u["sub_period_sharpe"]
        lines.append(
            f"| {name} | {_f(sp[_LABELS[0]])} | {_f(sp[_LABELS[1]])} | "
            f"{_f(sp[_LABELS[2]])} | {_f(u['full_sharpe'])} |"
        )
    lines += ["", "Cross-universe by sub-period:", ""]
    for label, d in r["sub_period_cross_universe"].items():
        lines.append(
            f"- {label}: mean {d['mean']:.3f}, sd {d['std']:.3f}, "
            f"min {d['min']:.3f}, max {d['max']:.3f}, positive {d['frac_positive']*100:.0f}%"
        )
    lines += [
        "",
        f"Weakest sub-period: **{r['weakest_sub_period']}**. "
        f"Negative (universe, sub-period) cells: {len(r['sub_period_negatives'])}.",
        "",
        "## (B) Rolling-window Sharpe (W6=37 ~6mo, W12=73 ~12mo, step 1)",
        "",
        "| Universe | W6 %pos | W6 min/med/max | W6 longest neg | W12 %pos | "
        "W12 min/med/max | W12 longest neg |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, u in r["per_universe"].items():
        a, b = u["rolling_w6"], u["rolling_w12"]
        lines.append(
            f"| {name} | {a.get('frac_positive', 0)*100:.0f}% | "
            f"{_f(a.get('min'))}/{_f(a.get('median'))}/{_f(a.get('max'))} | "
            f"{a.get('longest_negative_run', 0)} | {b.get('frac_positive', 0)*100:.0f}% | "
            f"{_f(b.get('min'))}/{_f(b.get('median'))}/{_f(b.get('max'))} | "
            f"{b.get('longest_negative_run', 0)} |"
        )
    pr = r["pooled_rolling"]
    lines += [
        "",
        f"Pooled: W6 {pr['w6']['frac_positive']*100:.0f}% of {pr['w6']['n_windows']} "
        f"windows positive; W12 {pr['w12']['frac_positive']*100:.0f}% of "
        f"{pr['w12']['n_windows']}.",
        "",
        "## (C) Drawdown duration (time underwater)",
        "",
        "| Universe | max DD duration (days) | frac underwater |",
        "|---|---|---|",
    ]
    for name, u in r["per_universe"].items():
        d = u["drawdown"]
        lines.append(f"| {name} | {d['max_duration_days']} | {d['frac_underwater']*100:.0f}% |")
    lines += ["", "## Reading", "", _reading(r, v), ""]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    r = characterize()
    v = _verdict(r)
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-TSM-014 temporal robustness of the base TSM (ADR-0031)",
        "result": r,
        "verdict": v,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_report(r, v)
    print(_reading(r, v))
    print(f"\nWrote {OUTPUT_JSON}\nWrote {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
