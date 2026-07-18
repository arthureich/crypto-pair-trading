"""Immutable append-only forward ledger for the canonical TSM (TASK-DEPLOY-001, Phase 2).

Records each rebalance DECISION before its simulated execution and never rewrites
the past. Guarantees:

- deterministic `decision_id` (a decision is identified by config-hash + exchange +
  symbol + signal timestamp, so replaying the same day is idempotent);
- append-only JSONL: a decision_id already on disk with an IDENTICAL payload is a
  no-op (idempotent replay); with a DIFFERENT payload it RAISES -- the past is
  never silently overwritten;
- corrections are new events (`event_type="correction"`) that REFERENCE the
  original decision_id and carry a reason; the original line is left untouched.

Three P&L streams are carried on every event, never conflated:
  A theoretical   -- strategy return net of the ORIGINALLY-declared cost only;
  B executable    -- net of realistic frictions (spread, slippage, fee, funding,
                     rounding, unfilled, delay) from the execution model;
  C conservative  -- the SAME signals under a smaller risk budget + production
                     controls (a DEPLOYMENT POLICY, not a new strategy).

This module is infrastructure: it stores and accounts, it does not define or
change any strategy signal, weight, or economic parameter.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

__all__ = [
    "DecisionEvent",
    "ForwardLedger",
    "LedgerImmutabilityError",
    "ThreeStreamPnl",
    "make_decision_id",
    "three_stream_pnl",
]


class LedgerImmutabilityError(RuntimeError):
    """Raised when an append would overwrite an existing decision with new content."""


def make_decision_id(
    strategy_config_hash: str, exchange: str, symbol: str, signal_timestamp_ms: int
) -> str:
    """Deterministic id: same (config, venue, symbol, signal time) -> same id."""
    key = f"{strategy_config_hash}|{exchange}|{symbol}|{int(signal_timestamp_ms)}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True, slots=True)
class ThreeStreamPnl:
    theoretical: float  # stream A
    executable: float  # stream B
    conservative: float  # stream C


def three_stream_pnl(
    gross_pnl: float,
    *,
    declared_cost: float,
    execution_frictions: float,
    conservative_risk_fraction: float,
    conservative_extra_drag: float = 0.0,
) -> ThreeStreamPnl:
    """Compute the three P&L streams from a gross return and friction inputs.

    A = gross - declared_cost (the originally-pre-registered 6bps/leg cost).
    B = gross - execution_frictions (spread+slippage+realistic fee+funding+
        rounding+unfilled from the execution model; supersedes declared_cost).
    C = risk_fraction * B - conservative_extra_drag (same signals, smaller risk
        budget; controls add a small drag). risk_fraction in (0, 1].
    """
    if not 0.0 < conservative_risk_fraction <= 1.0:
        raise ValueError("conservative_risk_fraction must be in (0, 1]")
    a = gross_pnl - declared_cost
    b = gross_pnl - execution_frictions
    c = conservative_risk_fraction * b - conservative_extra_drag
    return ThreeStreamPnl(theoretical=a, executable=b, conservative=c)


@dataclass(frozen=True, slots=True)
class DecisionEvent:
    # --- identity / provenance ---
    decision_id: str
    strategy_config_hash: str
    software_commit: str
    event_type: str = "decision"  # "decision" | "correction"
    corrects_decision_id: str | None = None
    correction_reason: str | None = None
    # --- venue / instrument ---
    exchange: str = ""
    symbol: str = ""
    # --- timing (UTC ms) ---
    signal_timestamp_ms: int = 0
    data_available_until_ms: int = 0
    decision_timestamp_ms: int = 0
    scheduled_execution_timestamp_ms: int = 0
    # --- sizing ---
    side: str = "flat"  # "long" | "short" | "flat"
    target_weight: float = 0.0
    previous_weight: float = 0.0
    target_notional: float = 0.0
    # --- market / fills ---
    reference_price: float = 0.0
    market_bid: float | None = None
    market_ask: float | None = None
    mid_price: float | None = None
    simulated_fill_price: float = 0.0
    executed_quantity: float = 0.0
    unfilled_quantity: float = 0.0
    # --- frictions & three P&L streams ---
    fee: float = 0.0
    slippage: float = 0.0
    funding: float = 0.0
    gross_pnl: float = 0.0
    net_pnl_theoretical: float = 0.0  # A
    net_pnl_executable: float = 0.0  # B
    net_pnl_conservative: float = 0.0  # C
    # --- flags ---
    data_quality_flags: tuple[str, ...] = field(default_factory=tuple)
    execution_flags: tuple[str, ...] = field(default_factory=tuple)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


class ForwardLedger:
    """Append-only JSONL ledger. One event per line; never edits or deletes."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def _index(self) -> dict[str, dict]:
        return {e["decision_id"]: e for e in self.read_all() if e["event_type"] == "decision"}

    def append(self, event: DecisionEvent) -> bool:
        """Append a decision. Returns True if written, False if an identical
        decision already existed (idempotent replay). Raises if the same
        decision_id exists with DIFFERENT content (use append_correction)."""
        if event.event_type != "decision":
            raise LedgerImmutabilityError("use append_correction for corrections")
        existing = self._index().get(event.decision_id)
        if existing is not None:
            if existing == json.loads(event.to_json()):
                return False  # idempotent no-op
            raise LedgerImmutabilityError(
                f"decision {event.decision_id} already recorded with different content; "
                "the past is append-only -- use append_correction"
            )
        self._write_line(event)
        return True

    def append_correction(self, corrected: DecisionEvent, *, reason: str) -> str:
        """Record a correction as a NEW event referencing the original; the
        original line is never modified. Returns the correction event id."""
        original_id = corrected.corrects_decision_id
        if not original_id or original_id not in self._index():
            raise LedgerImmutabilityError(
                "correction must reference an existing original decision_id"
            )
        corr_id = make_decision_id(
            corrected.strategy_config_hash + "|correction",
            corrected.exchange,
            corrected.symbol,
            corrected.signal_timestamp_ms,
        )
        event = DecisionEvent(
            **{
                **asdict(corrected),
                "decision_id": corr_id,
                "event_type": "correction",
                "correction_reason": reason,
                # tuples survive asdict as lists; restore
                "data_quality_flags": tuple(corrected.data_quality_flags),
                "execution_flags": tuple(corrected.execution_flags),
            }
        )
        self._write_line(event)
        return corr_id

    def _write_line(self, event: DecisionEvent) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(event.to_json() + "\n")
