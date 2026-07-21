"""Cash-and-carry delta-neutral mechanics (TASK-BASIS-001, ADR-0034).

Buy spot + short the same-asset dated future at entry, hold to expiry. The key
economic fact this module encodes and tests: the position's return is LOCKED at
entry = the entry basis, and is INDEPENDENT of the price path (delta-neutral). The
future converges to spot at expiry, so:

    spot leg P&L = S_T - S0
    short fut P&L = F0 - S_T
    total        = F0 - S0  = the entry basis   (S_T cancels)

Profit comes from convergence of a KNOWN entry basis, not from forecasting price.
Pure/stdlib+numpy; no network, no strategy state. Costs are conservative inputs.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "annualize_return",
    "annualized_basis",
    "basis_fraction",
    "capital_employed_return",
    "clears_deploy_hurdle",
    "funding_carry_return",
    "locked_carry_return",
    "net_carry_return",
    "worst_adverse_mtm",
]


def basis_fraction(spot: float, fut: float) -> float:
    """(future - spot) / spot -- the raw basis as a fraction of spot."""
    if spot <= 0:
        raise ValueError("spot must be positive")
    return (fut - spot) / spot


def annualized_basis(spot: float, fut: float, days_to_expiry: float) -> float:
    """Entry basis expressed as a simple annualized rate (APR)."""
    if days_to_expiry <= 0:
        raise ValueError("days_to_expiry must be positive")
    return basis_fraction(spot, fut) * (365.0 / days_to_expiry)


def locked_carry_return(entry_spot: float, entry_fut: float, settle_price: float) -> float:
    """Realized gross return (on spot notional) of buy-spot + short-fut held to
    settlement. Equals the entry basis fraction for ANY settle_price (delta-
    neutral); `settle_price` is accepted only to demonstrate path-independence."""
    spot_pnl = settle_price - entry_spot
    fut_pnl = entry_fut - settle_price
    return (spot_pnl + fut_pnl) / entry_spot


def net_carry_return(
    entry_spot: float,
    entry_fut: float,
    *,
    cost_bps_per_leg: float,
    n_legs_roundtrip: int = 4,
) -> float:
    """Locked gross basis return minus conservative execution cost.

    n_legs_roundtrip default 4 = enter both legs (spot buy + fut short) and exit
    both (spot sell + fut buy-to-close / settle) at cost_bps_per_leg each.
    """
    gross = basis_fraction(entry_spot, entry_fut)
    cost = n_legs_roundtrip * cost_bps_per_leg / 10_000.0
    return gross - cost


def worst_adverse_mtm(entry_spot: float, entry_fut: float, spot_path, fut_path) -> float:
    """Worst (most negative) mark-to-market of the position before expiry, as a
    fraction of spot notional. MTM_t = (basis0 - basis_t)/entry_spot; the basis
    WIDENING (basis_t > basis0) is the adverse move that marks the trade down."""
    s = np.asarray(spot_path, dtype=float)
    f = np.asarray(fut_path, dtype=float)
    basis0 = entry_fut - entry_spot
    mtm = (basis0 - (f - s)) / entry_spot  # position value change vs entry
    return float(mtm.min()) if mtm.size else 0.0


def funding_carry_return(
    funding_rates, *, cost_bps_per_leg: float, n_legs_roundtrip: int = 4
) -> float:
    """Gross return of long-spot + short-perp (delta ~0), net of round-trip cost.

    The SHORT perp RECEIVES funding when the rate is positive, so the funding P&L
    (as a fraction of notional) is the SUM of the funding rates over the hold; the
    long spot pays no funding. The spot-perp basis drift is second-order over a
    continuous hold and is handled separately by the caller. Cost is a one-time
    round trip (enter + exit both legs)."""
    total_funding = float(np.asarray(funding_rates, dtype=float).sum())
    cost = n_legs_roundtrip * cost_bps_per_leg / 10_000.0
    return total_funding - cost


def annualize_return(total_return: float, days_held: float) -> float:
    """Simple annualization of a period return."""
    if days_held <= 0:
        raise ValueError("days_held must be positive")
    return total_return * (365.0 / days_held)


def clears_deploy_hurdle(
    net_apr_on_capital: float,
    hurdle_apr: float,
    n_settlements: int,
    *,
    min_settlements: int,
) -> bool:
    """Deploy rule: net forward APR on TOTAL capital must exceed the operational
    hurdle AND the window must have enough settlements to be a valid read. The
    hurdle is set a-priori (opportunity + counterparty + custody + fees + funding-
    inversion safety + two-leg cost) -- NOT chosen from the data to make it pass."""
    return net_apr_on_capital > hurdle_apr and n_settlements >= min_settlements


def capital_employed_return(net_return_on_spot: float, *, margin_fraction: float) -> dict:
    """Convert the return-on-spot-notional to return on total capital employed and
    on margin. Capital employed = spot notional (1.0) + margin for the short
    (margin_fraction of the 1.0 futures notional). No leverage beyond the posted
    margin is assumed."""
    if margin_fraction <= 0:
        raise ValueError("margin_fraction must be positive")
    capital = 1.0 + margin_fraction
    return {
        "return_on_capital_employed": net_return_on_spot / capital,
        "return_on_margin": net_return_on_spot / margin_fraction,
        "capital_employed_per_unit_spot": capital,
    }
