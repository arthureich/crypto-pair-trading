"""Run the canonical Sprint 8 (roadmap) triple-barrier statistical backtest.

Evaluates all 41 Sprint 7 statistical candidate pairs (not the 31 cost-gated
or 13 backtest-approved pairs from the non-canonical Sprint 8/9 -- see
project_control/DECISIONS.md ADR-0009 for why this universe was chosen) on a
candle-level (1h bar) backtest with a conservative FIXED fee/slippage
assumption, distinct from Sprint 9's real tick-level execution-cost evidence.

Real data only: reads the already-normalized, checksum-verified June-2023
through May-2026 hourly bars produced by Sprint 7 (TASK-007-09). No mocked or
synthetic input.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest.statistical_backtest import (  # noqa: E402
    StatisticalBacktestConfig,
    TradeStatus,
    run_pair_statistical_backtest,
    summarize_statistical_backtest,
)

DEFAULT_BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv"
)
_NORMALIZED_DIR = PROJECT_ROOT / "data/research/binance_public/normalized"
DEFAULT_RESEARCH_GATE_JSON = (
    _NORMALIZED_DIR / "sprint7_binance_usdm_202306_202605_research_gate.json"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data/research/binance_public/cost_pilot"
EXPECTED_PAIR_COUNT = 41


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bars-csv", type=Path, default=DEFAULT_BARS_CSV)
    parser.add_argument("--research-gate-json", type=Path, default=DEFAULT_RESEARCH_GATE_JSON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def load_pairs_and_funding(research_gate_json: Path) -> dict[str, float]:
    payload = json.loads(research_gate_json.read_text(encoding="utf-8"))
    accepted = payload["accepted_pairs"]
    if len(accepted) != EXPECTED_PAIR_COUNT:
        raise ValueError(
            f"expected {EXPECTED_PAIR_COUNT} Sprint 7 statistical pairs, got {len(accepted)}"
        )
    funding_by_pair = {}
    for entry in accepted:
        if entry["statistical_status"] != "ACCEPT":
            raise ValueError(f"pair {entry['pair']} is not statistical_status=ACCEPT")
        funding_by_pair[entry["pair"]] = float(entry["funding_carry_bps_per_day"])
    return funding_by_pair


def _trade_to_dict(trade) -> dict:
    payload = asdict(trade)
    payload["side"] = str(trade.side)
    payload["outcome"] = str(trade.outcome)
    payload["status"] = str(trade.status)
    return payload


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading bars from {args.bars_csv} ...")
    bars = pd.read_csv(args.bars_csv, usecols=["symbol", "open_time", "log_price"])
    print(f"Loaded {len(bars)} bar rows across {bars['symbol'].nunique()} symbols.")

    funding_by_pair = load_pairs_and_funding(args.research_gate_json)
    config = StatisticalBacktestConfig()

    per_pair_json = {}
    per_pair_csv_rows = []
    all_resolved_trades = []
    approved_pairs = []
    rejected_pairs = []

    for pair in sorted(funding_by_pair):
        funding_carry = funding_by_pair[pair]
        trades = run_pair_statistical_backtest(
            bars, pair, funding_carry_bps_per_day=funding_carry, config=config
        )
        metrics = summarize_statistical_backtest(trades)
        resolved = [t for t in trades if t.status is TradeStatus.RESOLVED]
        unresolved_no_data = len(trades) - len(resolved)
        all_resolved_trades.extend(resolved)

        if metrics.profit_factor_gate_pass:
            approved_pairs.append(pair)
        else:
            rejected_pairs.append(pair)

        per_pair_json[pair] = {
            "funding_carry_bps_per_day": funding_carry,
            "metrics": asdict(metrics),
            "profit_factor_gate_pass": metrics.profit_factor_gate_pass,
            "unresolved_no_data_count": unresolved_no_data,
            "trades": [_trade_to_dict(t) for t in trades],
        }
        per_pair_csv_rows.append(
            {
                "pair": pair,
                "funding_carry_bps_per_day": funding_carry,
                "trade_count": metrics.trade_count,
                "unresolved_no_data_count": unresolved_no_data,
                "gross_pnl_bps": metrics.gross_pnl_bps,
                "cost_bps": metrics.cost_bps,
                "net_pnl_bps": metrics.net_pnl_bps,
                "hit_rate": metrics.hit_rate,
                "profit_factor": metrics.profit_factor,
                "sharpe": metrics.sharpe,
                "sortino": metrics.sortino,
                "max_drawdown_bps": metrics.max_drawdown_bps,
                "avg_win_bps": metrics.avg_win_bps,
                "avg_loss_bps": metrics.avg_loss_bps,
                "avg_bars_held": metrics.avg_bars_held,
                "turnover_notional": metrics.turnover_notional,
                "profit_factor_gate_pass": metrics.profit_factor_gate_pass,
            }
        )
        print(
            f"{pair}: {metrics.trade_count} trades "
            f"({unresolved_no_data} unresolved NO_DATA), "
            f"profit_factor={metrics.profit_factor:.3f}, "
            f"net_pnl_bps={metrics.net_pnl_bps:.2f}, "
            f"gate_pass={metrics.profit_factor_gate_pass}"
        )

    portfolio_metrics = summarize_statistical_backtest(tuple(all_resolved_trades))
    print(
        f"\nPortfolio (all {len(funding_by_pair)} pairs pooled): "
        f"{portfolio_metrics.trade_count} resolved trades, "
        f"profit_factor={portfolio_metrics.profit_factor:.3f}, "
        f"net_pnl_bps={portfolio_metrics.net_pnl_bps:.2f}"
    )
    print(
        f"Per-pair gate: {len(approved_pairs)}/{len(funding_by_pair)} pairs pass "
        f"profit factor >= 1.10; {len(rejected_pairs)} rejected."
    )

    summary = {
        "sprint": "8_canonical",
        "universe": "41_sprint7_statistical_pairs",
        "config": asdict(config),
        "approved_pairs": sorted(approved_pairs),
        "rejected_pairs": sorted(rejected_pairs),
        "approved_pair_count": len(approved_pairs),
        "rejected_pair_count": len(rejected_pairs),
        "portfolio_metrics": asdict(portfolio_metrics),
        "portfolio_gate_pass": portfolio_metrics.profit_factor_gate_pass,
        "per_pair": per_pair_json,
    }

    output_json = args.output_dir / "sprint8_canonical_backtest_results.json"
    output_csv = args.output_dir / "sprint8_canonical_backtest_pair_results.csv"
    output_json.write_text(json.dumps(summary, indent=2, allow_nan=True), encoding="utf-8")
    pd.DataFrame(per_pair_csv_rows).to_csv(output_csv, index=False)
    print(f"\nWrote {output_json}")
    print(f"Wrote {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
