#!/usr/bin/env python3
"""Run a causal fast-reversion signal experiment against the canonical baseline.

This script reruns the candle-level statistical backtest. It does not filter
previous trades by realized ``bars_held``, ``outcome``, or PnL.
"""

from __future__ import annotations

import argparse
import json
import math
import numbers
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest.statistical_backtest import (  # noqa: E402
    StatisticalBacktestConfig,
    StatisticalTradeResult,
    TradeStatus,
    run_pair_statistical_backtest,
    summarize_statistical_backtest,
)

DEFAULT_BARS_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv"
)
DEFAULT_RESEARCH_GATE_JSON = (
    PROJECT_ROOT
    / (
        "data/research/binance_public/normalized/"
        "sprint7_binance_usdm_202306_202605_research_gate.json"
    )
)
DEFAULT_CANONICAL_JSON = (
    PROJECT_ROOT
    / "data/research/binance_public/cost_pilot/sprint8_canonical_backtest_results.json"
)
DEFAULT_OUTPUT_JSON = (
    PROJECT_ROOT
    / "data/research/binance_public/cost_pilot/signal_fast_reversion_experiment.json"
)
DEFAULT_OUTPUT_CSV = (
    PROJECT_ROOT
    / "data/research/binance_public/cost_pilot/signal_fast_reversion_pair_results.csv"
)
DEFAULT_REPORT_MD = PROJECT_ROOT / "reports/signal_fast_reversion_experiment.md"
EXPECTED_PAIR_COUNT = 41
FAST_VERTICAL_BARS = 4
BASELINE_VARIANT = "baseline_canonical"
FAST_VARIANT = "fast_vertical_4h"
METRIC_TOLERANCE = 1e-6
BASELINE_REPRODUCTION_EXIT_CODE = 2


@dataclass(frozen=True, slots=True)
class SignalExperimentVariant:
    """One causal signal experiment variant."""

    name: str
    description: str
    config: StatisticalBacktestConfig


def build_experiment_variants() -> tuple[SignalExperimentVariant, ...]:
    """Return the baseline and causal fast-reversion variant."""

    baseline = StatisticalBacktestConfig()
    fast_vertical = StatisticalBacktestConfig(max_vertical_bars=FAST_VERTICAL_BARS)
    return (
        SignalExperimentVariant(
            name=BASELINE_VARIANT,
            description="Canonical Sprint 8 statistical backtest defaults.",
            config=baseline,
        ),
        SignalExperimentVariant(
            name=FAST_VARIANT,
            description=(
                "Causal fast-reversion exit: cap vertical barrier at 4 bars before "
                "the backtest is run."
            ),
            config=fast_vertical,
        ),
    )


def load_pairs_and_funding(research_gate_json: Path) -> dict[str, float]:
    """Load the 41 Sprint 7 statistical pairs and funding carry."""

    payload = json.loads(research_gate_json.read_text(encoding="utf-8"))
    accepted = payload["accepted_pairs"]
    if len(accepted) != EXPECTED_PAIR_COUNT:
        raise ValueError(
            f"expected {EXPECTED_PAIR_COUNT} Sprint 7 statistical pairs, got {len(accepted)}"
        )
    funding_by_pair = {}
    for entry in accepted:
        if entry["statistical_status"] != "ACCEPT":
            raise ValueError(f"pair {entry['pair']} is not statistical_status=ACCEPT")
        funding_by_pair[str(entry["pair"])] = float(entry["funding_carry_bps_per_day"])
    return funding_by_pair


def run_signal_experiment(
    bars: pd.DataFrame,
    funding_by_pair: dict[str, float],
    variants: tuple[SignalExperimentVariant, ...],
) -> dict[str, Any]:
    """Run all causal variants against the same bars and pair universe."""

    variant_results = {
        variant.name: _run_variant(
            bars=bars,
            funding_by_pair=funding_by_pair,
            variant=variant,
        )
        for variant in variants
    }
    return {
        "variants": variant_results,
        "comparison": compare_variant_results(
            variant_results[BASELINE_VARIANT],
            variant_results[FAST_VARIANT],
        ),
    }


