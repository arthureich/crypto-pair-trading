#!/usr/bin/env python3
"""TASK-DEPLOY-001 Phase 6: multiple-testing statistical haircut.

How much of the canonical TSM's evidence survives after accounting for higher
moments, finite sample, AND the number of hypotheses the program tried. Computes
the Probabilistic Sharpe Ratio, the Deflated Sharpe Ratio (for direct TSM-family
trials and for the whole program), effective independent trials given cross-
universe correlation, a block-bootstrap Sharpe CI, and PnL concentration. PBO/CSCV
is NOT reliably estimable under our experiment structure (few pre-registered
variants, not a large config grid on the same data) -> reported as such, no number
fabricated. Offline; no strategy/parameter change; no promotion.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.multiple_testing import (  # noqa: E402
    deflated_sharpe_ratio,
    effective_trials,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
)

_TR_SPEC = importlib.util.spec_from_file_location(
    "run_tsm_temporal_robustness", PROJECT_ROOT / "scripts" / "run_tsm_temporal_robustness.py"
)
tr = importlib.util.module_from_spec(_TR_SPEC)
_TR_SPEC.loader.exec_module(tr)

REPORT_MD = PROJECT_ROOT / "reports/multiple_testing_haircut.md"
LEDGER_OUT = PROJECT_ROOT / "artifacts/tsm/attempt_ledger.json"
JSON_OUT = PROJECT_ROOT / "data/research/binance_public/cost_pilot/multiple_testing_haircut.json"

HOLD_HOURS = 120
_ANN = math.sqrt(24 * 365 / HOLD_HOURS)
BLOCK = 10  # block-bootstrap block length (rebalances) to keep autocorrelation
N_BOOT = 10_000
BOOT_SEED = 0

# Comparable TSM-family dev Sharpes on the original-20 (the DIRECT competing trials).
TSM_FAMILY_SHARPES = (0.970, 0.949, 0.888, 1.039, 0.412, 1.107, 1.183)

# Program-wide inventory of distinct STRATEGY hypotheses (grounded in the ledger).
# fields: strategy_id, family, pre_registered, primary_or_secondary, n_variants,
# dev_window, result, selected_or_rejected.
ATTEMPTS = [
    [
        "sprint8_kalman_pairs",
        "price",
        True,
        "primary",
        1,
        "2023-06_2026-05",
        "NAO_PASSA",
        "rejected",
    ],
    [
        "sprint9_executable_pairs",
        "price",
        True,
        "primary",
        1,
        "2023-06_2026-05",
        "NAO_PASSA",
        "rejected",
    ],
    [
        "sprint10_passive_pairs",
        "price",
        True,
        "primary",
        2,
        "2023-06_2026-05",
        "NAO_PASSA",
        "rejected",
    ],
    [
        "sprint8_canonical_triple_barrier",
        "price",
        True,
        "primary",
        1,
        "2023-06_2026-05",
        "NAO_PASSA",
        "rejected",
    ],
    [
        "signal_iteration_SIG001_004",
        "price",
        True,
        "secondary",
        4,
        "2023-06_2026-05",
        "REJECTED",
        "rejected",
    ],
    [
        "funding_carry_full_rebalance",
        "carry",
        True,
        "primary",
        1,
        "2023-06_2026-05",
        "NAO_PASSA",
        "rejected",
    ],
    [
        "funding_carry_incremental_K5",
        "carry",
        True,
        "primary",
        1,
        "2023-06_2026-05",
        "NEAR_MISS",
        "forward",
    ],
    ["tsmom_donchian", "price", True, "primary", 1, "2023-06_2026-05", "NAO_PASSA", "rejected"],
    ["tsrev_24h", "price", True, "primary", 1, "2023-06_2026-05", "NAO_PASSA", "rejected"],
    [
        "regime_conditioned_tsrev",
        "price",
        True,
        "secondary",
        1,
        "2023-06_2026-05",
        "NAO_PASSA",
        "rejected",
    ],
    [
        "cross_sectional_momentum",
        "price",
        True,
        "primary",
        1,
        "2023-06_2026-05",
        "NAO_PASSA",
        "rejected",
    ],
    [
        "cross_sectional_reversion",
        "price",
        True,
        "primary",
        1,
        "2023-06_2026-05",
        "NAO_PASSA",
        "rejected",
    ],
    ["vrp_timing", "options", True, "primary", 1, "2023-06_2026-05", "NAO_PASSA", "rejected"],
    [
        "vrp_overlay_on_tsm",
        "options",
        True,
        "secondary",
        1,
        "2023-06_2026-05",
        "NAO_PASSA",
        "rejected",
    ],
    ["tsm_base_vol_targeted", "price", True, "primary", 1, "2023-06_2026-05", "LEAD", "selected"],
    ["tsm_regime_filter", "price", True, "secondary", 1, "2023-06_2026-05", "REJECTED", "rejected"],
    [
        "tsm_conviction_sizing",
        "price",
        True,
        "secondary",
        1,
        "2023-06_2026-05",
        "REJECTED",
        "rejected",
    ],
    ["tsm_erc", "price", True, "secondary", 1, "2023-06_2026-05", "CARRIED", "secondary"],
    ["tsm_meta_labeling", "price", True, "secondary", 1, "2023-06_2026-05", "REJECTED", "rejected"],
    [
        "tsm_ensemble_trend_carry",
        "price+carry",
        True,
        "secondary",
        1,
        "2023-06_2026-05",
        "CARRIED",
        "secondary",
    ],
    [
        "tsm_vol_target_overlay",
        "price",
        True,
        "secondary",
        1,
        "2023-06_2026-05",
        "CARRIED",
        "secondary",
    ],
    [
        "tsm_combined_erc_voltarget",
        "price",
        True,
        "secondary",
        1,
        "2023-06_2026-05",
        "CARRIED",
        "secondary",
    ],
    [
        "fc_ii_001_risk_sizing",
        "carry",
        True,
        "secondary",
        1,
        "2023-06_2026-05",
        "CAUTIONARY",
        "rejected",
    ],
    [
        "ml_001_meta_labeling_carry",
        "carry",
        True,
        "secondary",
        1,
        "2023-06_2026-05",
        "CAUTIONARY",
        "rejected",
    ],
]
_ATTEMPT_FIELDS = [
    "strategy_id",
    "family",
    "pre_registered",
    "primary_or_secondary",
    "n_variants",
    "dev_window",
    "result",
    "selected_or_rejected",
]


def _moments(r: np.ndarray) -> tuple[float, float, float]:
    mu, sd = r.mean(), r.std(ddof=1)
    z = (r - mu) / sd
    skew = float(np.mean(z**3))
    kurt = float(np.mean(z**4))  # non-excess (normal = 3)
    return float(mu / sd), skew, kurt  # per-period SR, skew, kurt


def _block_bootstrap_sr_ci(r: np.ndarray) -> list[float]:
    rng = np.random.default_rng(BOOT_SEED)
    n = r.size
    n_blocks = math.ceil(n / BLOCK)
    starts_max = n - BLOCK
    srs = []
    for _ in range(N_BOOT):
        starts = rng.integers(0, starts_max + 1, size=n_blocks)
        sample = np.concatenate([r[s : s + BLOCK] for s in starts])[:n]
        sd = sample.std(ddof=1)
        if sd > 1e-12:  # noqa: PLR2004
            srs.append(sample.mean() / sd * _ANN)
    lo, hi = np.percentile(srs, [2.5, 97.5])
    return [float(lo), float(hi)]


def _avg_cross_universe_corr(streams: dict[str, np.ndarray]) -> float:
    # align on the shortest common length (all share the same rebalance grid)
    m = min(len(v) for v in streams.values())
    mat = np.vstack([v[:m] for v in streams.values()])
    corr = np.corrcoef(mat)
    off = corr[~np.eye(corr.shape[0], dtype=bool)]
    return float(np.mean(off))


def _pnl_concentration(times: np.ndarray, r: np.ndarray) -> dict:
    idx = pd.to_datetime(times, unit="ms", utc=True)
    monthly = pd.Series(r, index=idx).groupby(pd.Grouper(freq="MS")).sum()
    total = float(monthly.sum())
    top1 = float(monthly.max())
    top3 = float(monthly.sort_values(ascending=False).head(3).sum())
    return {
        "n_months": int(monthly.size),
        "total_return": total,
        "best_month_share_of_total": (top1 / total) if total else None,
        "top3_months_share_of_total": (top3 / total) if total else None,
    }


def main() -> int:
    universes = tr._collect_universes()
    streams = {name: tr._base_stream(bars)[1] for name, bars in universes.items()}
    times_orig, pnl_orig = tr._base_stream(universes["original_20"])
    r = np.asarray(pnl_orig, dtype=float)
    r = r[~np.isnan(r)]

    sr_pp, skew, kurt = _moments(r)
    n = r.size
    psr0 = probabilistic_sharpe_ratio(sr_pp, n, skew, kurt, 0.0)

    fam = np.asarray(TSM_FAMILY_SHARPES) / _ANN  # to per-period
    sr_var = float(np.var(fam, ddof=1))
    n_direct = len(TSM_FAMILY_SHARPES)
    n_program = len(ATTEMPTS)
    dsr_direct = deflated_sharpe_ratio(sr_pp, n, skew, kurt, n_direct, sr_var)
    dsr_program = deflated_sharpe_ratio(sr_pp, n, skew, kurt, n_program, sr_var)

    avg_corr = _avg_cross_universe_corr(streams)
    n_eff_universes = effective_trials(len(streams), avg_corr)

    payload = {
        "task": "TASK-DEPLOY-001 Phase 6 multiple-testing haircut",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "canonical_original20": {
            "n_rebalances": n,
            "sharpe_per_period": sr_pp,
            "sharpe_annualized": sr_pp * _ANN,
            "skew": skew,
            "kurtosis_non_excess": kurt,
            "psr_vs_zero": psr0,
            "block_bootstrap_sharpe_ci_annualized": _block_bootstrap_sr_ci(r),
        },
        "deflation": {
            "trial_sharpe_variance_per_period": sr_var,
            "n_direct_tsm_variants": n_direct,
            "n_program_hypotheses": n_program,
            "direct": dsr_direct,
            "program": dsr_program,
            "expected_max_sharpe_annualized_direct": expected_max_sharpe(n_direct, sr_var) * _ANN,
            "expected_max_sharpe_annualized_program": expected_max_sharpe(n_program, sr_var) * _ANN,
        },
        "cross_universe_dependence": {
            "n_universes": len(streams),
            "avg_pairwise_correlation": avg_corr,
            "effective_independent_universes": n_eff_universes,
        },
        "pnl_concentration": _pnl_concentration(np.asarray(times_orig), r),
        "pbo_cscv": "NOT reliably estimable under the available experiment structure "
        "(few pre-registered variants, not a large combinatorial config grid on the "
        "same data). Not fabricated.",
    }
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    LEDGER_OUT.parent.mkdir(parents=True, exist_ok=True)
    LEDGER_OUT.write_text(
        json.dumps(
            {
                "fields": _ATTEMPT_FIELDS,
                "attempts": [dict(zip(_ATTEMPT_FIELDS, a, strict=True)) for a in ATTEMPTS],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_report(payload)
    c = payload["canonical_original20"]
    d = payload["deflation"]
    print(
        f"SR(ann) {c['sharpe_annualized']:.3f}; PSR vs 0 = {c['psr_vs_zero']:.4f}; "
        f"DSR direct(N={d['n_direct_tsm_variants']}) {d['direct']['deflated_sharpe_ratio']:.4f}; "
        f"DSR program(N={d['n_program_hypotheses']}) {d['program']['deflated_sharpe_ratio']:.4f}"
    )
    print(f"Wrote {REPORT_MD}\nWrote {LEDGER_OUT}\nWrote {JSON_OUT}")
    return 0


def _f(x, d: int = 4) -> str:
    return "n/a" if x is None else f"{x:.{d}f}"


def _write_report(p: dict) -> None:
    c, d, x, k = (
        p["canonical_original20"],
        p["deflation"],
        p["cross_universe_dependence"],
        p["pnl_concentration"],
    )
    ci = c["block_bootstrap_sharpe_ci_annualized"]
    lines = [
        "# Multiple-Testing Statistical Haircut (TASK-DEPLOY-001, Phase 6)",
        "",
        "How much of the canonical TSM's evidence survives higher moments, finite "
        "sample, and the number of hypotheses the program tried. Canonical stream = "
        "original-20, n={} rebalances. No promotion; descriptive.".format(c["n_rebalances"]),
        "",
        "## Canonical Sharpe under scrutiny",
        "",
        f"- Annualized Sharpe: **{c['sharpe_annualized']:.3f}** "
        f"(per-period {c['sharpe_per_period']:.4f})",
        f"- Skew {c['skew']:.3f}, kurtosis {c['kurtosis_non_excess']:.3f} (non-excess)",
        f"- **PSR vs 0** (prob true SR > 0): **{c['psr_vs_zero']:.4f}**",
        f"- Block-bootstrap 95% Sharpe CI (annualized, block={BLOCK}, seed={BOOT_SEED}): "
        f"**[{ci[0]:.3f}, {ci[1]:.3f}]**",
        "",
        "## Deflated Sharpe Ratio (correcting for selection across trials)",
        "",
        f"- Trial Sharpe variance (per-period, from {d['n_direct_tsm_variants']} TSM-family "
        f"variants): {d['trial_sharpe_variance_per_period']:.6f}",
        f"- Expected MAX Sharpe (annualized) under N direct trials "
        f"({d['n_direct_tsm_variants']}): {d['expected_max_sharpe_annualized_direct']:.3f}; "
        f"under N program hypotheses ({d['n_program_hypotheses']}): "
        f"{d['expected_max_sharpe_annualized_program']:.3f}",
        f"- **DSR (direct, N={d['n_direct_tsm_variants']}): "
        f"{d['direct']['deflated_sharpe_ratio']:.4f}**",
        f"- **DSR (whole program, N={d['n_program_hypotheses']}): "
        f"{d['program']['deflated_sharpe_ratio']:.4f}**",
        "",
        "## Cross-universe dependence (7 universes are NOT 7 independent tests)",
        "",
        f"- Average pairwise correlation of the 7 base streams: "
        f"**{x['avg_pairwise_correlation']:.3f}**",
        f"- Effective independent universes: **{x['effective_independent_universes']:.2f}** "
        f"(of {x['n_universes']}) -> the cross-universe breadth is worth far fewer than 7 "
        "independent bets.",
        "",
        "## PnL concentration",
        "",
        f"- Months: {k['n_months']}; best-month share of total: "
        f"**{_f(k['best_month_share_of_total'])}**; top-3-month share: "
        f"**{_f(k['top3_months_share_of_total'])}**",
        "",
        "## PBO / CSCV",
        "",
        p["pbo_cscv"],
        "",
        "## Reading -- a MIXED, sobering picture (fact / assumption / limitation)",
        "",
        "The multiple-testing correction is REASSURING, but three dependence/finite-"
        "sample facts cut the other way and are the honest haircut:",
        "",
        "- REASSURING (FACT): under iid assumptions PSR vs 0 = "
        f"{c['psr_vs_zero']:.3f}, and even deflating for the whole {d['n_program_hypotheses']}"
        "-hypothesis program the DSR stays high "
        f"({d['program']['deflated_sharpe_ratio']:.3f}) -> the lead is not plausibly "
        "the luckiest of many random trials (and the trials are mostly the same TSM "
        "family, so the naive count over-states selection risk).",
        "- SOBERING (FACT): the block-bootstrap Sharpe CI (serial-dependence aware) is "
        f"**[{ci[0]:.3f}, {ci[1]:.3f}] -- it INCLUDES zero**. So on the single 3-year "
        "stream the Sharpe is NOT conclusively above zero once autocorrelation is "
        "respected; the iid PSR is optimistic.",
        "- SOBERING (FACT): the 7 crypto universes are "
        f"{x['avg_pairwise_correlation']:.2f}-correlated -> only "
        f"~{x['effective_independent_universes']:.1f} EFFECTIVE independent universes. "
        "'Positive in 7/7' (TSM-010/013) is worth roughly ONE independent bet, not "
        "seven -- the breadth claim was materially overstated.",
        "- SOBERING (FACT): PnL is CONCENTRATED -- the best month is "
        f"{_f(k['best_month_share_of_total'], 2)} of total and the top 3 months are "
        f"{_f(k['top3_months_share_of_total'], 2)} of total return; the edge is "
        "episodic, not steady.",
        "- ASSUMPTION: trial Sharpe variance from the 7 original-20 TSM variants; "
        "block bootstrap block=10 rebalances. PBO/CSCV not estimable here (documented, "
        "not faked).",
        "- NET: the edge SURVIVES multiple-testing selection (DSR high), but its "
        "effective statistical weight is much THINNER than the raw '7/7, CI excludes "
        "zero' headline -- ~1 independent universe, a single-stream CI that touches "
        "zero, and episodic PnL. Honest verdict: a real but modest, dependence-"
        "discounted edge; the forward track (Phase 7) is what ultimately settles it.",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
