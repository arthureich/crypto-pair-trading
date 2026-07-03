from __future__ import annotations

import importlib.util
import json
import math
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

SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_signal_intrahour_sanity_check.py"
SPEC = importlib.util.spec_from_file_location("run_signal_intrahour_sanity_check", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _trade(net_pnl_bps: float, gross_pnl_bps: float, *, entry_time: int = 0) -> StatisticalTradeResult:
    return StatisticalTradeResult(
        pair="AAA/BBB",
        status=TradeStatus.RESOLVED,
        side=BarrierSide.SHORT_SPREAD,
        entry_time=entry_time,
        entry_zscore=2.5,
        exit_time=entry_time + 1,
        outcome=BarrierOutcome.PROFIT if net_pnl_bps > 0.0 else BarrierOutcome.STOP,
        bars_held=1,
        gross_pnl_bps=gross_pnl_bps,
        cost_bps=gross_pnl_bps - net_pnl_bps,
        net_pnl_bps=net_pnl_bps,
    )


def test_load_funding_by_pair_returns_only_requested_pairs(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "accepted_pairs": [
                    {"pair": "AAA/BBB", "funding_carry_bps_per_day": 1.0},
                    {"pair": "CCC/DDD", "funding_carry_bps_per_day": 2.0},
                ]
            }
        ),
        encoding="utf-8",
    )

    result = MODULE.load_funding_by_pair(gate, ("AAA/BBB",))

    assert result == {"AAA/BBB": 1.0}


def test_load_funding_by_pair_fails_closed_on_missing_pair(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps({"accepted_pairs": [{"pair": "AAA/BBB", "funding_carry_bps_per_day": 1.0}]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="CCC/DDD"):
        MODULE.load_funding_by_pair(gate, ("AAA/BBB", "CCC/DDD"))


def test_run_sanity_check_scales_windows_for_5_minute_bars(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_configs = []

    def fake_run_pair_statistical_backtest(bars, pair, *, funding_carry_bps_per_day, config):  # noqa: ARG001
        seen_configs.append(config)
        return (_trade(5.0, 6.0),)

    monkeypatch.setattr(
        MODULE, "run_pair_statistical_backtest", fake_run_pair_statistical_backtest
    )

    bars = pd.DataFrame({"symbol": ["AAA"], "open_time": [0], "log_price": [0.0]})
    MODULE.run_sanity_check(bars, {"AAA/BBB": 1.0})

    # Two configs (baseline + tight) x 1 pair = 2 calls.
    assert len(seen_configs) == 2
    for config in seen_configs:
        # Same real trailing window (168h) as the Sprint 8 canonical config,
        # just expressed in 5-minute bars instead of 1-hour bars.
        assert config.zscore_window == 168 * 12
        assert config.ou_window == 168 * 12
        assert config.max_vertical_bars == 240 * 12
        assert config.bar_duration_hours == pytest.approx(1.0 / 12.0)
    baseline_config, tight_config = seen_configs
    assert baseline_config.max_half_life_hours != tight_config.max_half_life_hours
    assert tight_config.max_half_life_hours == pytest.approx(
        MODULE.REPLICATION_MAX_HALF_LIFE_HOURS
    )


def test_run_config_computes_gross_profit_factor_from_trade_level_gross_pnl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trades = (_trade(10.0, 12.0), _trade(-5.0, -3.0))

    def fake_run_pair_statistical_backtest(*args, **kwargs):  # noqa: ARG001
        return trades

    monkeypatch.setattr(
        MODULE, "run_pair_statistical_backtest", fake_run_pair_statistical_backtest
    )

    bars = pd.DataFrame({"symbol": ["AAA"], "open_time": [0], "log_price": [0.0]})
    result = MODULE._run_config(
        bars, {"AAA/BBB": 1.0}, MODULE.StatisticalBacktestConfig(), "test"
    )

    # gross wins = 12.0, gross losses = 3.0 -> gross PF = 4.0.
    assert result["gross_profit_factor"] == pytest.approx(4.0)


def test_run_config_reports_nan_gross_profit_factor_when_no_trades(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        MODULE, "run_pair_statistical_backtest", lambda *a, **k: ()  # noqa: ARG005
    )

    bars = pd.DataFrame({"symbol": ["AAA"], "open_time": [0], "log_price": [0.0]})
    result = MODULE._run_config(
        bars, {"AAA/BBB": 1.0}, MODULE.StatisticalBacktestConfig(), "test"
    )

    assert math.isnan(result["gross_profit_factor"])


def test_download_and_normalize_bars_requests_klines_only_at_given_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    def fake_build_archive_plan(symbols, *, start_month, end_month_exclusive, interval, families):
        captured["symbols"] = tuple(symbols)
        captured["interval"] = interval
        captured["families"] = tuple(families)
        return ("spec-1",)

    def fake_download_archives(specs, data_root, *, max_workers):  # noqa: ARG001
        captured["downloaded"] = True

    def fake_normalize_archive_plan(specs, data_root, *, dataset_version):  # noqa: ARG001
        return pd.DataFrame({"symbol": ["AAA"], "open_time": [0], "log_price": [0.0]})

    monkeypatch.setattr(MODULE, "build_archive_plan", fake_build_archive_plan)
    monkeypatch.setattr(MODULE, "download_archives", fake_download_archives)
    monkeypatch.setattr(MODULE, "normalize_archive_plan", fake_normalize_archive_plan)

    bars = MODULE.download_and_normalize_bars(
        symbols=("AAA", "BBB"),
        start_month="2025-12",
        end_month_exclusive="2026-06",
        interval="5m",
        dataset_version="test",
        data_root=Path("/tmp/does-not-matter"),
        download_workers=1,
        download=True,
    )

    assert captured["symbols"] == ("AAA", "BBB")
    assert captured["interval"] == "5m"
    assert captured["families"] == (MODULE.BinanceDataFamily.KLINES,)
    assert captured["downloaded"] is True
    assert not bars.empty


def test_download_and_normalize_bars_skips_download_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"download": False}

    monkeypatch.setattr(
        MODULE,
        "build_archive_plan",
        lambda *a, **k: ("spec-1",),  # noqa: ARG005
    )

    def fake_download_archives(*args, **kwargs):  # noqa: ARG001
        called["download"] = True

    monkeypatch.setattr(MODULE, "download_archives", fake_download_archives)
    monkeypatch.setattr(
        MODULE,
        "normalize_archive_plan",
        lambda *a, **k: pd.DataFrame({"symbol": [], "open_time": [], "log_price": []}),  # noqa: ARG005
    )

    MODULE.download_and_normalize_bars(
        symbols=("AAA",),
        start_month="2025-12",
        end_month_exclusive="2026-06",
        interval="5m",
        dataset_version="test",
        data_root=Path("/tmp/does-not-matter"),
        download_workers=1,
        download=False,
    )

    assert called["download"] is False
