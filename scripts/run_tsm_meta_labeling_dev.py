#!/usr/bin/env python3
"""TASK-TSM-004: meta-labeling filter dev run + robustness battery (ADR-0031, Line 4).

DEVELOPMENT ONLY -- promotion is OOS-gated (like ML-001). The TSM sets each leg's
direction; a frozen GradientBoosting secondary model (features/threshold/CV all
locked a priori) predicts P(leg profitable) and drops low-probability legs via
purged+embargoed walk-forward CV out-of-fold predictions. Compares base vs
filtered on the OUT-OF-FOLD window (fair: the train-only first block is excluded)
plus the per-fold table (the ML-001 mirage guard) and the robustness battery.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.tsm_meta_labeling import build_leg_panel, run_meta_labeled_cv  # noqa: E402
from src.research.tsm_trend import (  # noqa: E402
    TsmTrendConfig,
    TsmTrendResult,
    run_tsm_trend_backtest,
    summarize_tsm_trend,
)

BARS = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/tsm_meta_labeling_dev.json"
REPORT_MD = PROJECT_ROOT / "reports/tsm_meta_labeling_dev.md"
N_SPLITS = 5
COST_GRID = (0.0, 6.0, 15.0, 30.0)
_PERIOD_EDGES = ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
_PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
_BTC = "BTCUSDT"
_LOOKBACK_H = 672


def main() -> int:
    bars = pd.read_csv(
        BARS,
        usecols=["symbol", "open_time", "log_price", "funding_rate_asof", "funding_interval_hours"],
    )
    cfg = TsmTrendConfig(include_funding=True)
    panel = build_leg_panel(bars, cfg)
    cv = run_meta_labeled_cv(panel, cfg, n_splits=N_SPLITS)
    mask = cv.keep_mask
    oof0 = cv.oof_start_time_ms

    base = run_tsm_trend_backtest(bars, cfg)
    filt = run_tsm_trend_backtest(bars, cfg, keep_mask=mask)

    edges = _edges_ms()
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-TSM-004 meta-labeling filter dev run (ADR-0031) -- DEVELOPMENT, no verdict",
        "n_splits": N_SPLITS,
        "n_legs": int(len(panel)),
        "label_mean": float(panel["label"].mean()),
        "oof_start_time_ms": oof0,
        "fold_metrics": [asdict(f) for f in cv.fold_metrics],
        "headline_oof": {
            "base": _metrics(_slice(base, _ge(base, oof0)), cfg),
            "filtered": _metrics(_slice(filt, _ge(filt, oof0)), cfg),
        },
        "sub_periods": _cmp(base, filt, cfg, _sub_masks(base, edges, oof0)),
        "btc_regime": _cmp(base, filt, cfg, _btc_masks(bars, base, oof0)),
        "cost_sensitivity": _cost_table(bars, mask, oof0),
        "funding_sensitivity": _funding_table(bars, mask, oof0),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)
    h = payload["headline_oof"]
    print(
        f"OOF base Sharpe {h['base']['sharpe']:.3f} maxDD {h['base']['max_dd']:.3f} | "
        f"filtered Sharpe {h['filtered']['sharpe']:.3f} maxDD {h['filtered']['max_dd']:.3f}",
        file=sys.stderr,
    )
    print(f"Wrote {OUTPUT_JSON}\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


def _edges_ms() -> tuple[int, ...]:
    return tuple(int(pd.Timestamp(d, tz="UTC").timestamp() * 1000) for d in _PERIOD_EDGES)


def _ge(r: TsmTrendResult, t0: int) -> list[bool]:
    return [t >= t0 for t in r.rebalance_times]


def _slice(result: TsmTrendResult, keep: list[bool]) -> TsmTrendResult:
    idx = [i for i, k in enumerate(keep) if k]

    def take(seq: tuple) -> tuple:
        return tuple(seq[i] for i in idx)

    return TsmTrendResult(
        rebalance_times=take(result.rebalance_times),
        tsm_net=take(result.tsm_net),
        tsm_long_only_net=take(result.tsm_long_only_net),
        baseline=take(result.baseline),
        tsm_turnover=take(result.tsm_turnover),
        tsm_long_sleeve=take(result.tsm_long_sleeve),
        tsm_short_sleeve=take(result.tsm_short_sleeve),
    )


def _metrics(result: TsmTrendResult, cfg: TsmTrendConfig) -> dict:
    if len(result.rebalance_times) < 2:  # noqa: PLR2004
        return {"n": len(result.rebalance_times), "sharpe": None, "max_dd": None, "net": None}
    s = summarize_tsm_trend(result, cfg)
    return {
        "n": s.n_rebalances,
        "sharpe": s.tsm_sharpe,
        "max_dd": s.tsm_max_drawdown,
        "net": s.tsm_net_pnl,
    }


def _sub_masks(base, edges, oof0) -> list[tuple[str, list[bool]]]:
    out = []
    for i, label in enumerate(_PERIOD_LABELS):
        lo, hi = max(edges[i], oof0), edges[i + 1]
        out.append((label, [lo <= t < hi for t in base.rebalance_times]))
    return out


def _btc_masks(bars, base, oof0) -> list[tuple[str, list[bool]]]:
    price = bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    if _BTC not in price.columns:
        return []
    trailing = (price[_BTC] - price[_BTC].shift(_LOOKBACK_H)).reindex(base.rebalance_times)
    vals = trailing.to_numpy()
    up = [bool(v > 0 and t >= oof0) for v, t in zip(vals, base.rebalance_times, strict=True)]
    down = [bool(v <= 0 and t >= oof0) for v, t in zip(vals, base.rebalance_times, strict=True)]
    return [("BTC_up", up), ("BTC_down", down)]


def _cmp(base, filt, cfg, masks) -> list[dict]:
    return [
        {
            "label": label,
            "base": _metrics(_slice(base, m), cfg),
            "filtered": _metrics(_slice(filt, m), cfg),
        }
        for label, m in masks
    ]


def _cost_table(bars, mask, oof0) -> list[dict]:
    out = []
    for c in COST_GRID:
        cfg = TsmTrendConfig(include_funding=True, cost_bps_per_leg=c)
        b = run_tsm_trend_backtest(bars, cfg)
        f = run_tsm_trend_backtest(bars, cfg, keep_mask=mask)
        out.append(
            {
                "cost_bps_per_leg": c,
                "base": _metrics(_slice(b, _ge(b, oof0)), cfg),
                "filtered": _metrics(_slice(f, _ge(f, oof0)), cfg),
            }
        )
    return out


def _funding_table(bars, mask, oof0) -> list[dict]:
    out = []
    for fund in (False, True):
        cfg = TsmTrendConfig(include_funding=fund)
        b = run_tsm_trend_backtest(bars, cfg)
        f = run_tsm_trend_backtest(bars, cfg, keep_mask=mask)
        out.append(
            {
                "include_funding": fund,
                "base": _metrics(_slice(b, _ge(b, oof0)), cfg),
                "filtered": _metrics(_slice(f, _ge(f, oof0)), cfg),
            }
        )
    return out


def _write_report(payload: dict) -> None:
    h = payload["headline_oof"]
    b, f = h["base"], h["filtered"]
    lines = [
        "# TASK-TSM-004 -- Meta-Labeling Filter Dev Run (DEVELOPMENT, no verdict)",
        "",
        "Per `docs/pre_registers/TASK-TSM-004.md` (ADR-0031, Line 4). TSM = primary "
        "(direction); a frozen GradientBoosting secondary model (6 causal features, "
        "threshold 0.5, purged+embargoed walk-forward CV) predicts P(leg profitable) "
        "and drops low-probability legs. **Development-window, out-of-fold result -- "
        "NOT a promotion (OOS-gated, like ML-001).** The per-fold table is the "
        "mirage guard: a gain from 1-2 folds is treated as a false positive.",
        "",
        f"Legs: {payload['n_legs']}; base label rate (leg profitable): "
        f"{payload['label_mean']:.3f} (a razor-thin leg-level edge).",
        "",
        "## Per-fold (purged walk-forward CV) -- mirage guard",
        "",
        "| Fold | n | kept | base leg-PnL | filtered leg-PnL | base prec | filt prec |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for fm in payload["fold_metrics"]:
        lines.append(
            f"| {fm['fold_index']} | {fm['n_test']} | {fm['kept_fraction']:.2f} | "
            f"{fm['base_mean_leg_pnl']:+.5f} | {fm['filtered_mean_leg_pnl']:+.5f} | "
            f"{fm['base_precision']:.3f} | {fm['filtered_precision']:.3f} |"
        )
    lines += [
        "",
        "## Headline (OUT-OF-FOLD window)",
        "",
        "| Metric | Base | Filtered |",
        "|---|---:|---:|",
        f"| Sharpe | {b['sharpe']:.3f} | {f['sharpe']:.3f} |",
        f"| Max drawdown | {b['max_dd']:.4f} | {f['max_dd']:.4f} |",
        f"| Net PnL | {b['net']:.4f} | {f['net']:.4f} |",
        f"| Rebalances | {b['n']} | {f['n']} |",
        "",
        "## Sub-period (OOF) Sharpe",
        "",
        "| Period | Base | Filtered |",
        "|---|---:|---:|",
    ]
    lines += [_row(r) for r in payload["sub_periods"]]
    lines += [
        "",
        "## BTC regime (OOF) Sharpe",
        "",
        "| Regime | Base | Filtered |",
        "|---|---:|---:|",
    ]
    lines += [_row(r) for r in payload["btc_regime"]]
    lines += [
        "",
        "## Cost sensitivity (OOF) Sharpe",
        "",
        "| Cost bps/leg | Base | Filtered |",
        "|---|---:|---:|",
    ]
    for r in payload["cost_sensitivity"]:
        lines.append(_row({"label": f"{r['cost_bps_per_leg']:.0f}", **r}))
    lines += [
        "",
        "## Funding sensitivity (OOF) Sharpe",
        "",
        "| include_funding | Base | Filtered |",
        "|---|---:|---:|",
    ]
    for r in payload["funding_sensitivity"]:
        lines.append(_row({"label": str(r["include_funding"]), **r}))
    lines += ["", "## Reading", "", _reading(payload), ""]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _row(r: dict) -> str:
    def fmt(d: dict) -> str:
        return "n/a" if d.get("sharpe") is None else f"{d['sharpe']:.3f}"

    return f"| {r['label']} | {fmt(r['base'])} | {fmt(r['filtered'])} |"


def _reading(payload: dict) -> str:
    b, f = payload["headline_oof"]["base"], payload["headline_oof"]["filtered"]
    if b["sharpe"] is None or f["sharpe"] is None:
        return "Insufficient out-of-fold rebalances to summarize."
    d_sharpe = f["sharpe"] - b["sharpe"]
    d_dd = f["max_dd"] - b["max_dd"]
    folds = payload["fold_metrics"]
    helped = sum(
        1
        for fm in folds
        if not math.isnan(fm["filtered_mean_leg_pnl"])
        and fm["filtered_mean_leg_pnl"] > fm["base_mean_leg_pnl"]
    )
    verdict = (
        "CANDIDATE for OOS."
        if (d_sharpe > 0 and d_dd <= 0 and helped >= math.ceil(len(folds) / 2) + 1)
        else "REJECTED / CAUTIONARY: the meta-labeling filter does not deliver a "
        "consistent out-of-fold improvement. Consistent with the ML-001 lesson -- on a "
        "razor-thin leg-level edge (base precision ~0.50) ML manufactures fold-specific "
        "gains that do not survive purged out-of-fold evaluation. Hypothesis closed; "
        "proceed to Line 5 (ensemble). Gate BLOCKED until OOS regardless."
    )
    return (
        f"OOF base -> filtered: Sharpe {b['sharpe']:.3f} -> {f['sharpe']:.3f} "
        f"(delta {d_sharpe:+.3f}); maxDD {b['max_dd']:.4f} -> {f['max_dd']:.4f} "
        f"(delta {d_dd:+.4f}). Filter beat base leg-PnL in {helped}/{len(folds)} folds. "
        f"{verdict}"
    )


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
