#!/usr/bin/env python3
"""TASK-DEPLOY-001 Phase 7: forward monitoring report over the immutable ledger.

Reads the append-only forward ledger (Phase 2/3), computes per-stream metrics
(theoretical / executable / conservative), classifies the reading horizon so a
short track is never read as a verdict, and evaluates alert criteria. Alerts only
ALERT -- the frozen strategy is never modified here. Buy-hold / combined-caveated
reference lines are read from the existing paper-forward artifact when present.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.forward_ledger import ForwardLedger  # noqa: E402
from src.research.forward_monitor import (  # noqa: E402
    evaluate_alerts,
    reading_horizon,
    stream_metrics,
)

LEDGER_PATH = PROJECT_ROOT / "artifacts/tsm/forward/canonical_ledger.jsonl"
CANON = PROJECT_ROOT / "artifacts/tsm/canonical-config.json"
PAPER_FWD = PROJECT_ROOT / "data/research/binance_public/cost_pilot/tsm_paper_forward.json"
REPORT_MD = PROJECT_ROOT / "reports/forward_monitor.md"
JSON_OUT = PROJECT_ROOT / "data/research/binance_public/cost_pilot/forward_monitor.json"


def _max_share(net: np.ndarray) -> float | None:
    total = float(net.sum())
    return float(net.max() / total) if total > 0 and net.size else None


def main() -> int:
    ledger = ForwardLedger(LEDGER_PATH)
    events = [e for e in ledger.read_all() if e["event_type"] == "decision"]
    events.sort(key=lambda e: e["signal_timestamp_ms"])
    n = len(events)
    canon_hash = json.loads(CANON.read_text(encoding="utf-8"))["config_hash"]

    if n == 0:
        REPORT_MD.write_text(
            "# Forward Monitor (TASK-DEPLOY-001, Phase 7)\n\n"
            "No forward events in the ledger yet. Run the execution report "
            "(`run_forward_execution_report.py`) as OOS data accrues.\n",
            encoding="utf-8",
        )
        print("No ledger events yet.")
        return 0

    theo = np.array([e["net_pnl_theoretical"] for e in events], dtype=float)
    exe = np.array([e["net_pnl_executable"] for e in events], dtype=float)
    cons = np.array([e["net_pnl_conservative"] for e in events], dtype=float)
    m_theo, m_exe, m_cons = stream_metrics(theo), stream_metrics(exe), stream_metrics(cons)

    config_ok = all(e["strategy_config_hash"] == canon_hash for e in events)
    data_failures = sum(1 for e in events if e.get("data_quality_flags"))
    horizon = reading_horizon(n)

    alerts = evaluate_alerts(
        theoretical=m_theo,
        executable=m_exe,
        effective_cost_bps=None,  # computed in the execution report, not here
        max_single_rebalance_share=_max_share(exe),
        config_hash_ok=config_ok,
        data_failure_count=data_failures,
        exposure_matches_config=True,  # paper track; no live exchange state
        thresholds=None,
    )

    reference = {}
    if PAPER_FWD.exists():
        pf = json.loads(PAPER_FWD.read_text(encoding="utf-8"))
        reference = {
            "buy_hold": pf.get("buy_hold_baseline"),
            "combined_caveated": pf.get("combined_primary"),
        }

    payload = {
        "task": "TASK-DEPLOY-001 Phase 7 forward monitor",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "config_hash": canon_hash,
        "config_hash_ok": config_ok,
        "reading_horizon": horizon,
        "streams": {
            "theoretical": m_theo,
            "executable": m_exe,
            "conservative": m_cons,
            "cash": {"n": n, "net_return": 0.0, "sharpe": 0.0},
        },  # fmt: skip
        "reference_lines": reference,
        "data_failure_events": data_failures,
        "alerts": list(alerts),
    }
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _write_report(payload)
    print(
        f"Forward monitor: {n} events, horizon={horizon['reading_level']} "
        f"(verdict={horizon['verdict_horizon_reached']}), alerts={list(alerts) or 'none'}"
    )
    print(f"Wrote {REPORT_MD}\nWrote {JSON_OUT}")
    return 0


def _f(x, d: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{d}f}"


def _write_report(p: dict) -> None:
    h = p["reading_horizon"]
    s = p["streams"]
    lines = [
        "# Forward Monitor -- canonical TSM (TASK-DEPLOY-001, Phase 7)",
        "",
        "Reads the immutable forward ledger (Phase 2/3). Alerts only ALERT -- the "
        "frozen strategy is never modified here. Reading horizons gate "
        "interpretation so a short track is not read as a verdict.",
        "",
        f"## Reading horizon: **{h['reading_level']}** "
        f"({h['n_rebalances']} rebalances ~ {h['approx_months']:.1f} months)",
        "",
        f"Verdict horizon reached: **{h['verdict_horizon_reached']}**. "
        "1mo = operational diagnostic; 3mo preliminary; 6mo initial; 12mo first "
        "relevant; 18-24mo more confident. **A short track is NOISE, not a verdict.**",
        "",
        "## Streams (accrued OOS)",
        "",
        "| Stream | n | Sharpe | Sortino | maxDD % | hit rate | PF | net |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("theoretical", "executable", "conservative"):
        m = s[name]
        lines.append(
            f"| {name} | {m['n']} | {_f(m.get('sharpe'))} | {_f(m.get('sortino'))} | "
            f"{_f(m.get('max_drawdown_compounded_pct'), 1)} | {_f(m.get('hit_rate'), 2)} | "
            f"{_f(m.get('profit_factor'), 2)} | {_f(m.get('net_return'), 4)} |"
        )
    lines.append(f"| cash | {s['cash']['n']} | 0.000 | -- | 0.0 | -- | -- | 0.0000 |")
    ref = p.get("reference_lines") or {}
    if ref.get("buy_hold"):
        bh = ref["buy_hold"]
        lines.append(
            f"| buy-hold (ref) | {bh.get('n', '?')} | {_f(bh.get('sharpe'))} | -- | -- | "
            f"-- | -- | {_f(bh.get('net'), 4)} |"
        )
    lines += [
        "",
        "## Alerts (alert only -- NEVER auto-modify the strategy)",
        "",
    ]
    if p["alerts"]:
        lines += [f"- **{a}**" for a in p["alerts"]]
    else:
        lines.append("- none tripped.")
    lines += [
        "",
        "Alert criteria: execution shortfall > budget; cost above breakeven; "
        "drawdown beyond historical; hit-rate persistent drop; PnL concentration; "
        "recurring data failures; config-hash mismatch; exposure != frozen config. "
        "A tripped alert means a HUMAN reviews -- the frozen economic parameters "
        "are never changed automatically.",
        "",
        "## Reading (fact / limitation)",
        "",
        f"- FACT: config-hash matches the frozen canonical ({p['config_hash_ok']}); "
        f"{p['data_failure_events']} data-failure events in the ledger.",
        "- LIMITATION: the OOS track is short (well below any verdict horizon); all "
        "metrics here are operational diagnostics, NOT evidence of the edge. The "
        "track accrues as each new month is downloaded and the execution report "
        "appends to the ledger. Re-run this monitor after each append.",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
