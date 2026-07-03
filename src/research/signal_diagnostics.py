"""Diagnostics for gross edge in canonical Sprint 8 trade results.

This module post-processes already-computed backtest trades. It does not
recompute signals, does not read raw market data, and does not touch execution
or ledger planes.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

RESOLVED_STATUS = "RESOLVED"
UNRESOLVED_NO_DATA_STATUS = "UNRESOLVED_NO_DATA"
VALID_STATUSES = frozenset({RESOLVED_STATUS, UNRESOLVED_NO_DATA_STATUS})
VALID_SIDES = frozenset({"LONG_SPREAD", "SHORT_SPREAD"})
VALID_OUTCOMES = frozenset({"PROFIT", "STOP", "VERTICAL"})
OUTCOME_BUCKETS = ("PROFIT", "STOP", "VERTICAL")
ENTRY_ZSCORE_BUCKET_MIN = 2.0
ENTRY_ZSCORE_BUCKETS = ("2.0-2.5", "2.5-3.0", "3.0+")
BARS_HELD_BUCKETS = ("1h", "2-4h", "5-12h", "13-24h", "25h+")
SIDE_BUCKETS = ("LONG_SPREAD", "SHORT_SPREAD")
SIDE_COMPARISON_COUNT = 2
ONE_HOUR = 1
TWO_HOURS = 2
FOUR_HOURS = 4
FIVE_HOURS = 5
TWELVE_HOURS = 12
THIRTEEN_HOURS = 13
TWENTY_FOUR_HOURS = 24
TWENTY_FIVE_HOURS = 25


class SignalDiagnosticError(ValueError):
    """Raised when signal-diagnostic inputs are malformed."""


def flatten_canonical_trades(payload: dict[str, Any]) -> pd.DataFrame:
    """Flatten canonical Sprint 8 per-pair JSON into resolved trade rows."""

    per_pair = payload.get("per_pair")
    if not isinstance(per_pair, dict):
        raise SignalDiagnosticError("canonical backtest payload must contain per_pair object")

    rows: list[dict[str, Any]] = []
    for pair, pair_payload in per_pair.items():
        if not isinstance(pair_payload, dict):
            raise SignalDiagnosticError(f"per_pair[{pair!r}] must be an object")
        trades = pair_payload.get("trades")
        if not isinstance(trades, list):
            raise SignalDiagnosticError(f"per_pair[{pair!r}] must contain trades list")
        for trade in trades:
            if not isinstance(trade, dict):
                raise SignalDiagnosticError(f"trade for {pair!r} must be an object")
            status = _validated_enum(trade.get("status"), VALID_STATUSES, "status")
            if status != RESOLVED_STATUS:
                continue
            side = _validated_enum(trade.get("side"), VALID_SIDES, "side")
            outcome = _validated_enum(trade.get("outcome"), VALID_OUTCOMES, "outcome")
            entry_zscore = _float_field(trade, "entry_zscore")
            bars_held = _positive_int_field(trade, "bars_held")
            abs_entry_zscore = abs(entry_zscore)
            if abs_entry_zscore < ENTRY_ZSCORE_BUCKET_MIN:
                raise SignalDiagnosticError(
                    f"abs(entry_zscore) must be >= {ENTRY_ZSCORE_BUCKET_MIN}"
                )
            rows.append(
                {
                    "pair": str(trade.get("pair", pair)),
                    "side": side,
                    "entry_time": _int_field(trade, "entry_time"),
                    "entry_zscore": entry_zscore,
                    "abs_entry_zscore": abs_entry_zscore,
                    "exit_time": _int_field(trade, "exit_time"),
                    "outcome": outcome,
                    "bars_held": bars_held,
                    "gross_pnl_bps": _float_field(trade, "gross_pnl_bps"),
                    "cost_bps": _float_field(trade, "cost_bps"),
                    "net_pnl_bps": _float_field(trade, "net_pnl_bps"),
                }
            )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "pair",
                "side",
                "entry_time",
                "entry_zscore",
                "abs_entry_zscore",
                "exit_time",
                "outcome",
                "bars_held",
                "gross_pnl_bps",
                "cost_bps",
                "net_pnl_bps",
            ]
        )
    frame["entry_zscore_bucket"] = _entry_zscore_bucket(frame["abs_entry_zscore"])
    frame["bars_held_bucket"] = _bars_held_bucket(frame["bars_held"])
    return frame


def build_signal_diagnostic_summary(payload: dict[str, Any]) -> dict[str, Any]:
    """Build gross-edge diagnostics from canonical Sprint 8 results."""

    trades = flatten_canonical_trades(payload)
    if trades.empty:
        raise SignalDiagnosticError("no resolved trades available for signal diagnostics")
    overall = _metrics(trades)
    outcome_distribution = _grouped_metrics(trades, "outcome", order=OUTCOME_BUCKETS)
    entry_zscore_buckets = _grouped_metrics(
        trades,
        "entry_zscore_bucket",
        order=ENTRY_ZSCORE_BUCKETS,
    )
    bars_held_buckets = _grouped_metrics(
        trades,
        "bars_held_bucket",
        order=BARS_HELD_BUCKETS,
    )
    side_summary = _grouped_metrics(trades, "side", order=SIDE_BUCKETS)
    pair_summary = sorted(
        _grouped_metrics(trades, "pair"),
        key=lambda row: (row["avg_gross_pnl_bps"], row["trade_count"]),
        reverse=True,
    )
    return {
        "source": "sprint8_canonical_backtest_results",
        "trade_count": int(len(trades)),
        "pair_count": int(trades["pair"].nunique()) if not trades.empty else 0,
        "overall": overall,
        "outcome_distribution": outcome_distribution,
        "entry_zscore_buckets": entry_zscore_buckets,
        "bars_held_buckets": bars_held_buckets,
        "side_summary": side_summary,
        "top_gross_pairs": pair_summary[:10],
        "bottom_gross_pairs": pair_summary[-10:],
        "pair_summary": pair_summary,
        "diagnosis": _diagnosis(
            overall=overall,
            outcome_distribution=outcome_distribution,
            entry_zscore_buckets=entry_zscore_buckets,
            bars_held_buckets=bars_held_buckets,
            side_summary=side_summary,
        ),
    }


def diagnostic_csv_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten diagnostic summary groups for CSV output."""

    rows: list[dict[str, Any]] = []
    for dimension in (
        "outcome_distribution",
        "entry_zscore_buckets",
        "bars_held_buckets",
        "side_summary",
        "pair_summary",
    ):
        for record in summary[dimension]:
            row = {"dimension": dimension, "bucket": record["bucket"]}
            row.update({key: value for key, value in record.items() if key != "bucket"})
            rows.append(row)
    return rows


