from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research import (  # noqa: I001
    BinanceDataFamily,
    HistoricalDatasetError,
    build_archive_plan,
    expected_hourly_bars,
    normalize_archive_plan,
    normalize_symbol_archive_files,
    parse_checksum_text,
    verify_checksum_file,
)
from src.research.pair_selection import CorrelationMode, PairSelectionConfig, select_pairs


KLINE_HEADER = (
    "open_time,open,high,low,close,volume,close_time,quote_volume,count,"
    "taker_buy_volume,taker_buy_quote_volume,ignore\n"
)


def test_build_archive_plan_uses_binance_public_data_paths() -> None:
    plan = build_archive_plan(
        ["btcusdt"],
        start_month="2023-06",
        end_month_exclusive="2023-08",
        families=(BinanceDataFamily.KLINES, BinanceDataFamily.FUNDING_RATE),
    )

    assert len(plan) == 4
    assert plan[0].symbol == "BTCUSDT"
    assert plan[0].url.endswith(
        "/data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2023-06.zip"
    )
    assert plan[1].url.endswith(
        "/data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2023-06.zip"
    )
    assert plan[0].checksum_url.endswith(".zip.CHECKSUM")
    assert expected_hourly_bars("2023-06", "2023-08") == 1464


def test_build_archive_plan_uses_binance_book_ticker_path() -> None:
    plan = build_archive_plan(
        ["btcusdt"],
        start_month="2023-06",
        end_month_exclusive="2023-07",
        families=(BinanceDataFamily.BOOK_TICKER,),
    )

    assert len(plan) == 1
    assert plan[0].filename == "BTCUSDT-bookTicker-2023-06.zip"
    assert plan[0].url.endswith(
        "/data/futures/um/monthly/bookTicker/BTCUSDT/BTCUSDT-bookTicker-2023-06.zip"
    )
    assert plan[0].checksum_url.endswith(
        "BTCUSDT-bookTicker-2023-06.zip.CHECKSUM"
    )


def test_checksum_parser_and_verifier_require_exact_sha256(tmp_path: Path) -> None:
    archive = tmp_path / "BTCUSDT-1h-2023-06.zip"
    archive.write_bytes(b"archive bytes")
    digest = hashlib.sha256(b"archive bytes").hexdigest()
    checksum = tmp_path / "BTCUSDT-1h-2023-06.zip.CHECKSUM"
    checksum.write_text(f"{digest}  BTCUSDT-1h-2023-06.zip\n", encoding="utf-8")

    parsed = parse_checksum_text(checksum.read_text(encoding="utf-8"))
    verified = verify_checksum_file(archive, checksum)

    assert parsed == (digest, "BTCUSDT-1h-2023-06.zip")
    assert verified.passed is True
    assert verified.expected_sha256 == digest


def test_checksum_parser_accepts_sha256sum_binary_filename_marker() -> None:
    digest = "a" * 64

    parsed = parse_checksum_text(f"{digest} *BTCUSDT-1h-2023-06.zip\n")

    assert parsed == (digest, "BTCUSDT-1h-2023-06.zip")


def test_normalize_symbol_archives_merges_sidecars_and_funding_without_future_data(
    tmp_path: Path,
) -> None:
    archives = _build_symbol_archives(tmp_path)

    bars = normalize_symbol_archive_files(
        "BTCUSDT",
        archives,
        dataset_version="unit-test",
    )

    assert list(bars["open_time"]) == [0, 3_600_000, 10_800_000]
    assert bars.loc[0, "price_for_research"] == pytest.approx(101.0)
    assert bars.loc[1, "price_for_research"] == pytest.approx(103.0)
    assert "PRICE_FALLBACK_CLOSE" in bars.loc[1, "quality_flags"]
    assert bars.loc[0, "funding_rate_asof"] == pytest.approx(0.0001)
    assert bars.loc[1, "funding_rate_asof"] == pytest.approx(0.0001)
    assert bars.loc[2, "funding_rate_asof"] == pytest.approx(0.0002)
    assert np.isnan(bars.loc[0, "return_1h"])
    assert bars.loc[1, "return_1h"] == pytest.approx(np.log(103.0) - np.log(101.0))
    assert np.isnan(bars.loc[2, "return_1h"])
    assert {
        "mark_close",
        "index_close",
        "premium_close",
        "funding_rate_asof",
        "execution_cost_quality",
    }.issubset(bars.columns)
    assert bars["execution_cost_quality"].unique().tolist() == ["UNAVAILABLE"]


