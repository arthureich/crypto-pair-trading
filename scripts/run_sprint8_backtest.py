#!/usr/bin/env python3
"""Run the Sprint 8 offline cost-aware walk-forward backtest.

The runner consumes only Sprint 8 approved pairs, June-2023 bars, and verified
hourly cost evidence. It writes research artifacts; it does not touch live
execution, ledger, exchange endpoints, or raw Binance ZIP files.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import numbers
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research import (  # noqa: E402
    Sprint8UniverseContract,
    WalkForwardSplitConfig,
    build_walk_forward_splits,
    generate_pair_signal_intents,
    load_sprint8_universe_contract,
    pair_symbols,
    run_cost_aware_backtest,
    summarize_backtest_metrics,
)

DEFAULT_OUTPUT_JSON = (
    PROJECT_ROOT / "data/research/binance_public/cost_pilot/sprint8_backtest_results.json"
)
DEFAULT_OUTPUT_CSV = (
    PROJECT_ROOT / "data/research/binance_public/cost_pilot/sprint8_backtest_pair_results.csv"
)


def main() -> int:
    args = _parse_args()
    contract = load_sprint8_universe_contract(args.contract_json)
    bars = pd.read_csv(args.bars_csv or _contract_path(contract, "bars_csv"), low_memory=False)
    hourly_cost = pd.read_csv(
        args.hourly_cost_csv or _contract_path(contract, "hourly_cost_csv"),
        low_memory=False,
    )
    folds = build_walk_forward_splits(
        bars,
        WalkForwardSplitConfig(
            train_bars=args.train_bars,
            test_bars=args.test_bars,
            step_bars=args.step_bars,
        ),
    )

    pair_results = [
        _backtest_pair(
            pair=pair,
            bars=bars,
            hourly_cost=hourly_cost,
            contract=contract,
            folds=folds,
            zscore_window=args.zscore_window,
            entry_zscore=args.entry_zscore,
            target_notional=args.target_notional,
        )
        for pair in contract.approved_pairs
    ]
    payload = _payload(
        args=args,
        contract=contract,
        folds=folds,
        pair_results=pair_results,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_pair_csv(args.output_csv, pair_results)
    print(json.dumps(_json_ready(payload["summary"]), allow_nan=False, indent=2, sort_keys=True))
    return 0


def _backtest_pair(
    *,
    pair: str,
    bars: pd.DataFrame,
    hourly_cost: pd.DataFrame,
    contract: Sprint8UniverseContract,
    folds: tuple[Any, ...],
    zscore_window: int,
    entry_zscore: float,
    target_notional: float,
) -> dict[str, Any]:
    pair_bars = _pair_frame(bars, pair)
    intents = generate_pair_signal_intents(
        bars,
        pair,
        contract=contract,
        zscore_window=zscore_window,
        entry_zscore=entry_zscore,
        target_notional=target_notional,
    )
    walk_forward_intents = [
        intent for intent in intents if _is_in_test_window(intent.created_at, folds)
    ]
    trades = []
    dropped_reasons: list[str] = []
    for intent in walk_forward_intents:
        edge = _one_hour_gross_edge_bps(intent, pair_bars)
        if edge is None:
            dropped_reasons.append("NO_NEXT_BAR_FOR_SIGNAL")
            continue
        gross_edge, exit_time = edge
        cost_map = _round_trip_symbol_cost_map(
            hourly_cost, intent.pair, intent.created_at, exit_time
        )
        result = run_cost_aware_backtest(
            [intent],
            gross_edge_bps_by_signal_id={intent.signal_id: gross_edge},
            symbol_cost_bps=cost_map,
            contract=contract,
        )
        trades.extend(result.trades)

    metrics = summarize_backtest_metrics(trades)
    status = _backtest_status(metrics.trade_count, metrics.net_pnl_bps)
    return {
        "pair": pair,
        "status": status,
        "observation_count": int(len(pair_bars)),
        "signal_count": int(len(intents)),
        "walk_forward_signal_count": int(len(walk_forward_intents)),
        "trade_count": metrics.trade_count,
        "gross_pnl_bps": metrics.gross_pnl_bps,
        "cost_bps": metrics.cost_bps,
        "net_pnl_bps": metrics.net_pnl_bps,
        "hit_rate": metrics.hit_rate,
        "max_drawdown_bps": metrics.max_drawdown_bps,
        "turnover_notional": metrics.turnover_notional,
        "net_pnl_quote": metrics.net_pnl_quote,
        "dropped_signal_count": len(dropped_reasons),
        "dropped_reasons": sorted(set(dropped_reasons)),
    }


def _payload(
    *,
    args: argparse.Namespace,
    contract: Sprint8UniverseContract,
    folds: tuple[Any, ...],
    pair_results: list[dict[str, Any]],
) -> dict[str, Any]:
    approved = [row for row in pair_results if row["status"] == "BACKTEST_APPROVED"]
    rejected = [row for row in pair_results if row["status"] != "BACKTEST_APPROVED"]
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "contract_json": str(args.contract_json),
        "bars_csv": str(args.bars_csv or _contract_path(contract, "bars_csv")),
        "hourly_cost_csv": str(args.hourly_cost_csv or _contract_path(contract, "hourly_cost_csv")),
        "evidence_scope": contract.evidence_scope,
        "methodology": {
            "signal": "offline SignalIntent from causal rolling z-score on Kalman spread",
            "trade_horizon": "one 1h bar after signal creation",
            "cost_policy": (
                "per-leg median spread bps with cost_available_time <= signal created_at"
            ),
            "walk_forward": {
                "policy": "only signals inside fold test windows are evaluated",
                "train_bars": args.train_bars,
                "test_bars": args.test_bars,
                "step_bars": args.step_bars,
                "fold_count": len(folds),
            },
            "entry_zscore": args.entry_zscore,
            "zscore_window": args.zscore_window,
            "target_notional": args.target_notional,
        },
        "summary": _summary(approved, rejected, pair_results),
        "folds": [asdict(fold) for fold in folds],
        "pair_results": pair_results,
    }


def _summary(
    approved: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    pair_results: list[dict[str, Any]],
) -> dict[str, Any]:
    portfolio_net_pnl_quote = float(sum(row["net_pnl_quote"] for row in pair_results))
    return {
        "pairs_evaluated": len(pair_results),
        "pairs_backtest_approved": len(approved),
        "pairs_backtest_rejected": len(rejected),
        "total_trades": int(sum(row["trade_count"] for row in pair_results)),
        "total_net_pnl_bps": float(sum(row["net_pnl_bps"] for row in pair_results)),
        "total_cost_bps": float(sum(row["cost_bps"] for row in pair_results)),
        "portfolio_net_pnl_quote": portfolio_net_pnl_quote,
        "backtest_approved_pairs": [row["pair"] for row in approved],
        "backtest_rejected_pairs": [row["pair"] for row in rejected],
        # Any single approved pair, NOT an aggregate portfolio verdict. A
        # positive result here can coexist with a negative
        # portfolio_net_pnl_quote across all 31 evaluated pairs equally
        # weighted -- see portfolio_gate_pass for the aggregate view.
        "any_pair_backtest_approved": bool(approved),
        "portfolio_gate_pass": portfolio_net_pnl_quote > 0.0,
    }


def _pair_frame(bars: pd.DataFrame, pair: str) -> pd.DataFrame:
    symbol_a, symbol_b = pair_symbols(pair)
    left = (
        bars.loc[bars["symbol"] == symbol_a, ["open_time", "log_price"]]
        .rename(columns={"log_price": "log_price_a"})
        .copy()
    )
    right = (
        bars.loc[bars["symbol"] == symbol_b, ["open_time", "log_price"]]
        .rename(columns={"log_price": "log_price_b"})
        .copy()
    )
    joined = left.merge(right, on="open_time", how="inner", sort=True).dropna()
    return joined.reset_index(drop=True)


def _one_hour_gross_edge_bps(intent: Any, pair_bars: pd.DataFrame) -> tuple[float, int] | None:
    """Return (beta-weighted gross edge bps, exit bar open_time) or None.

    The signal's beta comes from the Kalman spread `log_price_a - beta *
    log_price_b`; weighting leg B's return by that same beta keeps the
    simulated PnL consistent with the spread the entry signal was measured
    on. An unweighted 1:1 combination would price a different, uncontrolled
    exposure than the one the z-score gate actually triggered on.
    """

    matches = pair_bars.index[pair_bars["open_time"] == intent.created_at].tolist()
    if not matches:
        return None
    index = matches[0]
    if index + 1 >= len(pair_bars):
        return None
    current = pair_bars.iloc[index]
    next_bar = pair_bars.iloc[index + 1]
    return_a_bps = (float(next_bar["log_price_a"]) - float(current["log_price_a"])) * 10_000.0
    return_b_bps = (float(next_bar["log_price_b"]) - float(current["log_price_b"])) * 10_000.0
    multiplier_a = 1.0 if intent.side_a == "BUY" else -1.0
    multiplier_b = 1.0 if intent.side_b == "BUY" else -1.0
    beta_weight = abs(float(intent.beta))
    edge = float(multiplier_a * return_a_bps + multiplier_b * beta_weight * return_b_bps)
    return edge, int(next_bar["open_time"])


def _is_in_test_window(created_at: int, folds: tuple[Any, ...]) -> bool:
    return any(fold.test_start_time <= created_at <= fold.test_end_time for fold in folds)


def _round_trip_symbol_cost_map(
    hourly_cost: pd.DataFrame,
    pair: str,
    entry_time: int,
    exit_time: int,
) -> dict[str, float]:
    """Return per-symbol entry+exit cost bps for a full round-trip trade.

    A trade opened at ``entry_time`` and closed at ``exit_time`` crosses the
    spread twice per leg (once to enter, once to exit); charging only the
    entry cost understates round-trip cost by roughly half and can make a
    pair look net-profitable when it is not.
    """

    symbol_a, symbol_b = pair_symbols(pair)
    return {
        symbol_a: (
            _latest_symbol_cost_bps(hourly_cost, symbol_a, entry_time)
            + _latest_symbol_cost_bps(hourly_cost, symbol_a, exit_time)
        ),
        symbol_b: (
            _latest_symbol_cost_bps(hourly_cost, symbol_b, entry_time)
            + _latest_symbol_cost_bps(hourly_cost, symbol_b, exit_time)
        ),
    }


def _latest_symbol_cost_bps(hourly_cost: pd.DataFrame, symbol: str, created_at: int) -> float:
    required = {"symbol", "cost_available_time", "median_spread_bps_1h"}
    missing = required.difference(hourly_cost.columns)
    if missing:
        raise ValueError(f"hourly cost missing columns: {sorted(missing)}")
    rows = hourly_cost.loc[
        (hourly_cost["symbol"] == symbol) & (hourly_cost["cost_available_time"] <= created_at),
        ["cost_available_time", "median_spread_bps_1h"],
    ].sort_values("cost_available_time")
    if rows.empty:
        raise ValueError(f"no causal cost available for {symbol} at {created_at}")
    return float(rows.iloc[-1]["median_spread_bps_1h"])


def _backtest_status(trade_count: int, net_pnl_bps: float) -> str:
    if trade_count <= 0:
        return "REJECT_NO_SIGNALS"
    if net_pnl_bps > 0.0:
        return "BACKTEST_APPROVED"
    return "REJECT_NEGATIVE_NET_PNL"


def _contract_path(contract: Sprint8UniverseContract, artifact_key: str) -> Path:
    return PROJECT_ROOT / contract.artifacts[artifact_key]


def _write_pair_csv(path: Path, pair_results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = (
        "pair",
        "status",
        "observation_count",
        "signal_count",
        "walk_forward_signal_count",
        "trade_count",
        "gross_pnl_bps",
        "cost_bps",
        "net_pnl_bps",
        "hit_rate",
        "max_drawdown_bps",
        "turnover_notional",
        "net_pnl_quote",
        "dropped_signal_count",
        "dropped_reasons",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for result in pair_results:
            row = result.copy()
            row["dropped_reasons"] = ";".join(result["dropped_reasons"])
            writer.writerow({column: row.get(column) for column in columns})


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract-json",
        type=Path,
        default=PROJECT_ROOT / "project_control/SPRINT8_UNIVERSE.json",
    )
    parser.add_argument("--bars-csv", type=Path)
    parser.add_argument("--hourly-cost-csv", type=Path)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--zscore-window", type=int, default=168)
    parser.add_argument("--entry-zscore", type=float, default=2.0)
    parser.add_argument("--target-notional", type=float, default=1_000.0)
    parser.add_argument("--train-bars", type=int, default=336)
    parser.add_argument("--test-bars", type=int, default=168)
    parser.add_argument("--step-bars", type=int, default=168)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
