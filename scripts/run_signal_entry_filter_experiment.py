#!/usr/bin/env python3
"""Ex-ante ENTRY-filter falsification test (TASK-SIG-003).

Reruns the candle-level statistical backtest across a fixed, pre-registered
grid of `max_half_life_hours` entry gates. `max_half_life_hours` is already a
causal entry gate: the OU half-life comes from a trailing refit ending at the
entry bar (never full-sample). Tightening it only changes which entries are
taken, using information known at entry time.

Discipline (per TASK-SIG-003): the decision rule is PRE-REGISTERED and applied
literally. The whole grid is reported, never just the best bucket. Nothing here
filters trades ex-post by realized bars_held/outcome/PnL.
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

_NORMALIZED = PROJECT_ROOT / "data/research/binance_public/normalized"
_COST_PILOT = PROJECT_ROOT / "data/research/binance_public/cost_pilot"
DEFAULT_BARS_CSV = _NORMALIZED / "sprint7_binance_usdm_202306_202605_bars.csv"
DEFAULT_RESEARCH_GATE_JSON = _NORMALIZED / "sprint7_binance_usdm_202306_202605_research_gate.json"
DEFAULT_CANONICAL_JSON = _COST_PILOT / "sprint8_canonical_backtest_results.json"
DEFAULT_OUTPUT_JSON = _COST_PILOT / "signal_entry_filter_experiment.json"
DEFAULT_OUTPUT_CSV = _COST_PILOT / "signal_entry_filter_pair_results.csv"
DEFAULT_REPORT_MD = PROJECT_ROOT / "reports/signal_entry_filter_experiment.md"

EXPECTED_PAIR_COUNT = 41
# Pre-registered Run 1 grid of ex-ante entry half-life gates (hours).
# 240 == canonical. Found NON-BINDING (see reports/signal_entry_filter_experiment.md):
# >99.9% of entries already have trailing half-life < 12h, so this grid never
# actually carves out a distinct subpopulation.
HALF_LIFE_GRID_HOURS = (240.0, 120.0, 72.0, 48.0, 24.0, 12.0)
# Pre-registered Run 2 grid, added after Run 1's Quant Research review found
# Run 1 non-binding. 240h is kept as the canonical reproduction anchor; the
# remaining thresholds descend well below the Run 1 floor (12h) so the gate
# actually excludes a material fraction of entries. Same decision rule
# applies independently to this grid -- this is a fresh pre-registration, not
# cherry-picked buckets appended to Run 1.
RUN2_HALF_LIFE_GRID_HOURS = (240.0, 12.0, 6.0, 3.0, 1.5, 0.75, 0.375)
BASELINE_HALF_LIFE_HOURS = 240.0
# A grid is considered to have "bitten" if it excludes at least this fraction
# of the 240h baseline's trade count somewhere in the grid -- otherwise the
# STOP/CONTINUE decision cannot be read as evidence about entry-filtering,
# only as "this grid didn't reach a binding threshold."
MIN_BINDING_EXCLUSION_FRACTION = 0.05
# Pre-registered decision thresholds (TASK-SIG-003).
MIN_NET_PROFIT_FACTOR = 1.10
MIN_TRADE_COUNT = 200
METRIC_TOLERANCE = 1e-6
BASELINE_REPRODUCTION_EXIT_CODE = 2


@dataclass(frozen=True, slots=True)
class EntryFilterVariant:
    """One ex-ante entry-filter variant, identified by its half-life gate."""

    name: str
    max_half_life_hours: float
    config: StatisticalBacktestConfig


def _variant_name(half_life_hours: float) -> str:
    if float(half_life_hours).is_integer():
        return f"max_half_life_{int(half_life_hours)}h"
    return f"max_half_life_{half_life_hours}h".replace(".", "p")


def build_entry_filter_variants(
    grid: tuple[float, ...] = HALF_LIFE_GRID_HOURS,
) -> tuple[EntryFilterVariant, ...]:
    """Return one variant per half-life gate in the given (pre-registered) grid."""

    return tuple(
        EntryFilterVariant(
            name=_variant_name(hours),
            max_half_life_hours=hours,
            config=StatisticalBacktestConfig(max_half_life_hours=hours),
        )
        for hours in grid
    )


def binding_check(
    variant_results: dict[str, Any],
    *,
    min_exclusion_fraction: float = MIN_BINDING_EXCLUSION_FRACTION,
) -> dict[str, Any]:
    """Check whether the grid excluded a material fraction of its loosest variant's trades.

    A grid where every threshold keeps ~all trades never tests the entry-filter
    hypothesis -- it just reruns the same population repeatedly. Without this
    check, a STOP decision from a non-binding grid would be misreported as
    evidence against entry filtering in general, when it is only evidence that
    THIS grid never reached a binding threshold. Compares the grid's own
    loosest (largest max_half_life_hours) vs tightest variant, so this works
    for any pre-registered grid, not just one that happens to include the
    240h canonical baseline.
    """

    loosest = max(variant_results.values(), key=lambda r: r["max_half_life_hours"])
    loosest_trade_count = loosest["portfolio_metrics"]["trade_count"]
    min_trade_count = min(
        result["portfolio_metrics"]["trade_count"] for result in variant_results.values()
    )
    excluded_fraction = (
        (loosest_trade_count - min_trade_count) / loosest_trade_count
        if loosest_trade_count
        else 0.0
    )
    is_binding = excluded_fraction >= min_exclusion_fraction
    if is_binding:
        caveat = (
            f"Grid excluded {excluded_fraction:.2%} of the loosest variant's trades at "
            "its tightest threshold -- binding; the decision below is evidence about "
            "the entry-filter hypothesis, not just about this grid's range."
        )
    else:
        caveat = (
            f"Grid excluded at most {excluded_fraction:.4%} of the loosest variant's "
            f"trades across all thresholds -- below the {min_exclusion_fraction:.0%} bar "
            "for calling this grid binding. A STOP decision from a non-binding grid is "
            "evidence that THIS grid never reached a threshold that actually filters "
            "entries, not evidence against entry-filtering in general."
        )
    return {
        "loosest_variant_trade_count": loosest_trade_count,
        "min_trade_count_in_grid": min_trade_count,
        "max_excluded_fraction": excluded_fraction,
        "min_exclusion_fraction_required": min_exclusion_fraction,
        "is_binding": is_binding,
        "caveat": caveat,
    }


def load_pairs_and_funding(research_gate_json: Path) -> dict[str, float]:
    """Load the 41 Sprint 7 statistical pairs and their real funding carry."""

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


def run_entry_filter_experiment(
    bars: pd.DataFrame,
    funding_by_pair: dict[str, float],
    variants: tuple[EntryFilterVariant, ...],
) -> dict[str, Any]:
    """Run every entry-filter variant against the same bars and universe."""

    variant_results = {
        variant.name: _run_variant(bars=bars, funding_by_pair=funding_by_pair, variant=variant)
        for variant in variants
    }
    binding = binding_check(variant_results)
    return {
        "variants": variant_results,
        "binding": binding,
        "decision": apply_pre_registered_decision(variant_results, binding=binding),
    }


def apply_pre_registered_decision(
    variant_results: dict[str, Any],
    *,
    binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply the TASK-SIG-003 pre-registered rule literally to the whole grid.

    CONTINUE only if some variant has net_profit_factor >= 1.10 AND
    trade_count >= 200. Otherwise STOP. Even a CONTINUE is a weak,
    multiple-comparison-caveated candidate, never an approval. The literal
    pass/fail rule never changes based on `binding` -- it only changes how the
    result is INTERPRETED (a STOP from a non-binding grid must say so, not be
    reported as evidence against entry-filtering in general).
    """

    passing = []
    for name, result in variant_results.items():
        metrics = result["portfolio_metrics"]
        pf = metrics["profit_factor"]
        trade_count = metrics["trade_count"]
        pf_ok = (not math.isnan(pf)) and pf >= MIN_NET_PROFIT_FACTOR
        if pf_ok and trade_count >= MIN_TRADE_COUNT:
            passing.append(name)
    decision = "CONTINUE_SIGNAL_ITERATION" if passing else "STOP_SIGNAL_ITERATION"
    return {
        "passing_variants": sorted(passing),
        "decision": decision,
        "min_net_profit_factor": MIN_NET_PROFIT_FACTOR,
        "min_trade_count": MIN_TRADE_COUNT,
        "multiple_comparison_caveat": (
            "Grid has multiple thresholds; a single passing bucket is weak evidence "
            "(possible sampling luck). A CONTINUE is only a trigger for a "
            "dedicated out-of-sample test, never an approval."
        ),
        "interpretation": _decision_interpretation(decision, passing, binding),
    }