def test_no_header_public_data_zip_preserves_first_data_row(tmp_path: Path) -> None:
    kline = tmp_path / "BTCUSDT-1h-2023-06.zip"
    _write_zip(
        kline,
        "BTCUSDT-1h-2023-06.csv",
        "0,100,105,95,100,10,3599999,1000,10,5,500,0\n"
        + "3600000,102,104,101,103,11,7199999,1100,11,6,600,0\n",
    )

    bars = normalize_symbol_archive_files(
        "BTCUSDT",
        {BinanceDataFamily.KLINES: [kline]},
        dataset_version="unit-test",
    )

    assert list(bars["open_time"]) == [0, 3_600_000]
    assert list(bars["close"]) == [100, 103]


def test_normalize_archive_plan_verifies_checksums_and_feeds_pair_selection(
    tmp_path: Path,
) -> None:
    root = tmp_path / "binance_public"
    specs = build_archive_plan(
        ["BTCUSDT", "ETHUSDT"],
        start_month="2023-06",
        end_month_exclusive="2023-07",
        families=(BinanceDataFamily.KLINES, BinanceDataFamily.FUNDING_RATE),
    )
    for spec in specs:
        archive_path = spec.archive_path(root)
        if spec.family is BinanceDataFamily.KLINES:
            rows = _correlated_kline_rows(spec.symbol)
            _write_zip(archive_path, spec.filename.removesuffix(".zip") + ".csv", KLINE_HEADER + rows)
        else:
            _write_zip(
                archive_path,
                spec.filename.removesuffix(".zip") + ".csv",
                "calc_time,funding_interval_hours,last_funding_rate\n0,8,0.0001\n",
            )
        _write_checksum(archive_path, spec.checksum_path(root))

    bars = normalize_archive_plan(specs, root, dataset_version="unit-test")
    result = select_pairs(
        bars,
        PairSelectionConfig(
            expected_bars=3,
            min_history_bars=3,
            min_history_coverage=1.0,
            min_pair_joint_coverage=1.0,
            min_funding_coverage=1.0,
            min_reference_price_coverage=0.0,
            min_median_quote_volume=0.0,
            min_p10_quote_volume=0.0,
            min_median_trades=0.0,
            min_correlation=0.5,
            correlation_window=2,
            min_correlation_observations=2,
            correlation_mode=CorrelationMode.FULL_SAMPLE_EXPLORATORY,
        ),
    )

    assert sorted(bars["symbol"].unique()) == ["BTCUSDT", "ETHUSDT"]
    assert result.accepted_symbol_names == ("BTCUSDT", "ETHUSDT")
    assert [pair.pair_id for pair in result.candidate_pairs] == ["BTCUSDT/ETHUSDT"]


def test_normalize_archive_plan_rejects_checksum_mismatch_before_normalization(
    tmp_path: Path,
) -> None:
    root = tmp_path / "binance_public"
    spec = build_archive_plan(
        ["BTCUSDT"],
        start_month="2023-06",
        end_month_exclusive="2023-07",
        families=(BinanceDataFamily.KLINES,),
    )[0]
    archive_path = spec.archive_path(root)
    _write_zip(archive_path, "not-a-valid-kline.csv", "this,is,not,a,kline\n")
    spec.checksum_path(root).parent.mkdir(parents=True, exist_ok=True)
    spec.checksum_path(root).write_text(f"{'0' * 64}  {archive_path.name}\n", encoding="utf-8")

    with pytest.raises(HistoricalDatasetError, match="checksum mismatch"):
        normalize_archive_plan((spec,), root, dataset_version="unit-test")


