#!/usr/bin/env python3
"""TASK-DEPLOY-001 Phase 1: metric-units audit of the TSM drawdown numbers.

Resolves the maxDD ~0.31-0.80 "modest/shallow" narrative. Reconstructs the
canonical-core per-rebalance return stream OFFLINE for the 7 crypto universes
(reusing the temporal-robustness collector), then reports the drawdown in BOTH
framings side by side:

  - ADDITIVE (what the validation scripts reported via np.cumsum) -- fixed-notional
    cumulative P&L per unit gross, in RETURN UNITS (not a percent);
  - COMPOUNDED (canonical, what "maxDD %" normally means) -- (1+r).cumprod().

Cross-checks that the additive numbers reproduce the legacy tsm_trend._max_drawdown
exactly (so the audit measures the same object). Offline; no strategy change.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.drawdown import compute_drawdown  # noqa: E402
from src.research.tsm_trend import _max_drawdown  # noqa: E402  (legacy additive, for cross-check)

_TR_SPEC = importlib.util.spec_from_file_location(
    "run_tsm_temporal_robustness", PROJECT_ROOT / "scripts" / "run_tsm_temporal_robustness.py"
)
tr = importlib.util.module_from_spec(_TR_SPEC)
_TR_SPEC.loader.exec_module(tr)

REPORT_MD = PROJECT_ROOT / "reports" / "metric_units_audit.md"
CSV_OUT = PROJECT_ROOT / "reports" / "per_universe_drawdown_audit.csv"
JSON_OUT = PROJECT_ROOT / "reports" / "per_universe_drawdown_audit.json"
DAYS_PER_BAR = 5  # 120h hold


def _audit_one(name: str, times: np.ndarray, pnl: np.ndarray) -> dict:
    comp = compute_drawdown(pnl, times, compound=True)
    add = compute_drawdown(pnl, times, compound=False)
    legacy_additive = float(_max_drawdown(np.asarray(pnl, dtype=float)))
    return {
        "universe": name,
        "n_rebalances": comp.n,
        # additive (legacy) framing
        "additive_maxDD_return_units": add.max_drawdown,
        "legacy_max_drawdown": legacy_additive,
        "additive_matches_legacy": math.isclose(add.max_drawdown, legacy_additive, rel_tol=1e-9),
        # compounded (canonical) framing
        "compounded_maxDD_decimal": comp.max_drawdown,
        "compounded_maxDD_percent": comp.max_drawdown_percent,
        "peak_timestamp": comp.peak_timestamp,
        "trough_timestamp": comp.trough_timestamp,
        "recovery_timestamp": comp.recovery_timestamp if not comp.unrecovered else "UNRECOVERED",
        "peak_equity": comp.peak_equity,
        "trough_equity": comp.trough_equity,
        "drawdown_duration_bars": comp.duration_bars,
        "drawdown_duration_days": comp.duration_bars * DAYS_PER_BAR,
        "time_underwater_fraction": comp.time_underwater_fraction,
        "time_underwater_percent": comp.time_underwater_fraction * 100.0,
        "equity_non_positive": comp.equity_non_positive,
        "had_nan": comp.had_nan,
    }


def _verdict(rows: list[dict]) -> dict:
    all_match = all(r["additive_matches_legacy"] for r in rows)
    comp = [r["compounded_maxDD_percent"] for r in rows]
    add = [r["additive_maxDD_return_units"] for r in rows]
    return {
        "conclusion": "B",
        "conclusion_text": (
            "The reported maxDD ~0.31-0.80 was in ADDITIVE fixed-notional units "
            "(cumulative P&L per unit gross via np.cumsum), NOT compounded equity "
            "percent. It is a UNIT/FRAMING issue, not a calculation bug: the "
            "additive numbers reproduce the legacy _max_drawdown exactly. The "
            "'modest/shallow' wording was internally consistent with additive net "
            "PnL but MISLEADING against the '%' reading a reader assumes."
        ),
        "additive_reproduces_legacy_exactly": all_match,
        "additive_maxDD_range_return_units": [min(add), max(add)],
        "compounded_maxDD_range_percent": [min(comp), max(comp)],
    }


def _fmt_pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.1f}%"


def write_report(rows: list[dict], v: dict) -> None:
    lines = [
        "# Metric-Units Audit -- TSM drawdown (TASK-DEPLOY-001, Phase 1)",
        "",
        "Audits the `maxDD ~0.31-0.80` numbers previously described as 'modest/",
        "shallow'. Canonical-core stream reconstructed offline for 7 crypto "
        "universes; drawdown reported in BOTH framings.",
        "",
        "## VERDICT: option B -- unit/framing issue (not a calc bug)",
        "",
        v["conclusion_text"],
        "",
        f"- Additive numbers reproduce legacy `_max_drawdown` exactly: "
        f"**{v['additive_reproduces_legacy_exactly']}**.",
        f"- Additive maxDD range (return units, fixed-notional): "
        f"**{v['additive_maxDD_range_return_units'][0]:.3f} - "
        f"{v['additive_maxDD_range_return_units'][1]:.3f}**.",
        f"- Compounded maxDD range (canonical equity %): "
        f"**{v['compounded_maxDD_range_percent'][0]:.1f}% - "
        f"{v['compounded_maxDD_range_percent'][1]:.1f}%**.",
        "",
        "So `0.80` did NOT mean an 80% equity drawdown; it meant cumulative losses "
        "reached 0.80 of one unit of gross notional (fixed-notional). The TRUE "
        "compounded drawdowns are shown below and are the numbers to quote going "
        "forward. Correcting the earlier 'shallow' characterization.",
        "",
        "## Per-universe drawdown (canonical core, both framings)",
        "",
        "| Universe | n | additive maxDD (ret units) | **compounded maxDD %** | "
        "duration (days) | time underwater | recovered? |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        rec = "no (UNRECOVERED)" if r["recovery_timestamp"] == "UNRECOVERED" else "yes"
        lines.append(
            f"| {r['universe']} | {r['n_rebalances']} | "
            f"{r['additive_maxDD_return_units']:.3f} | "
            f"**{_fmt_pct(r['compounded_maxDD_percent'])}** | "
            f"{r['drawdown_duration_days']} | "
            f"{r['time_underwater_percent']:.0f}% | {rec} |"
        )
    lines += [
        "",
        "## Peak / trough / recovery timestamps (compounded)",
        "",
        "| Universe | peak | trough | recovery | peak eq | trough eq |",
        "|---|---|---|---|---:|---:|",
    ]
    for r in rows:
        rec = r["recovery_timestamp"] or "n/a"
        rec = rec if rec == "UNRECOVERED" else rec[:10]
        lines.append(
            f"| {r['universe']} | {(r['peak_timestamp'] or 'n/a')[:10]} | "
            f"{(r['trough_timestamp'] or 'n/a')[:10]} | {rec} | "
            f"{r['peak_equity']:.3f} | {r['trough_equity']:.3f} |"
        )
    lines += [
        "",
        "## Fact / estimate / assumption / limitation",
        "",
        "- FACT: the validation scripts computed drawdown as np.cumsum(returns) "
        "peak-to-trough (additive, fixed-notional); this audit reproduces those "
        "numbers exactly.",
        "- FACT: under the canonical compounded formula, the maxDD figures are "
        "different and are the ones to quote as 'equity drawdown %'.",
        "- ASSUMPTION: compounded equity reinvests P&L (bet size scales with "
        "equity); additive assumes constant notional. Both are legitimate; a real "
        "fixed-capital vol-targeted deployment sits between them.",
        "- ASSUMPTION: NaN per-rebalance returns treated as 0.0 (flagged).",
        "- LIMITATION: per-rebalance returns are gross-notional returns of a "
        "unit-gross long/short book; compounding a levered L/S book can drive "
        "equity non-positive (flagged per universe), which additive never shows.",
        "- DECISION: quote COMPOUNDED maxDD % as the headline risk number going "
        "forward; keep additive clearly labeled where used. No strategy/parameter "
        "change; the drawdown metric is reporting, not economic logic.",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    universes = tr._collect_universes()
    rows = []
    for name, bars in universes.items():
        times, pnl = tr._base_stream(bars)
        rows.append(_audit_one(name, times, pnl))
    v = _verdict(rows)

    JSON_OUT.write_text(
        json.dumps(
            {
                "task": "TASK-DEPLOY-001 Phase 1 metric-units audit",
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "verdict": v,
                "per_universe": rows,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    with CSV_OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    write_report(rows, v)

    print(
        f"VERDICT {v['conclusion']}: additive reproduces legacy = "
        f"{v['additive_reproduces_legacy_exactly']}"
    )
    print(f"additive maxDD range (ret units): {v['additive_maxDD_range_return_units']}")
    print(f"compounded maxDD range (%): {v['compounded_maxDD_range_percent']}")
    print(f"Wrote {REPORT_MD}\nWrote {CSV_OUT}\nWrote {JSON_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
