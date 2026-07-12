#!/usr/bin/env python3
"""TASK-TSM-003: ERC portfolio-construction dev run + robustness battery (ADR-0031).

DEVELOPMENT ONLY -- no promotion verdict (OOS-gated). Compares the base
vol-targeted TSM (FC-II-008, with funding; naive inverse-vol within each sleeve)
against ERC (equal risk contribution within each sleeve, correlation-aware,
preserving base direction and L/S gross) across the mandatory robustness
battery. The covariance window (90d) is fixed a priori; nothing tuned.
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
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/tsm_portfolio_erc_dev.json"
REPORT_MD = PROJECT_ROOT / "reports/tsm_portfolio_erc_dev.md"
COST_GRID = (0.0, 6.0, 15.0, 30.0, 60.0)
_PERIOD_EDGES = ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
_PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
_BTC = "BTCUSDT"
_LOOKBACK_H = 672


def _base(**kw) -> TsmTrendConfig:
    return TsmTrendConfig(include_funding=True, **kw)


def _erc(**kw) -> TsmTrendConfig:
    return TsmTrendConfig(include_funding=True, portfolio_erc=True, **kw)


def main() -> int:
    bars = pd.read_csv(
        BARS,
        usecols=["symbol", "open_time", "log_price", "funding_rate_asof", "funding_interval_hours"],
    )
    base_cfg, erc_cfg = _base(), _erc()
    base = run_tsm_trend_backtest(bars, base_cfg)
    erc = run_tsm_trend_backtest(bars, erc_cfg)

    edges = _edges_ms()
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-TSM-003 ERC portfolio construction dev run (ADR-0031) -- DEVELOPMENT",
        "headline": {
            "base": asdict(summarize_tsm_trend(base, base_cfg)),
            "erc": asdict(summarize_tsm_trend(erc, erc_cfg)),
        },
        "sub_periods": _cmp_table(base, erc, base_cfg, erc_cfg, _sub_masks(base, edges)),
        "btc_regime": _cmp_table(base, erc, base_cfg, erc_cfg, _btc_masks(bars, base)),
        "cost_sensitivity": [
            {
                "cost_bps_per_leg": c,
                "base": _metrics(run_tsm_trend_backtest(bars, _base(cost_bps_per_leg=c)), _base()),
                "erc": _metrics(run_tsm_trend_backtest(bars, _erc(cost_bps_per_leg=c)), _erc()),
            }
            for c in COST_GRID
        ],
        "funding_sensitivity": [_funding_row(bars, f) for f in (False, True)],
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)
    h = payload["headline"]
    print(
        f"base Sharpe {h['base']['tsm_sharpe']:.3f} maxDD {h['base']['tsm_max_drawdown']:.3f} | "
        f"erc Sharpe {h['erc']['tsm_sharpe']:.3f} maxDD {h['erc']['tsm_max_drawdown']:.3f}",
        file=sys.stderr,
    )
    print(f"Wrote {OUTPUT_JSON}\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


def _funding_row(bars: pd.DataFrame, funding: bool) -> dict:
    base_cfg = TsmTrendConfig(include_funding=funding)
    erc_cfg = TsmTrendConfig(include_funding=funding, portfolio_erc=True)
    return {
        "include_funding": funding,
        "base": _metrics(run_tsm_trend_backtest(bars, base_cfg), base_cfg),
        "erc": _metrics(run_tsm_trend_backtest(bars, erc_cfg), erc_cfg),
    }


def _edges_ms() -> tuple[int, ...]:
    return tuple(int(pd.Timestamp(d, tz="UTC").timestamp() * 1000) for d in _PERIOD_EDGES)


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


def _sub_masks(base: TsmTrendResult, edges: tuple[int, ...]) -> list[tuple[str, list[bool]]]:
    out = []
    for i, label in enumerate(_PERIOD_LABELS):
        lo, hi = edges[i], edges[i + 1]
        out.append((label, [lo <= t < hi for t in base.rebalance_times]))
    return out


def _btc_masks(bars: pd.DataFrame, base: TsmTrendResult) -> list[tuple[str, list[bool]]]:
    price = bars.pivot(index="open_time", columns="symbol", values="log_price").sort_index()
    if _BTC not in price.columns:
        return []
    trailing = (price[_BTC] - price[_BTC].shift(_LOOKBACK_H)).reindex(base.rebalance_times)
    up = [bool(v > 0) for v in trailing.to_numpy()]
    return [("BTC_up", up), ("BTC_down", [not u for u in up])]


def _cmp_table(base, erc, base_cfg, erc_cfg, masks) -> list[dict]:
    return [
        {
            "label": label,
            "base": _metrics(_slice(base, mask), base_cfg),
            "erc": _metrics(_slice(erc, mask), erc_cfg),
        }
        for label, mask in masks
    ]


def _write_report(payload: dict) -> None:
    h = payload["headline"]
    b, e = h["base"], h["erc"]
    lines = [
        "# TASK-TSM-003 -- ERC Portfolio Construction Dev Run (DEVELOPMENT, no verdict)",
        "",
        "Per `docs/pre_registers/TASK-TSM-003.md` (ADR-0031, Line 3). Base = "
        "vol-targeted TSM with funding (naive inverse-vol within each sleeve); ERC = "
        "equal risk contribution within each sleeve (correlation-aware, 90d causal "
        "covariance), preserving base direction and L/S gross. Params fixed a priori. "
        "**Development-window result -- NOT a promotion; promotion is OOS-gated.** ERC "
        "is more complex (covariance + solver), so per ADR-0031 the gain must justify "
        "the complexity.",
        "",
        "## Headline (full dev window)",
        "",
        "| Metric | Base | ERC |",
        "|---|---:|---:|",
        f"| Sharpe | {b['tsm_sharpe']:.3f} | {e['tsm_sharpe']:.3f} |",
        f"| Max drawdown | {b['tsm_max_drawdown']:.4f} | {e['tsm_max_drawdown']:.4f} |",
        f"| Net PnL | {b['tsm_net_pnl']:.4f} | {e['tsm_net_pnl']:.4f} |",
        f"| Mean turnover | {b['mean_turnover']:.4f} | {e['mean_turnover']:.4f} |",
        f"| Rebalances | {b['n_rebalances']} | {e['n_rebalances']} |",
        "",
        "## Sub-period stability (Sharpe)",
        "",
        "| Period | Base | ERC |",
        "|---|---:|---:|",
    ]
    lines += [_row(r) for r in payload["sub_periods"]]
    lines += ["", "## BTC regime (Sharpe)", "", "| Regime | Base | ERC |", "|---|---:|---:|"]
    lines += [_row(r) for r in payload["btc_regime"]]
    lines += [
        "",
        "## Cost sensitivity (Sharpe)",
        "",
        "| Cost bps/leg | Base | ERC |",
        "|---|---:|---:|",
    ]
    for r in payload["cost_sensitivity"]:
        label = f"{r['cost_bps_per_leg']:.0f}"
        lines.append(_row({"label": label, "base": r["base"], "erc": r["erc"]}))
    lines += [
        "",
        "## Funding sensitivity (Sharpe)",
        "",
        "| include_funding | Base | ERC |",
        "|---|---:|---:|",
    ]
    for r in payload["funding_sensitivity"]:
        label = str(r["include_funding"])
        lines.append(_row({"label": label, "base": r["base"], "erc": r["erc"]}))
    lines += ["", "## Reading", "", _reading(payload), ""]
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _row(r: dict) -> str:
    def fmt(d: dict) -> str:
        return "n/a" if d["sharpe"] is None else f"{d['sharpe']:.3f}"

    return f"| {r['label']} | {fmt(r['base'])} | {fmt(r['erc'])} |"


def _reading(payload: dict) -> str:
    b, e = payload["headline"]["base"], payload["headline"]["erc"]
    d_sharpe = e["tsm_sharpe"] - b["tsm_sharpe"]
    d_dd = e["tsm_max_drawdown"] - b["tsm_max_drawdown"]

    def helps_all(key: str) -> bool:
        return all(
            r["erc"]["sharpe"] is not None
            and r["base"]["sharpe"] is not None
            and r["erc"]["sharpe"] >= r["base"]["sharpe"]
            for r in payload[key]
        )

    def dd_all(key: str) -> bool:
        return all(
            r["erc"]["max_dd"] is not None
            and r["base"]["max_dd"] is not None
            and r["erc"]["max_dd"] <= r["base"]["max_dd"]
            for r in payload[key]
        )

    consistent = helps_all("sub_periods") and helps_all("btc_regime")
    dd_better = d_dd <= 0 and dd_all("sub_periods") and dd_all("btc_regime")
    verdict = (
        "CANDIDATE for OOS: ERC improves Sharpe AND reduces drawdown, consistently "
        "across all 3 sub-periods AND both BTC regimes, justifying the added "
        "complexity."
        if (d_sharpe > 0 and dd_better and consistent)
        else "REJECTED as a dev candidate: no CONSISTENT risk-adjusted improvement that "
        "justifies the covariance+solver complexity (ADR-0031 prefers simple robust "
        "gains). Per the pre-registration, a gain seen only in aggregate or one regime "
        "is treated as a likely false positive. Hypothesis closed with this negative "
        "result; proceed to Line 4 (meta-labeling / ML as an operation filter)."
    )
    return (
        f"ERC vs base: Sharpe {b['tsm_sharpe']:.3f} -> {e['tsm_sharpe']:.3f} "
        f"(delta {d_sharpe:+.3f}); maxDD {b['tsm_max_drawdown']:.4f} -> "
        f"{e['tsm_max_drawdown']:.4f} (delta {d_dd:+.4f}). Sharpe consistent across "
        f"sub-periods AND BTC regimes: {consistent}; drawdown better everywhere: "
        f"{dd_better}. {verdict}"
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
