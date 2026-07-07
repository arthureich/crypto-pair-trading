#!/usr/bin/env python3
"""Payoff distribution/attribution study (Research Family D, Phase 1).

Diagnostic only -- per project_control/DECISIONS.md ADR-0015. Analyzes the
EXACT trades already produced by the pre-registered TSREV primary cell
(Family A, time-series reversal, 24h, out-of-sample), same config, no
re-tuning, no new backtest methodology, no gate. Answers: where does the
drawdown come from (loss concentration, temporal/symbol/side/volatility/
funding/liquidity clustering)? Generates hypotheses for a future,
separately pre-registered Phase 2 -- does not itself decide anything.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.tsrev import (  # noqa: E402
    TimeSeriesReversalConfig,
    TradeStatus,
    run_time_series_reversal_backtest,
)

BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz"
)
REPORT_MD = PROJECT_ROOT / "reports/tsrev_payoff_attribution.md"
OOS_START = "2025-06-01"
PRIMARY_HORIZON = 24


def main() -> int:
    bars = pd.read_csv(
        BARS_CSV,
        usecols=["symbol", "open_time", "log_price", "funding_rate_asof", "quote_volume"],
    )
    signal_bars = bars[["symbol", "open_time", "log_price"]].copy()

    oos_start_ms = int(pd.Timestamp(OOS_START, tz="UTC").timestamp() * 1000)
    config = TimeSeriesReversalConfig(horizon_hours=PRIMARY_HORIZON)
    trades = run_time_series_reversal_backtest(signal_bars, config)

    oos_resolved = [
        t for t in trades if t.status is TradeStatus.RESOLVED and t.entry_time >= oos_start_ms
    ]
    print(f"OOS resolved trades: {len(oos_resolved)}", file=sys.stderr)

    lookup = bars.set_index(["symbol", "open_time"])
    rows = []
    for t in oos_resolved:
        key = (t.symbol, t.entry_time)
        funding = lookup.loc[key, "funding_rate_asof"] if key in lookup.index else float("nan")
        volume = lookup.loc[key, "quote_volume"] if key in lookup.index else float("nan")
        rows.append(
            {
                "symbol": t.symbol,
                "side": t.side.value,
                "entry_time": t.entry_time,
                "entry_sigma_h": t.entry_sigma_h,
                "gross_bps": t.weight * t.gross_return * 10_000.0,
                "net_bps": t.weight * t.net_return * 10_000.0,
                "weight": t.weight,
                "funding_rate_asof": funding,
                "quote_volume": volume,
            }
        )
    df = pd.DataFrame(rows)
    df["month"] = pd.to_datetime(df["entry_time"], unit="ms").dt.to_period("M").astype(str)

    sections = []
    sections.append(_loss_concentration(df))
    sections.append(_temporal_clustering(df))
    sections.append(_symbol_clustering(df))
    sections.append(_side_clustering(df))
    sections.append(_volatility_clustering(df))
    sections.append(_funding_clustering(df))
    sections.append(_liquidity_clustering(df))

    for title, body in sections:
        print(f"\n=== {title} ===")
        print(body)

    _write_report(len(oos_resolved), sections)
    print(f"\nWrote {REPORT_MD}", file=sys.stderr)
    return 0


def _first_crossing_fraction(cumulative: pd.Series, total: float, share: float, n: int) -> float:
    """Smallest fraction of (sorted, most-extreme-first) entries whose

    cumulative sum already reaches ``share`` of ``total`` (both negative
    for losses). ``cumulative`` must be monotonically moving away from
    zero (sorted most-extreme-first) -- NOT a boolean-count over the
    whole series, which would silently count entries AFTER the crossing
    too and could report a smaller fraction for a *larger* share.
    """

    if n == 0:
        return float("nan")
    threshold = share * total
    crossed = cumulative.to_numpy() <= threshold
    if not crossed.any():
        return 1.0
    first_index = int(crossed.argmax())
    return (first_index + 1) / n


def _loss_concentration(df: pd.DataFrame) -> tuple[str, str]:
    losers = df[df["net_bps"] < 0].sort_values("net_bps")
    total_loss = losers["net_bps"].sum()
    cumulative = losers["net_bps"].cumsum()
    n_losers = len(losers)
    frac_50 = _first_crossing_fraction(cumulative, total_loss, 0.5, n_losers)
    frac_80 = _first_crossing_fraction(cumulative, total_loss, 0.8, n_losers)
    body = (
        f"total losing trades: {n_losers} / {len(df)} ({n_losers / len(df):.1%})\n"
        f"total loss (bps): {total_loss:.2f}\n"
        f"fraction of LOSING trades responsible for 50% of total loss: {frac_50:.1%}\n"
        f"fraction of LOSING trades responsible for 80% of total loss: {frac_80:.1%}\n"
        f"worst 10 trades (bps): {losers['net_bps'].head(10).round(2).tolist()}"
    )
    return "Loss concentration (Pareto)", body


def _temporal_clustering(df: pd.DataFrame) -> tuple[str, str]:
    by_month = df.groupby("month")["net_bps"].agg(["sum", "count", "mean"])
    return "Temporal clustering (by month, OOS)", by_month.round(2).to_string()


def _symbol_clustering(df: pd.DataFrame) -> tuple[str, str]:
    by_symbol = df.groupby("symbol").agg(
        net_bps_sum=("net_bps", "sum"),
        count=("net_bps", "size"),
        win_rate=("net_bps", lambda s: (s > 0).mean()),
    )
    return "Symbol clustering", by_symbol.sort_values("net_bps_sum").round(3).to_string()


def _side_clustering(df: pd.DataFrame) -> tuple[str, str]:
    by_side = df.groupby("side").agg(
        net_bps_sum=("net_bps", "sum"),
        count=("net_bps", "size"),
        win_rate=("net_bps", lambda s: (s > 0).mean()),
        mean_net_bps=("net_bps", "mean"),
    )
    title = "Side clustering (LONG=bet on bounce after drop, SHORT=bet on pullback after rise)"
    return title, by_side.round(3).to_string()


def _volatility_clustering(df: pd.DataFrame) -> tuple[str, str]:
    df = df.copy()
    labels = ["Q1_low_vol", "Q2", "Q3", "Q4_high_vol"]
    df["sigma_quartile"] = pd.qcut(df["entry_sigma_h"], 4, labels=labels)
    by_q = df.groupby("sigma_quartile").agg(
        net_bps_sum=("net_bps", "sum"),
        count=("net_bps", "size"),
        win_rate=("net_bps", lambda s: (s > 0).mean()),
    )
    return "Entry-volatility clustering (quartiles of entry_sigma_h)", by_q.round(3).to_string()


def _funding_clustering(df: pd.DataFrame) -> tuple[str, str]:
    valid = df.dropna(subset=["funding_rate_asof"]).copy()
    if valid.empty:
        return "Funding-rate clustering", "no valid funding_rate_asof data at entry"
    labels = ["Q1_low", "Q2", "Q3", "Q4_high"]
    valid["funding_quartile"] = pd.qcut(
        valid["funding_rate_asof"], 4, labels=labels, duplicates="drop"
    )
    by_q = valid.groupby("funding_quartile").agg(
        net_bps_sum=("net_bps", "sum"),
        count=("net_bps", "size"),
        win_rate=("net_bps", lambda s: (s > 0).mean()),
    )
    corr = valid["funding_rate_asof"].corr(valid["net_bps"])
    body = f"corr(funding_rate_asof, net_bps) = {corr:.4f}\n\n{by_q.round(3).to_string()}"
    return "Funding-rate clustering at entry", body


def _liquidity_clustering(df: pd.DataFrame) -> tuple[str, str]:
    valid = df.dropna(subset=["quote_volume"]).copy()
    if valid.empty:
        return "Liquidity clustering", "no valid quote_volume data at entry"
    labels = ["Q1_low_liq", "Q2", "Q3", "Q4_high_liq"]
    valid["volume_quartile"] = pd.qcut(valid["quote_volume"], 4, labels=labels)
    by_q = valid.groupby("volume_quartile").agg(
        net_bps_sum=("net_bps", "sum"),
        count=("net_bps", "size"),
        win_rate=("net_bps", lambda s: (s > 0).mean()),
    )
    return "Liquidity clustering (quote_volume quartiles at entry bar)", by_q.round(3).to_string()


def _write_report(trade_count: int, sections: list[tuple[str, str]]) -> None:
    lines = [
        "# TSREV Payoff Distribution/Attribution Study (Research Family D, Phase 1)",
        "",
        "Diagnostic only, per `project_control/DECISIONS.md` ADR-0015. No gate, "
        "no new strategy, no re-tuning -- analyzes the exact trades already "
        "produced by the pre-registered TSREV primary cell (Family A, 24h, "
        f"out-of-sample). {trade_count} resolved OOS trades analyzed.",
        "",
    ]
    for title, body in sections:
        lines.append(f"## {title}")
        lines.append("")
        lines.append("```text")
        lines.append(body)
        lines.append("```")
        lines.append("")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
