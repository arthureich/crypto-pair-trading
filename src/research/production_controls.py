"""Production risk controls for the canonical TSM (TASK-DEPLOY-001, Phase 5).

Added by OPERATIONAL justification -- never because they improve a backtest. Three
layers:

1. Pre-trade LIMITS (reject the offending order, keep running): exposure caps,
   participation cap, min liquidity, gross/net/leverage/daily-turnover ceilings.
2. DATA-QUALITY flags for the failure modes (stale, non-positive price, incomplete
   bar, missing funding, price deviation, abnormal spread).
3. KILL SWITCHES (system-level halt): config-hash mismatch, margin below buffer,
   local-state divergence, and invalid data. The SAFE ACTION is to STOP OPENING
   NEW EXPOSURE -- NOT to auto-liquidate (auto-liquidation needs an explicit,
   separately-tested policy).

Idempotency: orders are keyed by the deterministic decision_id (Phase 2), so
re-processing after a restart never duplicates an order or its P&L.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "SAFE_ACTION",
    "ControlResult",
    "RiskPolicy",
    "data_quality_flags",
    "evaluate_order",
    "is_duplicate",
]

SAFE_ACTION = "HALT_NO_NEW_EXPOSURE"
_ABNORMAL_SPREAD_BPS = 100.0  # >1% spread on a liquid perp is abnormal
# Data-quality flags that are severe enough to trip a kill switch.
_CRITICAL_DATA_FLAGS = ("non_positive_price", "price_deviation", "stale_data")


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """A-priori conservative production limits (operational, not tuned)."""

    max_gross_exposure: float = 1.0  # unit-gross deploy
    max_net_exposure: float = 0.30
    max_leverage: float = 2.0
    max_exposure_per_symbol: float = 0.20
    max_participation: float = 0.10  # 10% ADV (Phase 4 prudent cap)
    min_liquidity_usd: float = 1_000_000.0  # trailing-24h dollar volume
    max_stale_data_seconds: float = 3_600.0
    max_price_deviation: float = 0.20  # |price/ref - 1| beyond this is "impossible"
    min_margin_buffer: float = 0.30
    max_daily_turnover: float = 2.0


@dataclass(frozen=True, slots=True)
class ControlResult:
    approved: bool
    violations: tuple[str, ...]  # order-level rejections (this order blocked)
    kill_switches: tuple[str, ...]  # system-level halts
    safe_action: str | None  # set iff a kill switch tripped


def data_quality_flags(
    *,
    bar_age_seconds: float,
    price: float,
    reference_price: float,
    is_complete_bar: bool,
    funding_present: bool,
    spread_bps: float | None,
    policy: RiskPolicy,
) -> tuple[str, ...]:
    """Classify the failure modes present in the current market data."""
    flags: list[str] = []
    if bar_age_seconds > policy.max_stale_data_seconds:
        flags.append("stale_data")
    if not (price > 0.0):
        flags.append("non_positive_price")
    if not is_complete_bar:
        flags.append("incomplete_bar")
    if not funding_present:
        flags.append("missing_funding")
    if reference_price > 0.0 and abs(price / reference_price - 1.0) > policy.max_price_deviation:
        flags.append("price_deviation")
    if spread_bps is not None and spread_bps > _ABNORMAL_SPREAD_BPS:
        flags.append("abnormal_spread")
    return tuple(flags)


def evaluate_order(
    *,
    symbol_exposure_after: float,
    gross_after: float,
    net_after: float,
    leverage_after: float,
    participation: float,
    symbol_dollar_volume: float,
    daily_turnover_after: float,
    margin_buffer: float,
    config_hash_ok: bool,
    exposure_matches_exchange: bool,
    data_flags: tuple[str, ...],
    policy: RiskPolicy,
) -> ControlResult:
    """Run all pre-trade limits + kill switches for one prospective order."""
    violations: list[str] = []
    if abs(symbol_exposure_after) > policy.max_exposure_per_symbol:
        violations.append("max_exposure_per_symbol")
    if participation > policy.max_participation:
        violations.append("max_participation")
    if symbol_dollar_volume < policy.min_liquidity_usd:
        violations.append("min_liquidity")
    if gross_after > policy.max_gross_exposure:
        violations.append("max_gross_exposure")
    if abs(net_after) > policy.max_net_exposure:
        violations.append("max_net_exposure")
    if leverage_after > policy.max_leverage:
        violations.append("max_leverage")
    if daily_turnover_after > policy.max_daily_turnover:
        violations.append("max_daily_turnover")

    kills: list[str] = []
    if not config_hash_ok:
        kills.append("config_hash_mismatch")
    if margin_buffer < policy.min_margin_buffer:
        kills.append("margin_below_buffer")
    if not exposure_matches_exchange:
        kills.append("local_state_divergence")
    kills.extend(f"data_invalid:{f}" for f in data_flags if f in _CRITICAL_DATA_FLAGS)

    approved = not violations and not kills
    return ControlResult(
        approved=approved,
        violations=tuple(violations),
        kill_switches=tuple(kills),
        safe_action=SAFE_ACTION if kills else None,
    )


def is_duplicate(decision_id: str, emitted_ids) -> bool:
    """Idempotency guard: an order whose decision_id was already emitted is a
    duplicate (re-processing after a restart must not re-send it)."""
    return decision_id in set(emitted_ids)
