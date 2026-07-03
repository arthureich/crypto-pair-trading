#!/usr/bin/env python3
"""Post-process canonical Sprint 8 trades to diagnose gross signal edge."""

from __future__ import annotations

import argparse
import json
import math
import numbers
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.signal_diagnostics import (  # noqa: E402
    build_signal_diagnostic_summary,
    diagnostic_csv_rows,
)

DEFAULT_INPUT_JSON = (
    PROJECT_ROOT
    / "data/research/binance_public/cost_pilot/sprint8_canonical_backtest_results.json"
)
DEFAULT_OUTPUT_JSON = (
    PROJECT_ROOT
    / "data/research/binance_public/cost_pilot/signal_diagnostics_sprint8_canonical.json"
)
DEFAULT_OUTPUT_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/cost_pilot/signal_diagnostics_sprint8_canonical.csv"
)
DEFAULT_REPORT_MD = PROJECT_ROOT / "reports/signal_diagnostics.md"


def main() -> int:
    args = _parse_args()
    payload = json.loads(args.input_json.read_text(encoding="utf-8"))
    summary = build_signal_diagnostic_summary(payload)
    report_payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "input_json": str(args.input_json),
        **summary,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_json_ready(report_payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(diagnostic_csv_rows(summary)).to_csv(args.output_csv, index=False)
    args.report_md.write_text(_markdown_report(report_payload), encoding="utf-8")

    print(json.dumps(_json_ready(report_payload["overall"]), allow_nan=False, indent=2))
    print(f"Wrote {args.output_json}")
    print(f"Wrote {args.output_csv}")
    print(f"Wrote {args.report_md}")
    return 0


def _markdown_report(payload: dict[str, Any]) -> str:
    diagnosis = payload["diagnosis"]
    lines = [
        "# Signal Diagnostics - Gross Edge",
        "",
        f"Data: {payload['generated_at_utc']}",
        "",
        "## Objetivo",
        "",
        "Diagnosticar os trades ja calculados no Sprint 8 canonico para entender "
        "onde existe, ou nao existe, edge bruto antes de custo. Este relatorio nao "
        "muda parametros, nao reroda backtest e nao abre Sprint 10.",
        "",
        "## Fonte",
        "",
        f"- Input: `{payload['input_json']}`",
        f"- Trades resolvidos analisados: {payload['trade_count']}",
        f"- Pares analisados: {payload['pair_count']}",
        "",
        "## Resultado Agregado",
        "",
        _table(
            ["Metrica", "Valor"],
            [
                ["Gross PnL total (bps)", _fmt(payload["overall"]["gross_pnl_bps"])],
                ["Gross PnL medio/trade (bps)", _fmt(payload["overall"]["avg_gross_pnl_bps"])],
                ["Gross profit factor", _fmt(payload["overall"]["gross_profit_factor"])],
                ["Net PnL total (bps)", _fmt(payload["overall"]["net_pnl_bps"])],
                ["Custo medio/trade (bps)", _fmt(payload["overall"]["avg_cost_bps"])],
                ["Hit rate bruto", _pct(payload["overall"]["hit_rate_gross"])],
                ["Bars held medio", _fmt(payload["overall"]["avg_bars_held"])],
            ],
        ),
        "",
        "## Outcomes",
        "",
        _records_table(payload["outcome_distribution"]),
        "",
        "## Edge Bruto Por |entry_zscore|",
        "",
        _records_table(payload["entry_zscore_buckets"]),
        "",
        "## Edge Bruto Por Tempo Em Trade",
        "",
        _records_table(payload["bars_held_buckets"]),
        "",
        "## Lado Do Spread",
        "",
        _records_table(payload["side_summary"]),
        "",
        "## Top 10 Pares Por Gross Medio",
        "",
        _records_table(payload["top_gross_pairs"]),
        "",
        "## Bottom 10 Pares Por Gross Medio",
        "",
        _records_table(payload["bottom_gross_pairs"]),
        "",
        "## Diagnostico",
        "",
        *[f"- {note}" for note in diagnosis["notes"]],
        "",
        "## Proxima Tarefa Recomendada",
        "",
        *[f"- {item}" for item in diagnosis["recommendations"]],
        "",
        "## Limites",
        "",
        "- Trades podem estar sobrepostos no tempo, como documentado no backtest canonico.",
        "- Custo aqui so contextualiza o net PnL ja calculado; a decisao desta tarefa olha "
        "principalmente para gross PnL.",
        "- Este diagnostico nao valida paper/live trading e nao altera Execution/Risk/Ledger.",
        "",
    ]
    return "\n".join(lines)


def _records_table(records: list[dict[str, Any]]) -> str:
    headers = [
        "Bucket",
        "Trades",
        "Gross/trade",
        "Gross PF",
        "PROFIT%",
        "STOP%",
        "VERTICAL%",
        "Avg |z|",
        "Avg hold",
    ]
    rows = [
        [
            record["bucket"],
            str(record["trade_count"]),
            _fmt(record["avg_gross_pnl_bps"]),
            _fmt(record["gross_profit_factor"]),
            _pct(record["profit_outcome_rate"]),
            _pct(record["stop_outcome_rate"]),
            _pct(record["vertical_outcome_rate"]),
            _fmt(record["avg_abs_entry_zscore"]),
            _fmt(record["avg_bars_held"]),
        ]
        for record in records
    ]
    return _table(headers, rows)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    numeric = float(value)
    if math.isnan(numeric):
        return "NA"
    if math.isinf(numeric):
        return "+inf" if numeric > 0.0 else "-inf"
    return f"{numeric:.4f}"


def _pct(value: Any) -> str:
    if value is None:
        return "NA"
    numeric = float(value)
    if not math.isfinite(numeric):
        return "NA"
    return f"{numeric * 100.0:.2f}%"


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
    parser.add_argument("--input-json", type=Path, default=DEFAULT_INPUT_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
