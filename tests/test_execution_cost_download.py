from __future__ import annotations

import hashlib
import importlib.util
import io
import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.historical_dataset import HistoricalDatasetError  # noqa: E402

_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_sprint7_execution_cost_download.py"
_SPEC = importlib.util.spec_from_file_location("run_sprint7_execution_cost_download", _SCRIPT_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)

BOOK_TICKER_ROWS = (
    "1,100.00,1.0,100.02,1.0,1000,1000\n"
    "2,100.01,1.0,100.03,1.0,2000,2000\n"
    "3,100.00,1.0,100.05,1.0,3600001,3600001\n"
)


def _zip_bytes(csv_text: str, csv_name: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(csv_name, csv_text)
    return buffer.getvalue()


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def test_process_one_symbol_day_never_calls_real_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_bytes = _zip_bytes(BOOK_TICKER_ROWS, "ETCUSDT-bookTicker-2023-06-01.csv")
    digest = hashlib.sha256(archive_bytes).hexdigest()
    checksum_text = f"{digest}  ETCUSDT-bookTicker-2023-06-01.zip\n".encode()

    def fake_urlopen(url: str, timeout: float) -> _FakeResponse:  # noqa: ARG001
        if url.endswith(".CHECKSUM"):
            return _FakeResponse(checksum_text)
        return _FakeResponse(archive_bytes)

    monkeypatch.setattr(_MODULE, "urlopen", fake_urlopen)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("real network access forbidden")),
    )

    hourly = _MODULE._process_one_symbol_day(
        "ETCUSDT",
        __import__("datetime").date(2023, 6, 1),
        data_root=tmp_path,
        dataset_version="unit-test",
        overwrite=False,
        timeout_seconds=5.0,
        stale_gap_threshold_ms=60_000,
    )

    assert list(hourly["symbol"]) == ["ETCUSDT", "ETCUSDT"]
    assert hourly.loc[0, "spread_sample_count_1h"] == 2
    assert hourly.loc[1, "spread_sample_count_1h"] == 1
    assert (tmp_path / "data/futures/um/daily/bookTicker/ETCUSDT" / "ETCUSDT-bookTicker-2023-06-01.zip").exists()


def test_process_one_symbol_day_fails_closed_on_checksum_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_bytes = _zip_bytes(BOOK_TICKER_ROWS, "ETCUSDT-bookTicker-2023-06-01.csv")

    def fake_urlopen(url: str, timeout: float) -> _FakeResponse:  # noqa: ARG001
        if url.endswith(".CHECKSUM"):
            return _FakeResponse(f"{'0' * 64}  ETCUSDT-bookTicker-2023-06-01.zip\n".encode())
        return _FakeResponse(archive_bytes)

    monkeypatch.setattr(_MODULE, "urlopen", fake_urlopen)

    with pytest.raises(HistoricalDatasetError, match="checksum mismatch"):
        _MODULE._process_one_symbol_day(
            "ETCUSDT",
            __import__("datetime").date(2023, 6, 1),
            data_root=tmp_path,
            dataset_version="unit-test",
            overwrite=False,
            timeout_seconds=5.0,
            stale_gap_threshold_ms=60_000,
        )


def test_day_range_is_half_open_and_ordered() -> None:
    days = _MODULE._day_range("2023-06", "2023-07")

    assert len(days) == 30
    assert days[0].isoformat() == "2023-06-01"
    assert days[-1].isoformat() == "2023-06-30"