def test_runner_script_executes_local_no_download_smoke(tmp_path: Path) -> None:
    root = tmp_path / "binance_public"
    specs = build_archive_plan(
        ["BTCUSDT", "ETHUSDT"],
        start_month="2023-06",
        end_month_exclusive="2023-07",
    )
    for spec in specs:
        archive_path = spec.archive_path(root)
        csv_name = spec.filename.removesuffix(".zip") + ".csv"
        if spec.family is BinanceDataFamily.FUNDING_RATE:
            _write_zip(
                archive_path,
                csv_name,
                "calc_time,funding_interval_hours,last_funding_rate\n0,8,0.0001\n",
            )
        else:
            _write_zip(archive_path, csv_name, KLINE_HEADER + _correlated_kline_rows(spec.symbol))
        _write_checksum(archive_path, spec.checksum_path(root))

    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_sprint7_historical_dataset.py"),
            "--no-download",
            "--data-root",
            str(root),
            "--symbols",
            "BTCUSDT",
            "ETHUSDT",
            "--start-month",
            "2023-06",
            "--end-month-exclusive",
            "2023-07",
            "--dataset-version",
            "unit_smoke",
            "--correlation-window",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(completed.stdout)
    summary_path = root / "normalized" / "unit_smoke_summary.json"
    bars_path = root / "normalized" / "unit_smoke_bars.csv"

    assert summary_path.exists()
    assert bars_path.exists()
    assert summary["dataset_version"] == "unit_smoke"
    assert summary["normalized_path"] == str(bars_path)
    assert summary["gate_note"].startswith("Statistical-only run")