def _decision_interpretation(
    decision: str,
    passing: list[str],
    binding: dict[str, Any] | None,
) -> str:
    if decision == "CONTINUE_SIGNAL_ITERATION":
        return (
            f"At least one entry-filter threshold ({', '.join(sorted(passing))}) cleared "
            "net PF >= 1.10 on >= 200 trades. Candidate only: requires an out-of-sample "
            "confirmation before any credit is given to the signal."
        )
    if binding is not None and not binding["is_binding"]:
        return (
            "No entry-filter threshold produced net PF >= 1.10 on >= 200 trades, but "
            "this grid was NON-BINDING (excluded at most "
            f"{binding['max_excluded_fraction']:.4%} of the loosest variant's trades). "
            "This is evidence that THIS grid never reached a threshold that actually "
            "filters entries -- it does NOT show that entry filtering in general lacks "
            "an edge. A tighter, binding grid must be tested before concluding that."
        )
    return (
        "No entry-filter threshold produced net PF >= 1.10 on >= 200 trades, on a grid "
        "that materially excluded entries at its tightest threshold. This is evidence "
        "against the ex-ante entry-filter hypothesis at this grid's range. Stop signal "
        "iteration; hand the macro decision back to the user."
    )


def baseline_reproduction_check(
    baseline_result: dict[str, Any],
    canonical_payload: dict[str, Any],
) -> dict[str, Any]:
    """Check the 240h variant reproduces the canonical Sprint 8 artifact."""

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
    variant: EntryFilterVariant,
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
            trades, target_notional=variant.config.target_notional
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
            "max_half_life_hours": variant.max_half_life_hours,
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
        tuple(all_resolved), target_notional=variant.config.target_notional
    )
    portfolio_dict = asdict(portfolio_metrics)
    gross_per_trade = (
        portfolio_dict["gross_pnl_bps"] / portfolio_dict["trade_count"]
        if portfolio_dict["trade_count"]
        else math.nan
    )
    return {
        "name": variant.name,
        "max_half_life_hours": variant.max_half_life_hours,
        "config": asdict(variant.config),
        "approved_pairs": sorted(approved_pairs),
        "rejected_pairs": sorted(rejected_pairs),
        "approved_pair_count": len(approved_pairs),
        "rejected_pair_count": len(rejected_pairs),
        "portfolio_metrics": portfolio_dict,
        "gross_pnl_bps_per_trade": gross_per_trade,
        "gross_profit_factor": _gross_profit_factor(tuple(all_resolved)),
        "outcome_counts": _outcome_counts(tuple(all_resolved)),
        "per_pair": per_pair,
        "pair_rows": pair_rows,
    }