def compare_variant_results(
    baseline: dict[str, Any],
    fast_vertical: dict[str, Any],
) -> dict[str, Any]:
    """Compare the fast-reversion variant against baseline metrics."""

    baseline_metrics = baseline["portfolio_metrics"]
    fast_metrics = fast_vertical["portfolio_metrics"]
    gross_delta = fast_metrics["gross_pnl_bps"] - baseline_metrics["gross_pnl_bps"]
    net_delta = fast_metrics["net_pnl_bps"] - baseline_metrics["net_pnl_bps"]
    pf_delta = fast_metrics["profit_factor"] - baseline_metrics["profit_factor"]
    trade_delta = fast_metrics["trade_count"] - baseline_metrics["trade_count"]
    approved_delta = fast_vertical["approved_pair_count"] - baseline["approved_pair_count"]
    outcome_deltas = {
        key: fast_vertical["outcome_counts"][key] - baseline["outcome_counts"][key]
        for key in ("profit_count", "stop_count", "vertical_count")
    }
    candidate_for_next_iteration = (
        gross_delta > 0.0
        and net_delta > 0.0
        and fast_metrics["profit_factor"] > baseline_metrics["profit_factor"]
    )
    return {
        "gross_pnl_bps_delta": gross_delta,
        "net_pnl_bps_delta": net_delta,
        "profit_factor_delta": pf_delta,
        "trade_count_delta": trade_delta,
        "max_drawdown_bps_delta": (
            fast_metrics["max_drawdown_bps"] - baseline_metrics["max_drawdown_bps"]
        ),
        "avg_bars_held_delta": fast_metrics["avg_bars_held"] - baseline_metrics["avg_bars_held"],
        "approved_pair_count_delta": approved_delta,
        "outcome_count_deltas": outcome_deltas,
        "candidate_for_next_iteration": candidate_for_next_iteration,
        "decision": (
            "CONTINUE_SIGNAL_ITERATION"
            if candidate_for_next_iteration
            else "STOP_FAST_REVERSION_PATH"
        ),
        "interpretation": _comparison_interpretation(
            baseline_metrics=baseline_metrics,
            fast_metrics=fast_metrics,
            gross_delta=gross_delta,
            net_delta=net_delta,
            trade_delta=trade_delta,
        ),
    }


def baseline_reproduction_check(
    baseline_result: dict[str, Any],
    canonical_payload: dict[str, Any],
) -> dict[str, Any]:
    """Check that the rerun baseline reproduces the canonical artifact."""

    canonical_metrics = canonical_payload["portfolio_metrics"]
    baseline_metrics = baseline_result["portfolio_metrics"]
    metrics = (
        "trade_count",
        "gross_pnl_bps",
        "cost_bps",
        "net_pnl_bps",
        "profit_factor",
        "hit_rate",
    )
    deltas = {
        metric: _metric_delta(baseline_metrics[metric], canonical_metrics[metric])
        for metric in metrics
    }
    approved_delta = baseline_result["approved_pair_count"] - int(
        canonical_payload["approved_pair_count"]
    )
    pass_check = approved_delta == 0 and all(
        abs(value) <= METRIC_TOLERANCE for value in deltas.values()
    )
    return {
        "pass": pass_check,
        "metric_deltas": deltas,
        "approved_pair_count_delta": approved_delta,
    }


