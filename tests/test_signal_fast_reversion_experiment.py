from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest.statistical_backtest import (  # noqa: E402
    StatisticalTradeResult,
    TradeStatus,
)
from src.research.triple_barrier import BarrierOutcome, BarrierSide  # noqa: E402

SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_signal_fast_reversion_experiment.py"
SPEC = importlib.util.spec_from_file_location("run_signal_fast_reversion_experiment", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _trade(pair: str, net_pnl_bps: float, *, entry_time: int = 0) -> StatisticalTradeResult:
    return StatisticalTradeResult(
        pair=pair,
        status=TradeStatus.RESOLVED,
        side=BarrierSide.SHORT_SPREAD,
        entry_time=entry_time,
        entry_zscore=2.5,
        exit_time=entry_time + 1,
        outcome=BarrierOutcome.PROFIT if net_pnl_bps > 0.0 else BarrierOutcome.STOP,
        bars_held=1,
        gross_pnl_bps=net_pnl_bps + 1.0,
        cost_bps=1.0,
        net_pnl_bps=net_pnl_bps,
    )


def test_build_experiment_variants_changes_only_fast_vertical_cap() -> None:
    baseline, fast = MODULE.build_experiment_variants()

    assert baseline.name == MODULE.BASELINE_VARIANT
    assert fast.name == MODULE.FAST_VARIANT
    assert baseline.config.max_vertical_bars == 240
    assert fast.config.max_vertical_bars == 4
    assert baseline.config.entry_zscore == fast.config.entry_zscore
    assert baseline.config.zscore_window == fast.config.zscore_window
    assert baseline.config.ou_window == fast.config.ou_window


def test_run_signal_experiment_reruns_backtest_for_each_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_run_pair_statistical_backtest(
        bars: pd.DataFrame,
        pair: str,
        *,
        funding_carry_bps_per_day: float,
        config,
    ) -> tuple[StatisticalTradeResult, ...]:
        calls.append(
            {
                "pair": pair,
                "funding_carry_bps_per_day": funding_carry_bps_per_day,
                "max_vertical_bars": config.max_vertical_bars,
                "bars_rows": len(bars),
            }
        )
        pnl = 10.0 if config.max_vertical_bars == 4 else -5.0
        return (_trade(pair, pnl),)

    monkeypatch.setattr(
        MODULE,
        "run_pair_statistical_backtest",
        fake_run_pair_statistical_backtest,
    )
    bars = pd.DataFrame({"symbol": ["AAA"], "open_time": [0], "log_price": [0.0]})

    result = MODULE.run_signal_experiment(
        bars=bars,
        funding_by_pair={"AAA/BBB": 2.0},
        variants=MODULE.build_experiment_variants(),
    )

    assert [call["max_vertical_bars"] for call in calls] == [240, 4]
    assert all(call["pair"] == "AAA/BBB" for call in calls)
    assert result["variants"][MODULE.BASELINE_VARIANT]["portfolio_metrics"]["net_pnl_bps"] == -5.0
    assert result["variants"][MODULE.FAST_VARIANT]["portfolio_metrics"]["net_pnl_bps"] == 10.0
    assert result["comparison"]["candidate_for_next_iteration"] is True


def test_baseline_reproduction_check_passes_on_exact_metric_match() -> None:
    metrics = {
        "trade_count": 2,
        "gross_pnl_bps": 10.0,
        "cost_bps": 2.0,
        "net_pnl_bps": 8.0,
        "profit_factor": 1.5,
        "hit_rate": 0.5,
    }
    baseline = {"portfolio_metrics": metrics, "approved_pair_count": 0}
    canonical = {"portfolio_metrics": metrics, "approved_pair_count": 0}

    check = MODULE.baseline_reproduction_check(baseline, canonical)

    assert check["pass"] is True
    assert all(value == 0.0 for value in check["metric_deltas"].values())


def test_baseline_reproduction_check_fails_on_metric_drift() -> None:
    baseline = {
        "portfolio_metrics": {
            "trade_count": 2,
            "gross_pnl_bps": 11.0,
            "cost_bps": 2.0,
            "net_pnl_bps": 9.0,
            "profit_factor": 1.5,
            "hit_rate": 0.5,
        },
        "approved_pair_count": 0,
    }
    canonical = {
        "portfolio_metrics": {
            "trade_count": 2,
            "gross_pnl_bps": 10.0,
            "cost_bps": 2.0,
            "net_pnl_bps": 8.0,
            "profit_factor": 1.5,
            "hit_rate": 0.5,
        },
        "approved_pair_count": 0,
    }

    check = MODULE.baseline_reproduction_check(baseline, canonical)

    assert check["pass"] is False
    assert check["metric_deltas"]["gross_pnl_bps"] == 1.0


def test_compare_variant_results_rejects_when_net_does_not_improve() -> None:
    baseline = {
        "approved_pair_count": 0,
        "outcome_counts": {"profit_count": 6, "stop_count": 2, "vertical_count": 2},
        "portfolio_metrics": {
            "gross_pnl_bps": 10.0,
            "net_pnl_bps": 5.0,
            "profit_factor": 1.1,
            "trade_count": 10,
            "max_drawdown_bps": 3.0,
            "avg_bars_held": 5.0,
        },
    }
    fast = {
        "approved_pair_count": 0,
        "outcome_counts": {"profit_count": 4, "stop_count": 2, "vertical_count": 2},
        "portfolio_metrics": {
            "gross_pnl_bps": 12.0,
            "net_pnl_bps": 4.0,
            "profit_factor": 1.2,
            "trade_count": 8,
            "max_drawdown_bps": 4.0,
            "avg_bars_held": 3.0,
        },
    }

    comparison = MODULE.compare_variant_results(baseline, fast)

    assert comparison["candidate_for_next_iteration"] is False
    assert comparison["decision"] == "STOP_FAST_REVERSION_PATH"


def test_main_aborts_without_writing_outputs_when_baseline_reproduction_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "out.json"
    output_csv = tmp_path / "out.csv"
    report_md = tmp_path / "report.md"
    canonical_json = tmp_path / "canonical.json"
    canonical_json.write_text(json.dumps({}), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_signal_fast_reversion_experiment.py",
            "--canonical-json",
            str(canonical_json),
            "--output-json",
            str(output_json),
            "--output-csv",
            str(output_csv),
            "--report-md",
            str(report_md),
        ],
    )
    monkeypatch.setattr(
        MODULE.pd,
        "read_csv",
        lambda *args, **kwargs: pd.DataFrame(
            {"symbol": ["AAA"], "open_time": [0], "log_price": [0.0]}
        ),
    )
    monkeypatch.setattr(MODULE, "load_pairs_and_funding", lambda path: {"AAA/BBB": 0.0})
    monkeypatch.setattr(
        MODULE,
        "run_signal_experiment",
        lambda *, bars, funding_by_pair, variants: {
            "variants": {
                MODULE.BASELINE_VARIANT: {"portfolio_metrics": {}, "approved_pair_count": 0},
                MODULE.FAST_VARIANT: {"portfolio_metrics": {}, "approved_pair_count": 0},
            },
            "comparison": {},
        },
    )
    monkeypatch.setattr(
        MODULE,
        "baseline_reproduction_check",
        lambda baseline_result, canonical_payload: {
            "pass": False,
            "metric_deltas": {"net_pnl_bps": 1.0},
            "approved_pair_count_delta": 0,
        },
    )

    exit_code = MODULE.main()

    assert exit_code == MODULE.BASELINE_REPRODUCTION_EXIT_CODE
    assert not output_json.exists()
    assert not output_csv.exists()
    assert not report_md.exists()


