"""Forward-track monitoring: horizons, metrics, alerts (TASK-DEPLOY-001, Phase 7).

Reads the immutable forward ledger (Phase 2/3) and turns it into a monitoring
view. Two firm principles:

- READING HORIZONS gate interpretation so a handful of rebalances is never read as
  a verdict: 1mo = operational diagnostic only; 3mo preliminary; 6mo initial;
  12mo first relevant; 18-24mo more confident. These are guards against premature
  conclusions, not statistical guarantees.
- ALERTS only ALERT -- they never modify the strategy. Tripping an alert means a
  human looks; the frozen economic parameters are untouched.

Pure and stdlib+numpy only. Metrics reuse the canonical compounded drawdown.
"""

from __future__ import annotations

import math

import numpy as np

from src.research.drawdown import compute_drawdown

__all__ = ["AlertThresholds", "evaluate_alerts", "reading_horizon", "stream_metrics"]

_ANN = math.sqrt(24 * 365 / 120)  # 5d rebalance, same as the project
_REBALANCES_PER_MONTH = 6.0  # ~30/5


def reading_horizon(n_rebalances: int) -> dict:
    """Map accrued OOS rebalances to a reading level (guard, not a guarantee)."""
    months = n_rebalances / _REBALANCES_PER_MONTH
    if months < 3:  # noqa: PLR2004
        level, verdict = "operational_diagnostic_only", False
    elif months < 6:  # noqa: PLR2004
        level, verdict = "preliminary", False
    elif months < 12:  # noqa: PLR2004
        level, verdict = "initial_evidence", False
    elif months < 18:  # noqa: PLR2004
        level, verdict = "first_relevant_assessment", True
    else:
        level, verdict = "more_confident_assessment", True
    return {"n_rebalances": n_rebalances, "approx_months": months,
            "reading_level": level, "verdict_horizon_reached": verdict}  # fmt: skip


def stream_metrics(returns) -> dict:
    """Per-period-return metrics for one forward stream (compounded DD)."""
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if r.size < 2:  # noqa: PLR2004
        return {"n": int(r.size), "sharpe": None, "sortino": None, "net_return": float(r.sum())}
    mu, sd = r.mean(), r.std(ddof=1)
    downside = r[r < 0]
    dstd = downside.std(ddof=1) if downside.size > 1 else 0.0
    dd = compute_drawdown(r, compound=True)
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    return {
        "n": int(r.size),
        "ann_return": float(mu * (_ANN**2)),  # per-period mean -> annual (sum-of-returns proxy)
        "ann_vol": float(sd * _ANN),
        "sharpe": float(mu / sd * _ANN) if sd > 1e-12 else None,  # noqa: PLR2004
        "sortino": float(mu / dstd * _ANN) if dstd > 1e-12 else None,  # noqa: PLR2004
        "max_drawdown_compounded_pct": dd.max_drawdown_percent,
        "drawdown_duration_bars": dd.duration_bars,
        "time_underwater_pct": dd.time_underwater_fraction * 100.0,
        "profit_factor": float(pos / neg) if neg > 0 else None,
        "hit_rate": float(np.mean(r > 0)),
        "net_return": float(r.sum()),
    }


class AlertThresholds:
    """A-priori alert thresholds (from committed dev/history). Alerts only alert."""

    exec_shortfall_sharpe_budget = 0.10  # |theoretical - executable| Sharpe gap
    historical_max_drawdown_pct = 58.0  # Phase 1 worst compounded maxDD
    historical_hit_rate = 0.50
    hit_rate_drop_margin = 0.10  # alert if hit_rate < historical - margin
    breakeven_cost_bps = 142.0  # FC-II-007 breakeven
    single_rebalance_concentration = 0.60  # one rebalance > 60% of net


def evaluate_alerts(
    *,
    theoretical: dict,
    executable: dict,
    effective_cost_bps: float | None,
    max_single_rebalance_share: float | None,
    config_hash_ok: bool,
    data_failure_count: int,
    exposure_matches_config: bool,
    thresholds: AlertThresholds | None = None,
) -> tuple[str, ...]:
    """Return the tripped alerts (never modifies anything)."""
    t = thresholds or AlertThresholds()
    alerts: list[str] = []
    ts, es = theoretical.get("sharpe"), executable.get("sharpe")
    if ts is not None and es is not None and (ts - es) > t.exec_shortfall_sharpe_budget:
        alerts.append("execution_shortfall_exceeds_budget")
    if effective_cost_bps is not None and effective_cost_bps > t.breakeven_cost_bps:
        alerts.append("cost_above_breakeven")
    dd = executable.get("max_drawdown_compounded_pct")
    if dd is not None and dd > t.historical_max_drawdown_pct:
        alerts.append("drawdown_beyond_historical")
    hr = executable.get("hit_rate")
    if hr is not None and hr < (t.historical_hit_rate - t.hit_rate_drop_margin):
        alerts.append("hit_rate_persistent_drop")
    if (
        max_single_rebalance_share is not None
        and max_single_rebalance_share > t.single_rebalance_concentration
    ):
        alerts.append("pnl_concentration")
    if data_failure_count > 0:
        alerts.append("recurring_data_failures")
    if not config_hash_ok:
        alerts.append("config_hash_mismatch")
    if not exposure_matches_config:
        alerts.append("exposure_differs_from_frozen_config")
    return tuple(alerts)
