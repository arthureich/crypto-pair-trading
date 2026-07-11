#!/usr/bin/env python3
"""TASK-FC-II-006: robustness decomposition of the vol-targeted TSM (FC-II-005).

Per docs/pre_registers/TASK-FC-II-006.md (ADR-0027). Descriptive, in-sample;
NO verdict. Decides whether the TSM lead is broad (worth an OOS pursuit) or
concentrated in one sub-period / the short leg / a single BTC regime (fragile).
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

from src.research.tsm_trend import (  # noqa: E402
    TsmTrendConfig,
    _max_drawdown,
    _sharpe,
    run_tsm_trend_backtest,
)

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
OUTPUT_JSON = PROJECT_ROOT / "data/research/binance_public/cost_pilot/fc_tsm_robustness.json"
REPORT_MD = PROJECT_ROOT / "reports/fc_tsm_robustness.md"
_HOURS_PER_YEAR = 24 * 365

PERIOD_LABELS = ("2023-06_2024-05", "2024-06_2025-05", "2025-06_2026-05")
PERIOD_BOUNDARIES = tuple(
    int(pd.Timestamp(d, tz="UTC").timestamp() * 1000)
    for d in ("2023-06-01", "2024-06-01", "2025-06-01", "2026-06-01")
)


def main() -> int:
    bars = pd.read_csv(BARS_CSV, usecols=["symbol", "open_time", "log_price"])
    config = TsmTrendConfig()
    result = run_tsm_trend_backtest(bars, config)
    ann = math.sqrt(_HOURS_PER_YEAR / config.hold_hours)

    times = np.array(result.rebalance_times)
    net = np.array(result.tsm_net)
    long_s = np.array(result.tsm_long_sleeve)
    short_s = np.array(result.tsm_short_sleeve)

    # 1) sub-period
    sub = {}
    for label, start, end in zip(
        PERIOD_LABELS, PERIOD_BOUNDARIES[:-1], PERIOD_BOUNDARIES[1:], strict=True
    ):
        mask = (times >= start) & (times < end)
        sub[label] = {
            "n": int(mask.sum()),
            "sharpe": _sharpe(net[mask], ann),
            "net_pnl": float(net[mask].sum()),
            "max_drawdown": _max_drawdown(net[mask]),
        }

    # 2) leg contribution (same book; long + short = gross)
    leg = {
        "long_sleeve_net_pnl": float(long_s.sum()),
        "short_sleeve_net_pnl": float(short_s.sum()),
        "long_sleeve_sharpe": _sharpe(long_s, ann),
        "short_sleeve_sharpe": _sharpe(short_s, ann),
    }

    # 3) regime by BTC 28d trailing return sign at each rebalance
    btc = bars[bars["symbol"] == "BTCUSDT"].set_index("open_time")["log_price"].sort_index()
    btc_trailing = (btc - btc.shift(config.lookback_hours)).reindex(times)
    up = btc_trailing.to_numpy() > 0
    down = btc_trailing.to_numpy() < 0
    regime = {
        "btc_up": {
            "n": int(up.sum()),
            "sharpe": _sharpe(net[up], ann),
            "net_pnl": float(net[up].sum()),
        },
        "btc_down": {
            "n": int(down.sum()),
            "sharpe": _sharpe(net[down], ann),
            "net_pnl": float(net[down].sum()),
        },
    }

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "task": "TASK-FC-II-006 TSM robustness decomposition",
        "phase": "DEVELOPMENT descriptive; NO verdict",
        "sub_period": sub,
        "leg": leg,
        "regime": regime,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_report(payload)

    for label, m in sub.items():
        print(
            f"subperiod {label}: Sharpe={m['sharpe']:.3f} net={m['net_pnl']:.4f} n={m['n']}",
            file=sys.stderr,
        )
    print(
        f"leg: long net={leg['long_sleeve_net_pnl']:.4f} / short net="
        f"{leg['short_sleeve_net_pnl']:.4f}",
        file=sys.stderr,
    )
    print(
        f"regime: BTC-up Sharpe={regime['btc_up']['sharpe']:.3f} (n={regime['btc_up']['n']}) / "
        f"BTC-down Sharpe={regime['btc_down']['sharpe']:.3f} (n={regime['btc_down']['n']})",
        file=sys.stderr,
    )
    print(f"Wrote {OUTPUT_JSON}", file=sys.stderr)
    print(f"Wrote {REPORT_MD}", file=sys.stderr)
    return 0


def _write_report(payload: dict) -> None:
    sub = payload["sub_period"]
    leg = payload["leg"]
    reg = payload["regime"]
    lines = [
        "# TASK-FC-II-006 -- Vol-Targeted TSM Robustness Decomposition",
        "",
        "Per `docs/pre_registers/TASK-FC-II-006.md` (ADR-0027). Descriptive, "
        "in-sample; NO verdict. Decides whether the TSM lead (FC-II-005) is "
        "broad (worth OOS) or fragile (concentrated in a sub-period / the short "
        "leg / a single BTC regime).",
        "",
        "## By sub-period",
        "",
        "| Sub-period | Sharpe | Net PnL | Max drawdown | N |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, m in sub.items():
        lines.append(
            f"| {label} | {m['sharpe']:.3f} | {m['net_pnl']:.4f} | "
            f"{m['max_drawdown']:.4f} | {m['n']} |"
        )
    lines.extend(
        [
            "",
            "## By leg (same book; long + short = gross)",
            "",
            f"- Long sleeve net PnL: {leg['long_sleeve_net_pnl']:.4f} "
            f"(Sharpe {leg['long_sleeve_sharpe']:.3f})",
            f"- Short sleeve net PnL: {leg['short_sleeve_net_pnl']:.4f} "
            f"(Sharpe {leg['short_sleeve_sharpe']:.3f})",
            "",
            "## By BTC regime (28d trailing sign at each rebalance)",
            "",
            f"- BTC up: Sharpe {reg['btc_up']['sharpe']:.3f}, net {reg['btc_up']['net_pnl']:.4f} "
            f"(n={reg['btc_up']['n']})",
            f"- BTC down: Sharpe {reg['btc_down']['sharpe']:.3f}, "
            f"net {reg['btc_down']['net_pnl']:.4f} (n={reg['btc_down']['n']})",
            "",
            "## Reading",
            "",
            _verdict(sub, leg, reg),
            "",
        ]
    )
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def _verdict(sub: dict, leg: dict, reg: dict) -> str:
    all_periods_positive = all(m["net_pnl"] > 0 for m in sub.values())
    long_contributes = leg["long_sleeve_net_pnl"] > 0
    both_regimes_positive = reg["btc_up"]["net_pnl"] > 0 and reg["btc_down"]["net_pnl"] > 0
    if all_periods_positive and long_contributes and both_regimes_positive:
        return (
            "BROAD: positive across all 3 sub-periods, the long leg contributes, "
            "and it works in both BTC regimes. The lead is not a single-regime "
            "artifact -> merits a separately pre-registered OOS pursuit."
        )
    reasons = []
    if not all_periods_positive:
        reasons.append("not positive in every sub-period")
    if not long_contributes:
        reasons.append("the long leg does not contribute (short-leg-only)")
    if not both_regimes_positive:
        reasons.append("it works in only one BTC regime")
    return (
        "CONCENTRATED / FRAGILE: " + "; ".join(reasons) + ". The in-sample Sharpe is "
        "driven by a narrow slice, consistent with a regime-dependent short-alt bet "
        "rather than a robust edge -> do NOT spend OOS effort on it now; the price "
        "family stays effectively closed pending a genuinely different construction."
    )


def _json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(v) for v in value]
    if isinstance(value, bool | str | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    raise SystemExit(main())
