#!/usr/bin/env python3
"""Bounded intrahour sanity check (TASK-SIG-004).

Signal Iteration 1 is CLOSED as a rejected hypothesis (ADR-0010). This is a
single, deliberately small, non-repeating exploratory check: TASK-SIG-003's
tightest bucket (max_half_life_hours=0.375, ~22.5 minutes) showed gross
profit factor > 1.0 for the first time in the whole iteration, but on only
74 trades across 3 pairs -- too small to trust, and possibly an artifact of
hourly bars being unable to resolve reversions faster than the bar interval.

This script downloads real 5-minute klines (Binance USD-M futures public
data, checksum-verified) for the 8 symbols involved in the 9 pairs that had
ANY trade at that threshold in Sprint 8 canonical / SIG-003 Run 2 -- not the
41-pair/20-symbol universe -- over a 6-month window, and reruns the SAME
causal statistical-backtest pipeline at that granularity. This is NOT a new
pre-registered decision framework: it is a plain replication check.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest.statistical_backtest import (  # noqa: E402
    StatisticalBacktestConfig,
    TradeStatus,
    run_pair_statistical_backtest,
    summarize_statistical_backtest,
)
from src.research.historical_dataset import (  # noqa: E402
    BinanceDataFamily,
    build_archive_plan,
    download_archives,
    normalize_archive_plan,
)

# The 8 symbols underlying the 9 pairs that had ANY trade in the tightest
# (0.375h) bucket of TASK-SIG-003 Run 2 -- using all 9, not just the 3 that
# individually passed the per-pair gate, to avoid the exact survivorship bias
# TASK-SIG-002 found and corrected.
SYMBOLS = (
    "ADAUSDT",
    "ARBUSDT",
    "AVAXUSDT",
    "BTCUSDT",
    "DOGEUSDT",
    "DOTUSDT",
    "ETCUSDT",
    "ETHUSDT",
)
PAIRS = (
    "ADAUSDT/ETCUSDT",
    "ADAUSDT/ETHUSDT",
    "ARBUSDT/ETCUSDT",
    "ARBUSDT/ETHUSDT",
    "AVAXUSDT/ETHUSDT",
    "BTCUSDT/ETHUSDT",
    "DOGEUSDT/ETHUSDT",
    "DOTUSDT/ETHUSDT",
    "ETCUSDT/ETHUSDT",
)
DEFAULT_START_MONTH = "2025-12"
DEFAULT_END_MONTH_EXCLUSIVE = "2026-06"
DEFAULT_INTERVAL = "5m"
DEFAULT_DATASET_VERSION = "intrahour_sanity_5m_202512_202605"
BARS_PER_HOUR_AT_5M = 12
# Same real trailing window as the Sprint 8 canonical / SIG-003 config
# (168 hours), expressed in 5-minute bars instead of 1-hour bars.
ZSCORE_WINDOW_BARS = 168 * BARS_PER_HOUR_AT_5M
OU_WINDOW_BARS = 168 * BARS_PER_HOUR_AT_5M
BAR_DURATION_HOURS = 1.0 / BARS_PER_HOUR_AT_5M
# Same 240h real-time max vertical cap as the canonical 1h backtest, expressed
# as a bar-count cap at 5-minute granularity.
MAX_VERTICAL_BARS = 240 * BARS_PER_HOUR_AT_5M
# The exact threshold that produced gross PF=1.156 / n=74 on 1h bars in
# TASK-SIG-003 Run 2. max_half_life_hours is already real-time (hours);
# max_vertical_bars is a bar-count cap and is scaled above.
REPLICATION_MAX_HALF_LIFE_HOURS = 0.375
DEFAULT_DOWNLOAD_WORKERS = 8

_NORMALIZED = PROJECT_ROOT / "data/research/binance_public/normalized"
_COST_PILOT = PROJECT_ROOT / "data/research/binance_public/cost_pilot"
DEFAULT_RESEARCH_GATE_JSON = (
    _NORMALIZED / "sprint7_binance_usdm_202306_202605_research_gate.json"
)
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data/research/binance_public"
DEFAULT_OUTPUT_JSON = _COST_PILOT / "signal_intrahour_sanity_check.json"
DEFAULT_OUTPUT_CSV = _COST_PILOT / "signal_intrahour_sanity_pair_results.csv"
DEFAULT_REPORT_MD = PROJECT_ROOT / "reports/signal_intrahour_sanity_check.md"


def load_funding_by_pair(research_gate_json: Path, pairs: tuple[str, ...]) -> dict[str, float]:
    """Reuse the existing Sprint 7 (3-year window) funding_carry_bps_per_day.

    Not re-derived for this 6-month window: funding-rate download/merge is
    out of scope for a bounded sanity check. This is a documented
    approximation, not a precision claim -- see the report's Limites section.
    """

    payload = json.loads(research_gate_json.read_text(encoding="utf-8"))
    by_pair = {
        entry["pair"]: float(entry["funding_carry_bps_per_day"])
        for entry in payload["accepted_pairs"]
    }
    missing = [pair for pair in pairs if pair not in by_pair]
    if missing:
        raise ValueError(f"missing funding_carry_bps_per_day for pairs: {missing}")
    return {pair: by_pair[pair] for pair in pairs}


def download_and_normalize_bars(
    *,
    symbols: tuple[str, ...],
    start_month: str,
    end_month_exclusive: str,
    interval: str,
    dataset_version: str,
    data_root: Path,
    download_workers: int,
    download: bool,
) -> pd.DataFrame:
    """Download (if requested) and normalize real 5-minute klines only.

    Klines alone are sufficient: `merge_symbol_data` falls back to
    `close` for `price_for_research`/`log_price` when mark-price sidecars are
    absent, which is exactly what `_pair_frame` in statistical_backtest.py
    consumes. Mark/index/premium/funding archives are skipped -- not needed
    for this check and would triple the download for no benefit here.
    """

    specs = build_archive_plan(
        symbols,
        start_month=start_month,
        end_month_exclusive=end_month_exclusive,
        interval=interval,
        families=(BinanceDataFamily.KLINES,),
    )
    if download:
        download_archives(specs, data_root, max_workers=download_workers)
    return normalize_archive_plan(specs, data_root, dataset_version=dataset_version)


def run_sanity_check(
    bars: pd.DataFrame,
    funding_by_pair: dict[str, float],
    *,
    replication_max_half_life_hours: float = REPLICATION_MAX_HALF_LIFE_HOURS,
) -> dict[str, Any]:
    """Run baseline (unfiltered) and tight (replication threshold) configs.

    Not a new pre-registered decision grid like TASK-SIG-003 -- a plain
    two-way replication comparison against the specific finding that
    motivated this check.
    """

    baseline_config = StatisticalBacktestConfig(
        zscore_window=ZSCORE_WINDOW_BARS,
        ou_window=OU_WINDOW_BARS,
        max_vertical_bars=MAX_VERTICAL_BARS,
        bar_duration_hours=BAR_DURATION_HOURS,
    )
    tight_config = StatisticalBacktestConfig(
        zscore_window=ZSCORE_WINDOW_BARS,
        ou_window=OU_WINDOW_BARS,
        max_vertical_bars=MAX_VERTICAL_BARS,
        bar_duration_hours=BAR_DURATION_HOURS,
        max_half_life_hours=replication_max_half_life_hours,
    )
    baseline = _run_config(bars, funding_by_pair, baseline_config, "baseline_5m_unfiltered")
    tight = _run_config(
        bars,
        funding_by_pair,
        tight_config,
        f"tight_5m_max_half_life_{replication_max_half_life_hours}h",
    )
    return {
        "baseline": baseline,
        "tight": tight,
        "replication_max_half_life_hours": replication_max_half_life_hours,
        "motivating_finding": {
            "granularity": "1h",
            "trade_count": 74,
            "gross_profit_factor": 1.1559121228252034,
            "net_profit_factor": 0.8326776657330394,
        },
        "replicates": _replicates(tight),
    }


def _replicates(tight: dict[str, Any]) -> dict[str, Any]:
    """Descriptive-only comparison against the motivating 1h finding.

    No decision rule is applied here -- see the task file for why: this is a
    replication check, not a new pre-registered gate.
    """

    metrics = tight["portfolio_metrics"]
    return {
        "trade_count": metrics["trade_count"],
        "gross_profit_factor": tight["gross_profit_factor"],
        "net_profit_factor": metrics["profit_factor"],
        "note": (
            "Descriptive comparison only -- read alongside "
            "reports/signal_intrahour_sanity_check.md, not as a pass/fail gate."
        ),
    }


def _run_config(
    bars: pd.DataFrame,
    funding_by_pair: dict[str, float],
    config: StatisticalBacktestConfig,
    label: str,
) -> dict[str, Any]:
    per_pair = {}
    pair_rows = []
    all_resolved = []
    for pair in sorted(funding_by_pair):
        trades = run_pair_statistical_backtest(
            bars, pair, funding_carry_bps_per_day=funding_by_pair[pair], config=config
        )
        resolved = tuple(trade for trade in trades if trade.status is TradeStatus.RESOLVED)
        metrics = summarize_statistical_backtest(trades, target_notional=config.target_notional)
        all_resolved.extend(resolved)
        row = {
            "label": label,
            "pair": pair,
            "trade_count": metrics.trade_count,
            "unresolved_no_data_count": len(trades) - len(resolved),
            **asdict(metrics),
        }
        pair_rows.append(row)
        per_pair[pair] = row

    portfolio_metrics = summarize_statistical_backtest(
        tuple(all_resolved), target_notional=config.target_notional
    )
    gross_values = [trade.gross_pnl_bps for trade in all_resolved]
    gross_profit = sum(value for value in gross_values if value > 0.0)
    gross_loss = -sum(value for value in gross_values if value < 0.0)
    gross_profit_factor = gross_profit / gross_loss if gross_loss > 0.0 else math.inf
    return {
        "label": label,
        "config": asdict(config),
        "portfolio_metrics": asdict(portfolio_metrics),
        "gross_profit_factor": gross_profit_factor if all_resolved else math.nan,
        "per_pair": per_pair,
        "pair_rows": pair_rows,
    }


def _markdown_report(payload: dict[str, Any]) -> str:
    result = payload["result"]
    baseline = result["baseline"]
    tight = result["tight"]
    motivating = result["motivating_finding"]
    lines = [
        "# Signal Intrahour Sanity Check (TASK-SIG-004)",
        "",
        f"Data: {payload['generated_at_utc']}",
        "",
        "## Natureza desta checagem",
        "",
        "Signal Iteration 1 esta ENCERRADA como hipotese rejeitada (ADR-0010). "
        "Isto NAO e uma nova iteracao nem reabre SIG-001/002/003 -- e uma unica "
        "checagem de sanidade, de escopo pequeno, sobre um achado especifico: "
        "no bucket mais apertado do Run 2 da TASK-SIG-003 "
        "(max_half_life_hours=0,375, ~22,5 min, barras de 1h), o gross profit "
        "factor passou de 1,0 pela primeira vez em toda a iteracao (1,156), "
        "mas com apenas 74 trades em 3 pares -- amostra pequena demais para "
        "confiar. Esta checagem re-roda o MESMO pipeline causal com barras "
        "de 5 minutos, para ver se o achado se replica com amostra adequada.",
        "",
        "## Escopo (deliberadamente pequeno)",
        "",
        f"- Simbolos: {', '.join(SYMBOLS)} (8, nao os 20 completos).",
        f"- Pares: {', '.join(PAIRS)} (9, os que tiveram QUALQUER trade no "
        "bucket 0,375h do Run 2 -- nao so os 3 que passaram o gate por par, "
        "para evitar a sobrevivencia que a TASK-SIG-002 ja corrigiu uma vez).",
        f"- Janela: {payload['start_month']} a {payload['end_month_exclusive']} "
        "(6 meses, nao os 3 anos completos).",
        f"- Granularidade: {payload['interval']} (barras de 5 minutos).",
        "",
        "## Achado motivador (1h, TASK-SIG-003 Run 2, bucket 0,375h)",
        "",
        f"- Trades: {motivating['trade_count']}",
        f"- Gross profit factor: {motivating['gross_profit_factor']:.4f}",
        f"- Net profit factor: {motivating['net_profit_factor']:.4f}",
        "",
        "## Resultado (5 minutos, mesmo pipeline causal)",
        "",
        "`bar_duration_hours=1/12` foi propagado para OU, custo de funding e "
        "triple barrier. `max_vertical_bars=2880` preserva o mesmo cap real "
        "de 240h do backtest canonico de 1h, agora em barras de 5 minutos.",
        "",
        _table(
            ["Config", "Trades", "Gross bps", "Gross PF", "Net bps", "Net PF", "Hit rate"],
            [_result_row("Baseline (sem filtro de half-life)", baseline), _result_row(
                f"Tight (max_half_life_hours={result['replication_max_half_life_hours']})", tight
            )],
        ),
        "",
        "## O achado se replica?",
        "",
        f"{result['replicates']['note']}",
        f"- Trades no bucket tight (5min): {result['replicates']['trade_count']} "
        f"(vs. 74 em 1h)",
        f"- Gross PF (5min): {result['replicates']['gross_profit_factor']:.4f} "
        f"(vs. {motivating['gross_profit_factor']:.4f} em 1h)",
        f"- Net PF (5min): {result['replicates']['net_profit_factor']:.4f} "
        f"(vs. {motivating['net_profit_factor']:.4f} em 1h)",
        "",
        "## Limites (leia antes de interpretar)",
        "",
        "- Funding reusa o `funding_carry_bps_per_day` da Sprint 7 (janela de "
        "3 anos), NAO re-derivado para esta janela de 6 meses -- aproximacao "
        "razoavel para uma checagem exploratoria, nao uma medicao de precisao.",
        "- Sem novo modelo de custo, sem nova regra de decisao pre-registrada: "
        "esta secao e descritiva, nao um gate PASSA/NAO PASSA.",
        "- `historical_dataset.py::normalize_kline_frame` rotula a coluna "
        "`interval` da saida como `1h` independente do intervalo real "
        "baixado -- bug de metadado conhecido, nao corrigido aqui (fora do "
        "escopo desta task). O hardcode relacionado tambem pode afetar "
        "`return_1h`/`EXTREME_RETURN` em dados 5m; esses campos nao sao "
        "consumidos por `statistical_backtest.py`, que usa `log_price` e "
        "`open_time`.",
        "- Nao abre Sprint 10, nao reabre Signal Iteration 1.",
        "",
    ]
    return "\n".join(lines)


def _result_row(label: str, result: dict[str, Any]) -> list[str]:
    metrics = result["portfolio_metrics"]
    return [
        label,
        str(metrics["trade_count"]),
        f"{metrics['gross_pnl_bps']:.4f}",
        _fmt(result["gross_profit_factor"]),
        f"{metrics['net_pnl_bps']:.4f}",
        _fmt(metrics["profit_factor"]),
        f"{metrics['hit_rate'] * 100.0:.2f}%" if math.isfinite(metrics["hit_rate"]) else "NA",
    ]


def _fmt(value: float) -> str:
    if math.isnan(value):
        return "NA"
    if math.isinf(value):
        return "+inf" if value > 0.0 else "-inf"
    return f"{value:.4f}"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--research-gate-json", type=Path, default=DEFAULT_RESEARCH_GATE_JSON)
    parser.add_argument("--start-month", default=DEFAULT_START_MONTH)
    parser.add_argument("--end-month-exclusive", default=DEFAULT_END_MONTH_EXCLUSIVE)
    parser.add_argument("--interval", default=DEFAULT_INTERVAL)
    parser.add_argument("--dataset-version", default=DEFAULT_DATASET_VERSION)
    parser.add_argument("--download-workers", type=int, default=DEFAULT_DOWNLOAD_WORKERS)
    parser.add_argument("--no-download", dest="download", action="store_false")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(
        f"Downloading/normalizing {args.interval} klines for {len(SYMBOLS)} symbols, "
        f"{args.start_month} to {args.end_month_exclusive} ..."
    )
    bars = download_and_normalize_bars(
        symbols=SYMBOLS,
        start_month=args.start_month,
        end_month_exclusive=args.end_month_exclusive,
        interval=args.interval,
        dataset_version=args.dataset_version,
        data_root=args.data_root,
        download_workers=args.download_workers,
        download=args.download,
    )
    print(f"Normalized {len(bars)} bar rows across {bars['symbol'].nunique()} symbols.")
    normalized_csv = _NORMALIZED / f"{args.dataset_version}_bars.csv"
    normalized_csv.parent.mkdir(parents=True, exist_ok=True)
    bars.to_csv(normalized_csv, index=False)
    print(f"Wrote {normalized_csv}")

    funding_by_pair = load_funding_by_pair(args.research_gate_json, PAIRS)
    result = run_sanity_check(bars, funding_by_pair)

    for label, config_result in (("baseline", result["baseline"]), ("tight", result["tight"])):
        metrics = config_result["portfolio_metrics"]
        print(
            f"{label}: {metrics['trade_count']} trades, "
            f"gross_pf={config_result['gross_profit_factor']:.4f}, "
            f"net_pf={metrics['profit_factor']:.4f}"
        )

    payload = {
        "generated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "start_month": args.start_month,
        "end_month_exclusive": args.end_month_exclusive,
        "interval": args.interval,
        "symbols": list(SYMBOLS),
        "pairs": list(PAIRS),
        "result": result,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_json_ready(payload), indent=2, sort_keys=True), encoding="utf-8"
    )
    all_rows = result["baseline"]["pair_rows"] + result["tight"]["pair_rows"]
    pd.DataFrame(all_rows).to_csv(args.output_csv, index=False)
    args.report_md.write_text(_markdown_report(payload), encoding="utf-8")
    print(f"Wrote {args.output_json}")
    print(f"Wrote {args.output_csv}")
    print(f"Wrote {args.report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