def _run_variant(
    *,
    bars: pd.DataFrame,
    funding_by_pair: dict[str, float],
    variant: SignalExperimentVariant,
) -> dict[str, Any]:
    per_pair = {}
    pair_rows = []
    all_resolved: list[StatisticalTradeResult] = []
    approved_pairs = []
    rejected_pairs = []

    for pair in sorted(funding_by_pair):
        trades = run_pair_statistical_backtest(
            bars,
            pair,
            funding_carry_bps_per_day=funding_by_pair[pair],
            config=variant.config,
        )
        resolved = tuple(trade for trade in trades if trade.status is TradeStatus.RESOLVED)
        metrics = summarize_statistical_backtest(
            trades,
            target_notional=variant.config.target_notional,
        )
        unresolved_no_data = len(trades) - len(resolved)
        all_resolved.extend(resolved)
        if metrics.profit_factor_gate_pass:
            approved_pairs.append(pair)
        else:
            rejected_pairs.append(pair)

        outcome_counts = _outcome_counts(resolved)
        row = {
            "variant": variant.name,
            "pair": pair,
            "funding_carry_bps_per_day": funding_by_pair[pair],
            "unresolved_no_data_count": unresolved_no_data,
            **asdict(metrics),
            **outcome_counts,
            "profit_factor_gate_pass": metrics.profit_factor_gate_pass,
        }
        pair_rows.append(row)
        per_pair[pair] = row

    portfolio_metrics = summarize_statistical_backtest(
        tuple(all_resolved),
        target_notional=variant.config.target_notional,
    )
    return {
        "name": variant.name,
        "description": variant.description,
        "config": asdict(variant.config),
        "approved_pairs": sorted(approved_pairs),
        "rejected_pairs": sorted(rejected_pairs),
        "approved_pair_count": len(approved_pairs),
        "rejected_pair_count": len(rejected_pairs),
        "portfolio_metrics": asdict(portfolio_metrics),
        "outcome_counts": _outcome_counts(tuple(all_resolved)),
        "per_pair": per_pair,
        "pair_rows": pair_rows,
    }


def _outcome_counts(trades: tuple[StatisticalTradeResult, ...]) -> dict[str, int]:
    counts = {"profit_count": 0, "stop_count": 0, "vertical_count": 0}
    for trade in trades:
        outcome = str(trade.outcome).rsplit(".", maxsplit=1)[-1]
        if outcome == "PROFIT":
            counts["profit_count"] += 1
        elif outcome == "STOP":
            counts["stop_count"] += 1
        elif outcome == "VERTICAL":
            counts["vertical_count"] += 1
    return counts


def _comparison_interpretation(
    *,
    baseline_metrics: dict[str, Any],
    fast_metrics: dict[str, Any],
    gross_delta: float,
    net_delta: float,
    trade_delta: int,
) -> str:
    if gross_delta > 0.0 and net_delta > 0.0:
        return (
            "Fast vertical cap improved gross and net PnL versus baseline. "
            "Treat as a candidate signal iteration, subject to formal review."
        )
    if trade_delta < 0 and fast_metrics["trade_count"] < baseline_metrics["trade_count"]:
        return (
            "Fast vertical cap reduced the trade sample but did not improve both gross "
            "and net PnL. Do not continue this path without a stronger causal signal."
        )
    return (
        "Fast vertical cap did not improve both gross and net PnL. "
        "Do not promote this signal change."
    )


def _baseline_reproduction_error(check: dict[str, Any]) -> str:
    return (
        "Baseline reproduction failed; aborting fast-reversion comparison. "
        f"metric_deltas={check['metric_deltas']} "
        f"approved_pair_count_delta={check['approved_pair_count_delta']}"
    )


def _metric_delta(left: Any, right: Any) -> float:
    left_value = float(left)
    right_value = float(right)
    if math.isinf(left_value) and math.isinf(right_value):
        return 0.0
    return left_value - right_value