def test_markdown_report_includes_drawdown_and_outcome_decomposition() -> None:
    payload = {
        "generated_at_utc": "2026-07-03T00:00:00+00:00",
        "experiment": {
            "baseline_reproduction": {
                "pass": True,
                "metric_deltas": {},
                "approved_pair_count_delta": 0,
            },
            "variants": {
                MODULE.BASELINE_VARIANT: _variant_payload(trades=10, vertical=4),
                MODULE.FAST_VARIANT: _variant_payload(trades=8, vertical=2),
            },
            "comparison": {
                "gross_pnl_bps_delta": 1.0,
                "net_pnl_bps_delta": 2.0,
                "profit_factor_delta": 0.1,
                "max_drawdown_bps_delta": -5.0,
                "avg_bars_held_delta": -1.0,
                "trade_count_delta": -2,
                "approved_pair_count_delta": 0,
                "outcome_count_deltas": {
                    "profit_count": -1,
                    "stop_count": -1,
                    "vertical_count": -2,
                },
                "decision": "CONTINUE_SIGNAL_ITERATION",
                "candidate_for_next_iteration": True,
                "interpretation": "ok",
            },
        },
    }

    report = MODULE._markdown_report(payload)

    assert "Drawdown" in report
    assert "## Decomposicao" in report
    assert "VERTICAL count" in report
    assert "Avg bars held" in report


def _variant_payload(*, trades: int, vertical: int) -> dict:
    return {
        "description": "test",
        "config": {},
        "approved_pair_count": 0,
        "approved_pairs": [],
        "portfolio_metrics": {
            "trade_count": trades,
            "gross_pnl_bps": 10.0,
            "net_pnl_bps": 5.0,
            "profit_factor": 1.1,
            "hit_rate": 0.5,
            "max_drawdown_bps": 20.0,
            "avg_bars_held": 3.0,
        },
        "outcome_counts": {
            "profit_count": 3,
            "stop_count": 2,
            "vertical_count": vertical,
        },
    }
