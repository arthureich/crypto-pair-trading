from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.signal_diagnostics import (  # noqa: E402
    SignalDiagnosticError,
    build_signal_diagnostic_summary,
    diagnostic_csv_rows,
    flatten_canonical_trades,
)


def _payload() -> dict:
    return {
        "per_pair": {
            "AAA/BBB": {
                "trades": [
                    _trade("PROFIT", 2.1, 1, 10.0, -2.0),
                    _trade("STOP", -2.7, 3, -20.0, -32.0),
                    _trade("VERTICAL", 3.2, 15, 5.0, -7.0),
                    {
                        **_trade("NO_DATA", 2.4, 0, 0.0, 0.0),
                        "status": "UNRESOLVED_NO_DATA",
                    },
                ]
            },
            "CCC/DDD": {
                "trades": [
                    {**_trade("PROFIT", -3.5, 26, 30.0, 18.0), "pair": "CCC/DDD"},
                    {**_trade("STOP", 2.2, 5, -15.0, -27.0), "pair": "CCC/DDD"},
                ]
            },
        }
    }


def _trade(
    outcome: str,
    entry_zscore: float,
    bars_held: int,
    gross_pnl_bps: float,
    net_pnl_bps: float,
) -> dict:
    return {
        "pair": "AAA/BBB",
        "status": "RESOLVED",
        "side": "SHORT_SPREAD" if entry_zscore > 0 else "LONG_SPREAD",
        "entry_time": 1,
        "entry_zscore": entry_zscore,
        "exit_time": 2,
        "outcome": outcome,
        "bars_held": bars_held,
        "gross_pnl_bps": gross_pnl_bps,
        "cost_bps": gross_pnl_bps - net_pnl_bps,
        "net_pnl_bps": net_pnl_bps,
    }


def test_flatten_canonical_trades_keeps_only_resolved_rows_and_adds_buckets() -> None:
    trades = flatten_canonical_trades(_payload())

    assert len(trades) == 5
    assert set(trades["entry_zscore_bucket"]) == {"2.0-2.5", "2.5-3.0", "3.0+"}
    assert set(trades["bars_held_bucket"]) == {"1h", "2-4h", "5-12h", "13-24h", "25h+"}
    assert "status" not in trades.columns


def test_build_signal_diagnostic_summary_reports_gross_edge_groups() -> None:
    summary = build_signal_diagnostic_summary(_payload())

    assert summary["trade_count"] == 5
    assert summary["pair_count"] == 2
    assert summary["overall"]["gross_pnl_bps"] == pytest.approx(10.0)
    assert summary["overall"]["avg_gross_pnl_bps"] == pytest.approx(2.0)
    assert summary["overall"]["gross_profit_factor"] == pytest.approx(45.0 / 35.0)

    by_outcome = {row["bucket"]: row for row in summary["outcome_distribution"]}
    assert by_outcome["PROFIT"]["trade_count"] == 2
    assert by_outcome["STOP"]["trade_count"] == 2
    assert by_outcome["VERTICAL"]["trade_count"] == 1

    by_z = {row["bucket"]: row for row in summary["entry_zscore_buckets"]}
    assert by_z["2.0-2.5"]["trade_count"] == 2
    assert by_z["2.5-3.0"]["trade_count"] == 1
    assert by_z["3.0+"]["trade_count"] == 2
    assert math.isfinite(by_z["3.0+"]["avg_gross_pnl_bps"])

    by_hold = {row["bucket"]: row for row in summary["bars_held_buckets"]}
    assert by_hold["25h+"]["trade_count"] == 1


def test_diagnostic_csv_rows_include_all_group_dimensions() -> None:
    summary = build_signal_diagnostic_summary(_payload())

    rows = diagnostic_csv_rows(summary)

    dimensions = {row["dimension"] for row in rows}
    assert {
        "outcome_distribution",
        "entry_zscore_buckets",
        "bars_held_buckets",
        "side_summary",
        "pair_summary",
    }.issubset(dimensions)


def test_build_signal_diagnostic_summary_reports_empty_required_buckets() -> None:
    payload = {
        "per_pair": {
            "AAA/BBB": {
                "trades": [
                    _trade("PROFIT", 2.1, 1, 10.0, -2.0),
                    _trade("STOP", -2.7, 3, -20.0, -32.0),
                ]
            }
        }
    }

    summary = build_signal_diagnostic_summary(payload)

    by_hold = {row["bucket"]: row for row in summary["bars_held_buckets"]}
    assert by_hold["5-12h"]["trade_count"] == 0
    assert by_hold["13-24h"]["trade_count"] == 0
    assert by_hold["25h+"]["trade_count"] == 0


def test_build_signal_diagnostic_summary_fails_when_no_resolved_trades_exist() -> None:
    payload = {
        "per_pair": {
            "AAA/BBB": {
                "trades": [
                    {
                        **_trade("NO_DATA", 2.1, 1, 0.0, 0.0),
                        "status": "UNRESOLVED_NO_DATA",
                    }
                ]
            }
        }
    }

    with pytest.raises(SignalDiagnosticError, match="no resolved trades"):
        build_signal_diagnostic_summary(payload)


def test_flatten_canonical_trades_rejects_missing_required_field() -> None:
    trade = _trade("PROFIT", 2.1, 1, 10.0, -2.0)
    trade.pop("entry_time")
    payload = {"per_pair": {"AAA/BBB": {"trades": [trade]}}}

    with pytest.raises(SignalDiagnosticError, match="entry_time"):
        flatten_canonical_trades(payload)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("status", None, "status"),
        ("status", "CORRUPT", "status"),
        ("side", "BAD_SIDE", "side"),
        ("outcome", "BAD_OUTCOME", "outcome"),
    ],
)
def test_flatten_canonical_trades_rejects_invalid_enums(
    field: str,
    value: str | None,
    match: str,
) -> None:
    trade = _trade("PROFIT", 2.1, 1, 10.0, -2.0)
    if value is None:
        trade.pop(field)
    else:
        trade[field] = value
    payload = {"per_pair": {"AAA/BBB": {"trades": [trade]}}}

    with pytest.raises(SignalDiagnosticError, match=match):
        flatten_canonical_trades(payload)


def test_flatten_canonical_trades_rejects_non_positive_bars_held() -> None:
    trade = _trade("PROFIT", 2.1, 0, 10.0, -2.0)
    payload = {"per_pair": {"AAA/BBB": {"trades": [trade]}}}

    with pytest.raises(SignalDiagnosticError, match="bars_held"):
        flatten_canonical_trades(payload)


def test_flatten_canonical_trades_rejects_entry_zscore_below_contract_threshold() -> None:
    trade = _trade("PROFIT", 1.9, 1, 10.0, -2.0)
    payload = {"per_pair": {"AAA/BBB": {"trades": [trade]}}}

    with pytest.raises(SignalDiagnosticError, match="entry_zscore"):
        flatten_canonical_trades(payload)


def test_flatten_canonical_trades_rejects_missing_per_pair_object() -> None:
    with pytest.raises(SignalDiagnosticError, match="per_pair"):
        flatten_canonical_trades({})
