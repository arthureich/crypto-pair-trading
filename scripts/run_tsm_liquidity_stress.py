#!/usr/bin/env python3
"""TASK-TSM-015: liquidity-stress test of the base TSM (ADR-0031).

Does the base-TSM edge survive at the LOWER-liquidity end of the instruments that
have 3y history, at REALISTIC cost? Segments the union of already-cached symbols
into liquidity TERCILES (by median daily dollar-volume), runs the FIXED base TSM
(FC-II-008, include_funding, zero re-tune) per tier under a cost sweep
(6/12/20/30 bps), and compares to buy-hold. Windows/tiers/costs declared a priori
in docs/pre_registers/TASK-TSM-015.md.

HONEST caveat (survivorship): truly illiquid/microcap perps lack 3y history and
are absent -- this covers only the lower-liquidity END of survivors, an optimistic
lower bound on the liquidity question. Offline (cached bars only, no download);
causal signals; descriptive validation, no live promotion.
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

# Reuse the multiverse coverage gate + expected-bars helper as single source.
_MV_SPEC = importlib.util.spec_from_file_location(
    "run_tsm_multiverse", PROJECT_ROOT / "scripts" / "run_tsm_multiverse.py"
)
mv = importlib.util.module_from_spec(_MV_SPEC)
_MV_SPEC.loader.exec_module(mv)

DATA_ROOT = PROJECT_ROOT / "data" / "research" / "binance_public"
MV_BARS = DATA_ROOT / "normalized" / "tsm_multiverse_202306_202605_bars.csv.gz"
ORIG20_BARS = DATA_ROOT / "normalized" / "sprint7_binance_usdm_202306_202605_bars.csv.gz"
OUTPUT_JSON = DATA_ROOT / "cost_pilot" / "tsm_liquidity_stress.json"
REPORT_MD = PROJECT_ROOT / "reports" / "tsm_liquidity_stress.md"

_ANN = mv._ANN  # sqrt(24*365/120), same as the project
COSTS_BPS = (6.0, 12.0, 20.0, 30.0)  # LOCKED a priori (low-liq deserves higher cost)
REALISTIC_LOWLIQ_BPS = 20.0  # LOCKED: bar at which the LOW tier must still work
TIER_NAMES = ("HIGH", "MID", "LOW")


def daily_dollar_volume_median(df_symbol: pd.DataFrame) -> float:
    """Median of daily summed quote_volume (dollar volume) for one symbol."""
    q = df_symbol.dropna(subset=["quote_volume"]).copy()
    if q.empty:
        return 0.0
    day = (q["open_time"].astype("int64") // 86_400_000).to_numpy()
    daily = pd.Series(q["quote_volume"].to_numpy(), index=day).groupby(level=0).sum()
    return float(daily.median())


def tercile_split(ranked_symbols: list[str]) -> dict[str, list[str]]:
    """Split symbols (ascending by liquidity) into HIGH/MID/LOW terciles."""
    parts = np.array_split(np.asarray(ranked_symbols, dtype=object), 3)
    low, mid, high = (list(p) for p in parts)  # ascending -> first third = LOW
    return {"HIGH": high, "MID": mid, "LOW": low}


def _metrics(net: np.ndarray, turnover: np.ndarray | None = None) -> dict:
    r = np.asarray(net, dtype=float)
    r = r[~np.isnan(r)]
    if r.size < 2:  # noqa: PLR2004
        return {"n": int(r.size), "sharpe": None, "max_dd": None, "net": None}
    std = r.std(ddof=1)
    sharpe = float(r.mean() / std * _ANN) if std > 1e-12 else None  # noqa: PLR2004
    equity = np.cumsum(r)
    max_dd = float(np.max(np.maximum.accumulate(equity) - equity))
    out = {"n": int(r.size), "sharpe": sharpe, "max_dd": max_dd, "net": float(r.sum())}
    if turnover is not None:
        t = np.asarray(turnover, dtype=float)
        out["mean_turnover"] = float(np.nanmean(t)) if t.size else None
    return out


def _load_union() -> pd.DataFrame:
    frames = [pd.read_csv(MV_BARS, low_memory=False), pd.read_csv(ORIG20_BARS, low_memory=False)]
    bars = pd.concat(frames, ignore_index=True)
    bars = bars.drop_duplicates(subset=["symbol", "open_time"]).reset_index(drop=True)
    return bars


def _tier_run(bars: pd.DataFrame, symbols: list[str]) -> dict:
    sub = bars[bars["symbol"].isin(symbols)].reset_index(drop=True)
    per_cost = {}
    baseline = None
    for cost in COSTS_BPS:
        r = run_tsm_trend_backtest(sub, TsmTrendConfig(include_funding=True, cost_bps_per_leg=cost))
        per_cost[str(int(cost))] = _metrics(np.asarray(r.tsm_net), np.asarray(r.tsm_turnover))
        if baseline is None:
            baseline = _metrics(np.asarray(r.baseline))
    return {
        "n_symbols": len(symbols),
        "symbols": symbols,
        "by_cost": per_cost,
        "buy_hold": baseline,
    }


def characterize() -> dict:
    bars = _load_union()
    expected = mv.expected_hourly_bars(mv.START_MONTH, mv.END_MONTH_EXCL)
    covered = set(mv._coverage_filter(bars, expected))
    proxy = {s: daily_dollar_volume_median(bars[bars["symbol"] == s]) for s in sorted(covered)}
    ranked = sorted(covered, key=lambda s: proxy[s])  # ascending liquidity
    tiers = tercile_split(ranked)

    results = {}
    for tier in TIER_NAMES:
        syms = tiers[tier]
        run = _tier_run(bars, syms)
        run["median_dollar_vol"] = float(np.median([proxy[s] for s in syms]))
        results[tier] = run
    return {
        "n_covered": len(covered),
        "liquidity_proxy_median_daily_quote_volume": {s: proxy[s] for s in ranked},
        "tiers": results,
    }


def _verdict(r: dict) -> dict:
    low = r["tiers"]["LOW"]
    high = r["tiers"]["HIGH"]
    key = str(int(REALISTIC_LOWLIQ_BPS))
    low_real = low["by_cost"][key]
    low_bh = low["buy_hold"]["sharpe"]
    low_survives = (
        low_real["sharpe"] is not None
        and low_real["sharpe"] > 0
        and low_bh is not None
        and low_real["sharpe"] > low_bh
    )
    high6 = high["by_cost"]["6"]["sharpe"]
    low6 = low["by_cost"]["6"]["sharpe"]
    drop = (high6 - low6) if (high6 is not None and low6 is not None) else None
    return {
        "low_tier_survives_realistic_cost": bool(low_survives),
        "realistic_cost_bps": REALISTIC_LOWLIQ_BPS,
        "low_sharpe_at_realistic_cost": low_real["sharpe"],
        "low_buy_hold_sharpe": low_bh,
        "sharpe_drop_high_minus_low_at_6bps": drop,
    }


def _reading(r: dict, v: dict) -> str:
    t = r["tiers"]
    key = str(int(REALISTIC_LOWLIQ_BPS))

    def sh(tier: str, cost: str) -> str:
        x = t[tier]["by_cost"][cost]["sharpe"]
        return "n/a" if x is None else f"{x:.3f}"

    head = (
        "LIQUIDITY-ROBUST (within survivors): the base TSM edge survives at the "
        "lower-liquidity end at realistic cost."
        if v["low_tier_survives_realistic_cost"]
        else "LIQUIDITY LIMIT FOUND (in-domain): at realistic cost the base TSM does "
        "NOT clear buy-hold in the lower-liquidity tier -- an honest applicability "
        "condition (the edge needs liquidity), not a bug to 'fix'."
    )
    drop = v["sharpe_drop_high_minus_low_at_6bps"]
    drop_s = "n/a" if drop is None else f"{drop:.3f}"
    low_bh_s = _f(v["low_buy_hold_sharpe"])
    low_real_s = _f(v["low_sharpe_at_realistic_cost"])
    return (
        f"{head}\n\n"
        f"By tier @6bps: HIGH {sh('HIGH', '6')}, MID {sh('MID', '6')}, "
        f"LOW {sh('LOW', '6')} (HIGH-LOW gap {drop_s}). "
        f"LOW tier across cost: 6bps {sh('LOW', '6')}, 12bps {sh('LOW', '12')}, "
        f"20bps {sh('LOW', '20')}, 30bps {sh('LOW', '30')}; LOW buy-hold {low_bh_s}. "
        f"Decision bar: LOW must beat buy-hold at >= {int(REALISTIC_LOWLIQ_BPS)}bps -> "
        f"LOW@{key}bps {low_real_s}.\n\n"
        f"SURVIVORSHIP CAVEAT (central): truly illiquid/microcap perps lack 3y "
        f"history and are ABSENT -- this covers only the lower-liquidity END of "
        f"{r['n_covered']} survivors, an OPTIMISTIC lower bound on the liquidity "
        f"question, not the real microcap tail. quote_volume is a coarse proxy "
        f"(no spread/book depth). Fixed params, a-priori tiers/costs; offline; "
        f"descriptive, no live promotion."
    )


def _f(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def write_report(r: dict, v: dict) -> None:
    lines = [
        "# TASK-TSM-015 -- Liquidity-stress test of the base TSM",
        "",
        "Per `docs/pre_registers/TASK-TSM-015.md` (ADR-0031). Union of cached "
        "survivors segmented into liquidity terciles (median daily dollar-volume); "
        "FIXED base TSM (FC-II-008, include_funding, zero re-tune) per tier under a "
        "cost sweep. Offline; causal; descriptive. See the survivorship caveat.",
        "",
        f"Covered symbols (coverage gate 0.95): {r['n_covered']}. Cost bars: "
        f"{', '.join(str(int(c)) for c in COSTS_BPS)} bps/leg.",
        "",
        "## Sharpe by tier x cost",
        "",
        "| Tier | n | median $vol/day | "
        + " | ".join(f"{int(c)}bps" for c in COSTS_BPS)
        + " | buy-hold |",
        "|---|---:|---:|" + "---:|" * (len(COSTS_BPS) + 1),
    ]
    for tier in TIER_NAMES:
        tt = r["tiers"][tier]
        cells = " | ".join(_f(tt["by_cost"][str(int(c))]["sharpe"]) for c in COSTS_BPS)
        lines.append(
            f"| {tier} | {tt['n_symbols']} | {tt['median_dollar_vol']:.3e} | "
            f"{cells} | {_f(tt['buy_hold']['sharpe'])} |"
        )
    lines += [
        "",
        "## maxDD / turnover by tier (at 6bps and 20bps)",
        "",
        "| Tier | maxDD@6 | turn@6 | maxDD@20 | turn@20 |",
        "|---|---:|---:|---:|---:|",
    ]
    for tier in TIER_NAMES:
        c6 = r["tiers"][tier]["by_cost"]["6"]
        c20 = r["tiers"][tier]["by_cost"]["20"]
        lines.append(
            f"| {tier} | {_f(c6['max_dd'])} | {_f(c6.get('mean_turnover'))} | "
            f"{_f(c20['max_dd'])} | {_f(c20.get('mean_turnover'))} |"
        )
    lines += ["", "## Tier membership (ascending liquidity within tier)", ""]
    for tier in TIER_NAMES:
        lines.append(f"- **{tier}**: {', '.join(r['tiers'][tier]['symbols'])}")
    lines += ["", "## Reading", "", _reading(r, v), ""]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    r = characterize()
    v = _verdict(r)
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-TSM-015 liquidity-stress test of the base TSM (ADR-0031)",
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