def _grouped_metrics(
    trades: pd.DataFrame,
    column: str,
    *,
    order: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    if trades.empty:
        return []
    records = []
    for bucket, group in trades.groupby(column, sort=False, observed=True):
        metrics = _metrics(group)
        metrics["bucket"] = str(bucket)
        records.append(metrics)
    if order is not None:
        existing = {record["bucket"]: record for record in records}
        for bucket in order:
            if bucket not in existing:
                empty = _metrics(trades.iloc[0:0])
                empty["bucket"] = bucket
                records.append(empty)
        order_index = {bucket: index for index, bucket in enumerate(order)}
        records.sort(key=lambda row: order_index.get(row["bucket"], len(order_index)))
    return records


def _metrics(trades: pd.DataFrame) -> dict[str, Any]:
    if trades.empty:
        return {
            "trade_count": 0,
            "gross_pnl_bps": 0.0,
            "avg_gross_pnl_bps": math.nan,
            "gross_profit_factor": math.nan,
            "net_pnl_bps": 0.0,
            "avg_net_pnl_bps": math.nan,
            "avg_cost_bps": math.nan,
            "profit_outcome_rate": math.nan,
            "stop_outcome_rate": math.nan,
            "vertical_outcome_rate": math.nan,
            "hit_rate_gross": math.nan,
            "avg_abs_entry_zscore": math.nan,
            "avg_bars_held": math.nan,
        }
    gross = trades["gross_pnl_bps"].astype(float)
    net = trades["net_pnl_bps"].astype(float)
    positive = gross[gross > 0.0]
    negative = gross[gross < 0.0]
    gross_profit = float(positive.sum()) if not positive.empty else 0.0
    gross_loss = float(-negative.sum()) if not negative.empty else 0.0
    return {
        "trade_count": int(len(trades)),
        "gross_pnl_bps": float(gross.sum()),
        "avg_gross_pnl_bps": float(gross.mean()),
        "gross_profit_factor": _profit_factor(gross_profit, gross_loss),
        "net_pnl_bps": float(net.sum()),
        "avg_net_pnl_bps": float(net.mean()),
        "avg_cost_bps": float(trades["cost_bps"].astype(float).mean()),
        "profit_outcome_rate": _outcome_rate(trades, "PROFIT"),
        "stop_outcome_rate": _outcome_rate(trades, "STOP"),
        "vertical_outcome_rate": _outcome_rate(trades, "VERTICAL"),
        "hit_rate_gross": float((gross > 0.0).mean()),
        "avg_abs_entry_zscore": float(trades["abs_entry_zscore"].astype(float).mean()),
        "avg_bars_held": float(trades["bars_held"].astype(float).mean()),
    }


def _diagnosis(
    *,
    overall: dict[str, Any],
    outcome_distribution: list[dict[str, Any]],
    entry_zscore_buckets: list[dict[str, Any]],
    bars_held_buckets: list[dict[str, Any]],
    side_summary: list[dict[str, Any]],
) -> dict[str, Any]:
    notes = []
    recommendations = []
    if overall["avg_gross_pnl_bps"] <= 0.0:
        notes.append("O edge bruto agregado e nao-positivo antes de custos.")
        recommendations.append("Priorizar mudanca no criterio de entrada antes de otimizar custo.")
    else:
        notes.append(
            "Ha edge bruto agregado positivo antes de custos, "
            "mas ele precisa sobreviver ao custo."
        )

    outcome_by_bucket = {row["bucket"]: row for row in outcome_distribution}
    profit_count = outcome_by_bucket.get("PROFIT", {}).get("trade_count", 0)
    stop_count = outcome_by_bucket.get("STOP", {}).get("trade_count", 0)
    if stop_count > profit_count:
        notes.append("STOP ocorre mais vezes que PROFIT; investigar assimetria da barreira.")
        recommendations.append(
            "Testar barrier configs com stop mais distante ou profit mais proximo "
            "em tarefa separada."
        )
    else:
        notes.append(
            "PROFIT ocorre pelo menos tao frequentemente quanto STOP; "
            "foco deve ser payoff medio."
        )

    high_z = _find_bucket(entry_zscore_buckets, "3.0+")
    low_z = _find_bucket(entry_zscore_buckets, "2.0-2.5")
    if high_z and low_z and high_z["avg_gross_pnl_bps"] > low_z["avg_gross_pnl_bps"]:
        recommendations.append("Testar entrada mais seletiva por |z| >= 3.0 em TASK-SIG-002.")
    else:
        notes.append("|z| >= 3.0 nao melhora o gross medio contra a faixa 2.0-2.5.")
        recommendations.append(
            "Nao priorizar aumento simples de |z|; validar filtro de regime/velocidade."
        )

    fast = _find_bucket(bars_held_buckets, "2-4h")
    slow = _find_bucket(bars_held_buckets, "5-12h")
    very_slow = _find_bucket(bars_held_buckets, "13-24h")
    if fast and slow and fast["avg_gross_pnl_bps"] > 0.0 and slow["avg_gross_pnl_bps"] < 0.0:
        notes.append("O edge bruto aparece em reversoes de 2-4h e desaparece em holds de 5h+.")
        recommendations.append(
            "TASK-SIG-002 deve testar cap vertical <=4h como experimento causal, "
            "sem tocar em execucao."
        )
        recommendations.append(
            "Gate por OU half-life curto e hipotese secundaria: exige registrar ou "
            "recalcular half-life por entrada antes de concluir."
        )
    if very_slow and very_slow["trade_count"] > 0 and very_slow["avg_gross_pnl_bps"] < 0.0:
        notes.append("Holds de 13-24h sao poucos, mas extremamente negativos em gross PnL medio.")

    side_edge = sorted(side_summary, key=lambda row: row["avg_gross_pnl_bps"], reverse=True)
    if len(side_edge) >= SIDE_COMPARISON_COUNT:
        best = side_edge[0]
        worst = side_edge[-1]
        notes.append(
            f"Lado com melhor gross medio: {best['bucket']} "
            f"({best['avg_gross_pnl_bps']:.4f} bps/trade); pior: {worst['bucket']} "
            f"({worst['avg_gross_pnl_bps']:.4f} bps/trade)."
        )
    return {
        "notes": notes,
        "recommendations": recommendations,
    }


def _entry_zscore_bucket(abs_zscore: pd.Series) -> pd.Series:
    buckets = pd.cut(
        abs_zscore.astype(float),
        bins=[2.0, 2.5, 3.0, math.inf],
        labels=ENTRY_ZSCORE_BUCKETS,
        include_lowest=True,
        right=False,
    )
    return buckets.astype(str)


def _bars_held_bucket(bars_held: pd.Series) -> pd.Series:
    values = bars_held.astype(int)
    labels = pd.Series(index=values.index, dtype="object")
    labels.loc[values == ONE_HOUR] = "1h"
    labels.loc[(values >= TWO_HOURS) & (values <= FOUR_HOURS)] = "2-4h"
    labels.loc[(values >= FIVE_HOURS) & (values <= TWELVE_HOURS)] = "5-12h"
    labels.loc[(values >= THIRTEEN_HOURS) & (values <= TWENTY_FOUR_HOURS)] = "13-24h"
    labels.loc[values >= TWENTY_FIVE_HOURS] = "25h+"
    labels = labels.fillna("INVALID")
    if (labels == "INVALID").any():
        raise SignalDiagnosticError("bars_held must fit a known positive holding-time bucket")
    return labels.astype(str)


def _profit_factor(gross_profit: float, gross_loss: float) -> float:
    if gross_loss > 0.0:
        return gross_profit / gross_loss
    if gross_profit > 0.0:
        return math.inf
    return math.nan


def _outcome_rate(trades: pd.DataFrame, outcome: str) -> float:
    return float((trades["outcome"] == outcome).mean())


def _find_bucket(records: list[dict[str, Any]], bucket: str) -> dict[str, Any] | None:
    for record in records:
        if record["bucket"] == bucket:
            return record
    return None


def _validated_enum(value: Any, allowed: frozenset[str], field: str) -> str:
    if value is None:
        raise SignalDiagnosticError(f"trade missing required field: {field}")
    text = _enum_value(value)
    if text not in allowed:
        raise SignalDiagnosticError(f"{field} must be one of {sorted(allowed)}")
    return text


def _enum_value(value: Any) -> str:
    text = str(value)
    return text.rsplit(".", maxsplit=1)[-1].strip().upper()


def _float_field(payload: dict[str, Any], field: str) -> float:
    if field not in payload:
        raise SignalDiagnosticError(f"trade missing required field: {field}")
    value = payload[field]
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise SignalDiagnosticError(f"{field} must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise SignalDiagnosticError(f"{field} must be finite")
    return numeric


def _int_field(payload: dict[str, Any], field: str) -> int:
    if field not in payload:
        raise SignalDiagnosticError(f"trade missing required field: {field}")
    value = payload[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise SignalDiagnosticError(f"{field} must be an integer")
    return int(value)


def _positive_int_field(payload: dict[str, Any], field: str) -> int:
    value = _int_field(payload, field)
    if value <= 0:
        raise SignalDiagnosticError(f"{field} must be positive")
    return value


__all__ = [
    "SignalDiagnosticError",
    "build_signal_diagnostic_summary",
    "diagnostic_csv_rows",
    "flatten_canonical_trades",
]
