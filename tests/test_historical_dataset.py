from __future__ import annotations

import hashlib
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
    normalize_symbol_archive_files,
    parse_checksum_text,
    verify_checksum_file,
)


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


def _write_zip(path: Path, csv_name: str, content: str) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(csv_name, content)