def _gross_profit_factor(trades: tuple[StatisticalTradeResult, ...]) -> float:
    """Profit factor computed on gross (pre-cost) PnL, mirroring the net PF
    convention: +inf when there are wins and zero gross losses, NaN when
    there are no trades at all."""

    if not trades:
        return math.nan
    gross_values = [trade.gross_pnl_bps for trade in trades]
    gross_profit = sum(value for value in gross_values if value > 0.0)
    gross_loss = -sum(value for value in gross_values if value < 0.0)
    if gross_loss > 0.0:
        return gross_profit / gross_loss
    return math.inf


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
                "max_half_life_hours": result["max_half_life_hours"],
                "config": result["config"],
                "approved_pair_count": result["approved_pair_count"],
                "approved_pairs": result["approved_pairs"],
                "portfolio_metrics": result["portfolio_metrics"],
                "gross_pnl_bps_per_trade": result["gross_pnl_bps_per_trade"],
                "gross_profit_factor": result["gross_profit_factor"],
                "outcome_counts": result["outcome_counts"],
            }
            for name, result in experiment["variants"].items()
        },
        "binding": experiment.get("binding"),
        "decision": experiment["decision"],
        "baseline_reproduction": experiment.get("baseline_reproduction"),
    }


def _markdown_report(payload: dict[str, Any]) -> str:
    summary = _summary_json(payload["experiment"])
    baseline_reproduction = summary["baseline_reproduction"]
    decision = summary["decision"]
    binding = summary["binding"]
    grid_hours = payload["half_life_grid_hours"]
    grid_rows = [
        _grid_row(summary["variants"][_variant_name(hours)])
        for hours in grid_hours
    ]
    lines = [
        "# Signal Entry-Filter Falsification Experiment (TASK-SIG-003)",
        "",
        f"Data: {payload['generated_at_utc']}",
        f"Run: `{payload.get('run_label', 'run1')}` -- grade: {grid_hours}",
        "",
        "## Objetivo",
        "",
        "Teste de falsificacao ex-ante do lado da ENTRADA: varrer o gate causal "
        "`max_half_life_hours` (meia-vida OU trailing conhecida na entrada) numa grade "
        "fixa e pre-registrada, para ver se algum filtro de entrada seleciona uma "
        "subpopulacao com edge liquido real. Nao filtra trades ex-post.",
        "",
        "## Regra De Decisao Pre-Registrada",
        "",
        f"- CONTINUE apenas se algum threshold tiver net profit factor >= {MIN_NET_PROFIT_FACTOR} "
        f"E trade_count >= {MIN_TRADE_COUNT}.",
        "- Caso contrario STOP_SIGNAL_ITERATION.",
        f"- {decision['multiple_comparison_caveat']}",
        "",
        "## Baseline Reproduction (240h == canonico)",
        "",
        f"- Passou: {baseline_reproduction['pass']}",
        f"- Deltas: `{baseline_reproduction['metric_deltas']}`",
        f"- Delta approved pairs: {baseline_reproduction['approved_pair_count_delta']}",
        "",
        "## Grade e Vinculante? (auditoria anti-grade-nao-mordente)",
        "",
        f"- Grade e vinculante: {binding['is_binding']}",
        f"- Trades no variant mais solto: {binding['loosest_variant_trade_count']}",
        f"- Trades no variant mais apertado: {binding['min_trade_count_in_grid']}",
        f"- Fracao maxima excluida: {binding['max_excluded_fraction']:.4%}",
        f"- {binding['caveat']}",
        "",
        "## Grade Completa (todos os thresholds, nao so o melhor)",
        "",
        _table(
            [
                "max_half_life_h",
                "Trades",
                "Gross bps/trade",
                "Gross bps",
                "Gross PF",
                "Net bps",
                "Net PF",
                "Hit rate",
                "Max drawdown bps",
                "PROFIT",
                "STOP",
                "VERTICAL",
                "Approved pairs",
                "Passa regra",
            ],
            grid_rows,
        ),
        "",
        "## Decisao",
        "",
        f"- Decisao: `{decision['decision']}`",
        f"- Thresholds que passam a regra: {decision['passing_variants'] or 'nenhum'}",
        f"- Interpretacao: {decision['interpretation']}",
        "",
        "## Limites",
        "",
        "- O backtest continua permitindo trades sobrepostos, como no Sprint 8 canonico.",
        "- Custo continua sendo a suposicao fixa conservadora do backtest estatistico.",
        "- Um CONTINUE seria candidato fraco, exigindo teste out-of-sample; nao e aprovacao.",
        "- Se a grade nao for vinculante, a decisao NAO se generaliza a filtros mais "
        "apertados -- ver secao 'Grade e Vinculante?' acima.",
        "- Nada neste experimento abre Sprint 10, paper trading ou live trading.",
        "",
    ]
    return "\n".join(lines)