def test_research_gate_script_executes_on_normalized_bars(tmp_path: Path) -> None:
    bars_path = tmp_path / "bars.csv"
    summary_path = tmp_path / "summary.json"
    output_json = tmp_path / "research_gate.json"
    output_csv = tmp_path / "research_gate.csv"

    rows = ["symbol,open_time,log_price\n"]
    for index in range(600):
        open_time = index * 3_600_000
        log_eth = 4.0 + 0.0001 * index + 0.01 * np.sin(index / 17.0)
        spread = 0.02 * np.sin(index / 5.0)
        log_btc = log_eth + spread
        rows.append(f"BTCUSDT,{open_time},{log_btc:.12f}\n")
        rows.append(f"ETHUSDT,{open_time},{log_eth:.12f}\n")
    bars_path.write_text("".join(rows), encoding="utf-8")
    summary_path.write_text(
        json.dumps(
            {
                "dataset_version": "unit_gate",
                "candidate_pairs": [
                    {
                        "pair": "BTCUSDT/ETHUSDT",
                        "score": 0.8,
                        "correlation": 0.8,
                        "funding_carry_bps_per_day": 1.2,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_sprint7_research_gate.py"),
            "--bars-csv",
            str(bars_path),
            "--summary-json",
            str(summary_path),
            "--output-json",
            str(output_json),
            "--output-csv",
            str(output_csv),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    stdout_payload = json.loads(completed.stdout)
    file_payload = json.loads(output_json.read_text(encoding="utf-8"))

    assert stdout_payload["candidate_pairs_evaluated"] == 1
    assert file_payload["dataset_version"] == "unit_gate"
    assert file_payload["candidate_pairs_evaluated"] == 1
    assert file_payload["statistical_pairs_accepted"] + file_payload["statistical_pairs_rejected"] == 1
    assert file_payload["cost_gated_pass"] is False
    assert "top-of-book/L2" in file_payload["cost_gate_reason"]
    assert output_csv.read_text(encoding="utf-8").count("\n") == 2


def test_disagreeing_duplicate_open_time_fails_closed(tmp_path: Path) -> None:
    bad_kline = tmp_path / "bad.zip"
    _write_zip(
        bad_kline,
        "bad.csv",
        KLINE_HEADER
        + "0,100,101,99,100,1,3599999,1000,10,0.5,500,0\n"
        + "0,100,102,99,100,1,3599999,1000,10,0.5,500,0\n",
    )

    with pytest.raises(HistoricalDatasetError, match="duplicate"):
        normalize_symbol_archive_files(
            "BTCUSDT",
            {BinanceDataFamily.KLINES: [bad_kline]},
            dataset_version="unit-test",
        )


def _build_symbol_archives(tmp_path: Path) -> dict[BinanceDataFamily, list[Path]]:
    kline = tmp_path / "BTCUSDT-1h-2023-06.zip"
    mark = tmp_path / "BTCUSDT-mark-1h-2023-06.zip"
    index = tmp_path / "BTCUSDT-index-1h-2023-06.zip"
    premium = tmp_path / "BTCUSDT-premium-1h-2023-06.zip"
    funding = tmp_path / "BTCUSDT-fundingRate-2023-06.zip"

    _write_zip(
        kline,
        "BTCUSDT-1h-2023-06.csv",
        KLINE_HEADER
        + "0,100,105,95,100,10,3599999,1000,10,5,500,0\n"
        + "3600000,102,104,101,103,11,7199999,1100,11,6,600,0\n"
        + "10800000,104,107,103,106,12,14399999,1200,12,7,700,0\n",
    )
    _write_zip(
        mark,
        "BTCUSDT-1h-2023-06.csv",
        KLINE_HEADER
        + "0,101,102,100,101,0,3599999,0,3600,0,0,0\n"
        + "3600000,,,,,0,7199999,0,3600,0,0,0\n"
        + "10800000,106,107,105,106,0,14399999,0,3600,0,0,0\n",
    )
    _write_zip(
        index,
        "BTCUSDT-1h-2023-06.csv",
        KLINE_HEADER
        + "0,100,101,99,100,0,3599999,0,3600,0,0,0\n"
        + "3600000,103,104,102,103,0,7199999,0,3600,0,0,0\n"
        + "10800000,106,107,105,106,0,14399999,0,3600,0,0,0\n",
    )
    _write_zip(
        premium,
        "BTCUSDT-1h-2023-06.csv",
        KLINE_HEADER
        + "0,-0.2,0.2,-0.3,-0.1,0,3599999,0,3600,0,0,0\n"
        + "3600000,-0.2,0.2,-0.3,-0.1,0,7199999,0,3600,0,0,0\n"
        + "10800000,-0.2,0.2,-0.3,-0.1,0,14399999,0,3600,0,0,0\n",
    )
    _write_zip(
        funding,
        "BTCUSDT-fundingRate-2023-06.csv",
        "calc_time,funding_interval_hours,last_funding_rate\n"
        + "0,8,0.0001\n"
        + "7200000,8,0.0002\n",
    )
    return {
        BinanceDataFamily.KLINES: [kline],
        BinanceDataFamily.MARK_PRICE_KLINES: [mark],
        BinanceDataFamily.INDEX_PRICE_KLINES: [index],
        BinanceDataFamily.PREMIUM_INDEX_KLINES: [premium],
        BinanceDataFamily.FUNDING_RATE: [funding],
    }


def _correlated_kline_rows(symbol: str) -> str:
    closes = (100.0, 101.0, 102.0) if symbol == "BTCUSDT" else (200.0, 202.0, 204.0)
    rows = []
    for index, close in enumerate(closes):
        open_time = index * 3_600_000
        rows.append(
            f"{open_time},{close},{close + 1},{close - 1},{close},100,"
            f"{open_time + 3_599_999},1000000,100,50,500000,0"
        )
    return "\n".join(rows) + "\n"


def _write_checksum(archive_path: Path, checksum_path: Path) -> None:
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    checksum_path.parent.mkdir(parents=True, exist_ok=True)
    checksum_path.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")


def _write_zip(path: Path, csv_name: str, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(csv_name, content)
