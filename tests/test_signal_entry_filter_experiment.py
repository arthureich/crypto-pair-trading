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

SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_signal_entry_filter_experiment.py"
SPEC = importlib.util.spec_from_file_location("run_signal_entry_filter_experiment", SCRIPT_PATH)
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


def test_build_variants_sweeps_the_pre_registered_half_life_grid() -> None:
    variants = MODULE.build_entry_filter_variants()

    grid = tuple(v.max_half_life_hours for v in variants)
    assert grid == MODULE.HALF_LIFE_GRID_HOURS
    # Only max_half_life_hours changes across variants; every other config field
    # stays at the canonical default.
    baseline = MODULE.StatisticalBacktestConfig()
    for variant in variants:
        assert variant.config.max_half_life_hours == variant.max_half_life_hours
        assert variant.config.entry_zscore == baseline.entry_zscore
        assert variant.config.zscore_window == baseline.zscore_window
        assert variant.config.ou_window == baseline.ou_window
        assert variant.config.max_vertical_bars == baseline.max_vertical_bars


def test_decision_stops_when_no_variant_meets_pre_registered_rule() -> None:
    variant_results = {
        "max_half_life_240h": {"portfolio_metrics": {"profit_factor": 0.78, "trade_count": 60000}},
        "max_half_life_12h": {"portfolio_metrics": {"profit_factor": 1.05, "trade_count": 500}},
    }

    decision = MODULE.apply_pre_registered_decision(variant_results)

    assert decision["decision"] == "STOP_SIGNAL_ITERATION"
    assert decision["passing_variants"] == []


def test_decision_continues_only_when_pf_and_trade_count_both_clear() -> None:
    variant_results = {
        # PF clears but trade_count too low -> does not pass.
        "max_half_life_12h": {"portfolio_metrics": {"profit_factor": 1.5, "trade_count": 100}},
        # both clear -> passes.
        "max_half_life_24h": {"portfolio_metrics": {"profit_factor": 1.2, "trade_count": 300}},
    }

    decision = MODULE.apply_pre_registered_decision(variant_results)

    assert decision["decision"] == "CONTINUE_SIGNAL_ITERATION"
    assert decision["passing_variants"] == ["max_half_life_24h"]


def test_decision_treats_nan_profit_factor_as_failing() -> None:
    variant_results = {
        "max_half_life_12h": {"portfolio_metrics": {"profit_factor": float("nan"), "trade_count": 5000}},
    }

    decision = MODULE.apply_pre_registered_decision(variant_results)

    assert decision["decision"] == "STOP_SIGNAL_ITERATION"


def test_run_entry_filter_experiment_reruns_backtest_per_variant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_configs = []

    def fake_run_pair_statistical_backtest(bars, pair, *, funding_carry_bps_per_day, config):  # noqa: ARG001
        seen_configs.append(config.max_half_life_hours)
        return (_trade(pair, 5.0),)

    monkeypatch.setattr(MODULE, "run_pair_statistical_backtest", fake_run_pair_statistical_backtest)

    bars = pd.DataFrame({"symbol": ["AAA"], "open_time": [0], "log_price": [0.0]})
    variants = MODULE.build_entry_filter_variants()
    experiment = MODULE.run_entry_filter_experiment(
        bars=bars,
        funding_by_pair={"AAA/BBB": 1.0},
        variants=variants,
    )

    # Every variant's own half-life gate reached the backtest -- the experiment
    # reruns the backtest per variant, never filters a prior result.
    assert set(seen_configs) == set(MODULE.HALF_LIFE_GRID_HOURS)
    assert set(experiment["variants"]) == {v.name for v in variants}
    assert "decision" in experiment
    assert "binding" in experiment


def test_variant_name_is_unique_for_fractional_hours() -> None:
    # int() truncation would collide 0.75h and 0.375h onto the same "0h" name.
    names = {MODULE._variant_name(hours) for hours in (12.0, 6.0, 3.0, 1.5, 0.75, 0.375)}
    assert len(names) == 6


def test_binding_check_flags_non_binding_grid_when_trade_count_barely_moves() -> None:
    variant_results = {
        "max_half_life_240h": {
            "max_half_life_hours": 240.0,
            "portfolio_metrics": {"trade_count": 62878},
        },
        "max_half_life_12h": {
            "max_half_life_hours": 12.0,
            "portfolio_metrics": {"trade_count": 62838},
        },
    }

    binding = MODULE.binding_check(variant_results)

    assert binding["is_binding"] is False
    assert binding["max_excluded_fraction"] < MODULE.MIN_BINDING_EXCLUSION_FRACTION


def test_binding_check_flags_binding_grid_when_trade_count_drops_materially() -> None:
    variant_results = {
        "max_half_life_240h": {
            "max_half_life_hours": 240.0,
            "portfolio_metrics": {"trade_count": 62878},
        },
        "max_half_life_0p375h": {
            "max_half_life_hours": 0.375,
            "portfolio_metrics": {"trade_count": 1000},
        },
    }

    binding = MODULE.binding_check(variant_results)

    assert binding["is_binding"] is True


def test_decision_interpretation_flags_non_binding_grid_instead_of_overreaching() -> None:
    variant_results = {
        "max_half_life_240h": {"portfolio_metrics": {"profit_factor": 0.78, "trade_count": 62878}},
        "max_half_life_12h": {"portfolio_metrics": {"profit_factor": 0.78, "trade_count": 62838}},
    }
    non_binding = MODULE.binding_check(
        {
            "max_half_life_240h": {
                "max_half_life_hours": 240.0,
                "portfolio_metrics": {"trade_count": 62878},
            },
            "max_half_life_12h": {
                "max_half_life_hours": 12.0,
                "portfolio_metrics": {"trade_count": 62838},
            },
        }
    )

    decision = MODULE.apply_pre_registered_decision(variant_results, binding=non_binding)

    assert decision["decision"] == "STOP_SIGNAL_ITERATION"
    assert "NON-BINDING" in decision["interpretation"]


def test_parse_grid_requires_the_canonical_baseline() -> None:
    with pytest.raises(ValueError, match="240"):
        MODULE._parse_grid("12,6,3")

    assert MODULE._parse_grid("240,12,6") == (240.0, 12.0, 6.0)


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
            "run_signal_entry_filter_experiment.py",
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
        "run_entry_filter_experiment",
        lambda *, bars, funding_by_pair, variants: {
            "variants": {
                MODULE._variant_name(MODULE.BASELINE_HALF_LIFE_HOURS): {
                    "portfolio_metrics": {},
                    "approved_pair_count": 0,
                },
            },
            "decision": {},
        },
    )
    monkeypatch.setattr(
        MODULE,
        "baseline_reproduction_check",
        lambda baseline_result, canonical_payload: {
            "pass": False,
            "metric_deltas": {"net_pnl_bps": 1.0},
            "approved_pair_count_delta": 3,
        },
    )

    exit_code = MODULE.main()

    assert exit_code == MODULE.BASELINE_REPRODUCTION_EXIT_CODE
    assert not output_json.exists()
    assert not output_csv.exists()
    assert not report_md.exists()


def test_load_pairs_and_funding_rejects_wrong_pair_count(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {"accepted_pairs": [{"pair": "AAA/BBB", "statistical_status": "ACCEPT", "funding_carry_bps_per_day": 1.0}]}
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="41"):
        MODULE.load_pairs_and_funding(gate)