def _grid_row(variant: dict[str, Any]) -> list[str]:
    metrics = variant["portfolio_metrics"]
    pf = metrics["profit_factor"]
    trade_count = metrics["trade_count"]
    outcomes = variant["outcome_counts"]
    passes = (not math.isnan(pf)) and pf >= MIN_NET_PROFIT_FACTOR and trade_count >= MIN_TRADE_COUNT
    return [
        _fmt_hours(variant["max_half_life_hours"]),
        str(trade_count),
        _fmt(variant["gross_pnl_bps_per_trade"]),
        _fmt(metrics["gross_pnl_bps"]),
        _fmt(variant["gross_profit_factor"]),
        _fmt(metrics["net_pnl_bps"]),
        _fmt(pf),
        _pct(metrics["hit_rate"]),
        _fmt(metrics["max_drawdown_bps"]),
        str(outcomes["profit_count"]),
        str(outcomes["stop_count"]),
        str(outcomes["vertical_count"]),
        str(variant["approved_pair_count"]),
        "sim" if passes else "nao",
    ]


def _fmt_hours(hours: float) -> str:
    return str(int(hours)) if float(hours).is_integer() else f"{hours:g}"


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


def _parse_grid(raw: str) -> tuple[float, ...]:
    hours = tuple(float(part.strip()) for part in raw.split(",") if part.strip())
    if not hours:
        raise ValueError("grid must contain at least one half-life value")
    if BASELINE_HALF_LIFE_HOURS not in hours:
        raise ValueError(
            f"grid must include the {BASELINE_HALF_LIFE_HOURS}h canonical baseline "
            "so it can be reproduction-checked; run the baseline separately if "
            "testing a grid that intentionally excludes it"
        )
    return hours


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bars-csv", type=Path, default=DEFAULT_BARS_CSV)
    parser.add_argument("--research-gate-json", type=Path, default=DEFAULT_RESEARCH_GATE_JSON)
    parser.add_argument("--canonical-json", type=Path, default=DEFAULT_CANONICAL_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument(
        "--grid",
        type=_parse_grid,
        default=HALF_LIFE_GRID_HOURS,
        help="Comma-separated half-life hours; must include 240 (canonical baseline).",
    )
    parser.add_argument("--run-label", type=str, default="run1")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(f"Loading bars from {args.bars_csv} ...")
    bars = pd.read_csv(args.bars_csv, usecols=["symbol", "open_time", "log_price"])
    funding_by_pair = load_pairs_and_funding(args.research_gate_json)
    experiment = run_entry_filter_experiment(
        bars=bars,
        funding_by_pair=funding_by_pair,
        variants=build_entry_filter_variants(args.grid),
    )
    canonical_payload = json.loads(args.canonical_json.read_text(encoding="utf-8"))
    experiment["baseline_reproduction"] = baseline_reproduction_check(
        experiment["variants"][_variant_name(BASELINE_HALF_LIFE_HOURS)],
        canonical_payload,
    )
    if not experiment["baseline_reproduction"]["pass"]:
        print(
            "Baseline reproduction failed; aborting entry-filter experiment. "
            f"deltas={experiment['baseline_reproduction']['metric_deltas']} "
            f"approved_delta={experiment['baseline_reproduction']['approved_pair_count_delta']}",
            file=sys.stderr,
        )
        return BASELINE_REPRODUCTION_EXIT_CODE
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "run_label": args.run_label,
        "bars_csv": str(args.bars_csv),
        "research_gate_json": str(args.research_gate_json),
        "canonical_json": str(args.canonical_json),
        "half_life_grid_hours": list(args.grid),
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