def _pair_rows_for_csv(experiment: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for variant in experiment["variants"].values():
        rows.extend(variant["pair_rows"])
    return rows


def _summary_json(experiment: dict[str, Any]) -> dict[str, Any]:
    return {
        "variants": {
            name: {
                "description": result["description"],
                "config": result["config"],
                "approved_pair_count": result["approved_pair_count"],
                "approved_pairs": result["approved_pairs"],
                "portfolio_metrics": result["portfolio_metrics"],
                "outcome_counts": result["outcome_counts"],
            }
            for name, result in experiment["variants"].items()
        },
        "comparison": experiment["comparison"],
        "baseline_reproduction": experiment.get("baseline_reproduction"),
    }


def _markdown_report(payload: dict[str, Any]) -> str:
    summary = _summary_json(payload["experiment"])
    baseline = summary["variants"][BASELINE_VARIANT]
    fast = summary["variants"][FAST_VARIANT]
    comparison = summary["comparison"]
    baseline_reproduction = summary["baseline_reproduction"]
    lines = [
        "# Signal Fast Reversion Experiment",
        "",
        f"Data: {payload['generated_at_utc']}",
        "",
        "## Objetivo",
        "",
        "Testar uma regra causal de reversao rapida (`max_vertical_bars=4`) "
        "contra o baseline canonico. Este experimento reroda o backtest; ele "
        "nao filtra trades antigos por `bars_held`, `outcome`, gross ou net PnL.",
        "",
        "## Baseline Reproduction",
        "",
        f"- Passou: {baseline_reproduction['pass']}",
        f"- Deltas: `{baseline_reproduction['metric_deltas']}`",
        f"- Delta approved pairs: {baseline_reproduction['approved_pair_count_delta']}",
        "",
        "## Nota De Implementacao",
        "",
        "Durante a implementacao foi corrigido um bug no backtest estatistico: "
        "a janela enviada ao resolvedor de triple barrier precisava incluir uma "
        "barra adicional alem do orcamento vertical para confirmar VERTICAL. Sem "
        "essa barra, a variante curta podia transformar VERTICAL em NO_DATA "
        "artificialmente. A correcao tem regressao dedicada em "
        "`tests/test_statistical_backtest.py`.",
        "",
        "## Portfolio",
        "",
        _portfolio_table(baseline, fast),
        "",
        "## Comparacao",
        "",
        _table(
            ["Metrica", "Delta fast - baseline"],
            [
                ["Gross PnL bps", _fmt(comparison["gross_pnl_bps_delta"])],
                ["Net PnL bps", _fmt(comparison["net_pnl_bps_delta"])],
                ["Profit factor", _fmt(comparison["profit_factor_delta"])],
                ["Max drawdown bps", _fmt(comparison["max_drawdown_bps_delta"])],
                ["Avg bars held", _fmt(comparison["avg_bars_held_delta"])],
                ["Trade count", str(comparison["trade_count_delta"])],
                ["Approved pair count", str(comparison["approved_pair_count_delta"])],
            ],
        ),
        "",
        "## Decomposicao",
        "",
        _decomposition_table(baseline, fast, comparison),
        "",
        "## Decisao",
        "",
        f"- Decisao: `{comparison['decision']}`",
        f"- Candidate for next iteration: {comparison['candidate_for_next_iteration']}",
        f"- Interpretacao: {comparison['interpretation']}",
        "",
        "## Limites",
        "",
        "- O backtest continua permitindo trades sobrepostos, como no Sprint 8 canonico.",
        "- Custo continua sendo a suposicao fixa conservadora do backtest estatistico.",
        "- Nada neste experimento abre Sprint 10, paper trading ou live trading.",
        "",
    ]
    return "\n".join(lines)


def _decomposition_table(
    baseline: dict[str, Any],
    fast: dict[str, Any],
    comparison: dict[str, Any],
) -> str:
    return _table(
        ["Metrica", BASELINE_VARIANT, FAST_VARIANT, "Delta"],
        [
            [
                "PROFIT count",
                str(baseline["outcome_counts"]["profit_count"]),
                str(fast["outcome_counts"]["profit_count"]),
                str(comparison["outcome_count_deltas"]["profit_count"]),
            ],
            [
                "STOP count",
                str(baseline["outcome_counts"]["stop_count"]),
                str(fast["outcome_counts"]["stop_count"]),
                str(comparison["outcome_count_deltas"]["stop_count"]),
            ],
            [
                "VERTICAL count",
                str(baseline["outcome_counts"]["vertical_count"]),
                str(fast["outcome_counts"]["vertical_count"]),
                str(comparison["outcome_count_deltas"]["vertical_count"]),
            ],
            [
                "Avg bars held",
                _fmt(baseline["portfolio_metrics"]["avg_bars_held"]),
                _fmt(fast["portfolio_metrics"]["avg_bars_held"]),
                _fmt(comparison["avg_bars_held_delta"]),
            ],
            [
                "Max drawdown bps",
                _fmt(baseline["portfolio_metrics"]["max_drawdown_bps"]),
                _fmt(fast["portfolio_metrics"]["max_drawdown_bps"]),
                _fmt(comparison["max_drawdown_bps_delta"]),
            ],
        ],
    )


def _portfolio_table(baseline: dict[str, Any], fast: dict[str, Any]) -> str:
    return _table(
        [
            "Variant",
            "Trades",
            "Gross bps",
            "Net bps",
            "PF",
            "Hit rate",
            "Drawdown",
            "Avg hold",
            "Approved pairs",
        ],
        [
            _portfolio_row(BASELINE_VARIANT, baseline),
            _portfolio_row(FAST_VARIANT, fast),
        ],
    )


def _portfolio_row(name: str, result: dict[str, Any]) -> list[str]:
    metrics = result["portfolio_metrics"]
    return [
        name,
        str(metrics["trade_count"]),
        _fmt(metrics["gross_pnl_bps"]),
        _fmt(metrics["net_pnl_bps"]),
        _fmt(metrics["profit_factor"]),
        _pct(metrics["hit_rate"]),
        _fmt(metrics["max_drawdown_bps"]),
        _fmt(metrics["avg_bars_held"]),
        str(result["approved_pair_count"]),
    ]


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    numeric = float(value)
    if math.isnan(numeric):
        return "NA"
    if math.isinf(numeric):
        return "+inf" if numeric > 0.0 else "-inf"
    return f"{numeric:.4f}"


def _pct(value: Any) -> str:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bars-csv", type=Path, default=DEFAULT_BARS_CSV)
    parser.add_argument("--research-gate-json", type=Path, default=DEFAULT_RESEARCH_GATE_JSON)
    parser.add_argument("--canonical-json", type=Path, default=DEFAULT_CANONICAL_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(f"Loading bars from {args.bars_csv} ...")
    bars = pd.read_csv(args.bars_csv, usecols=["symbol", "open_time", "log_price"])
    funding_by_pair = load_pairs_and_funding(args.research_gate_json)
    experiment = run_signal_experiment(
        bars=bars,
        funding_by_pair=funding_by_pair,
        variants=build_experiment_variants(),
    )
    canonical_payload = json.loads(args.canonical_json.read_text(encoding="utf-8"))
    experiment["baseline_reproduction"] = baseline_reproduction_check(
        experiment["variants"][BASELINE_VARIANT],
        canonical_payload,
    )
    if not experiment["baseline_reproduction"]["pass"]:
        print(_baseline_reproduction_error(experiment["baseline_reproduction"]), file=sys.stderr)
        return BASELINE_REPRODUCTION_EXIT_CODE
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "bars_csv": str(args.bars_csv),
        "research_gate_json": str(args.research_gate_json),
        "canonical_json": str(args.canonical_json),
        "experiment": experiment,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(_json_ready(payload), allow_nan=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(_pair_rows_for_csv(experiment)).to_csv(args.output_csv, index=False)
    args.report_md.write_text(_markdown_report(payload), encoding="utf-8")
    print(json.dumps(_json_ready(_summary_json(experiment)), allow_nan=False, indent=2))
    print(f"Wrote {args.output_json}")
    print(f"Wrote {args.output_csv}")
    print(f"Wrote {args.report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
