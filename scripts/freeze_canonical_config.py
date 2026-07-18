#!/usr/bin/env python3
"""TASK-DEPLOY-001 Phase 0: freeze the canonical TSM configuration (immutable artifact).

Resolves the naming ambiguity ("base TSM" / "base vol-targeted TSM" /
"vol-target-only" / "combined ERC+vol-target") from the CODE and VALIDATION
ARTIFACTS, not the report names. Evidence: the validation program (TSM-009/010/
011/013/014/015) ran the primary/core as `TsmTrendConfig(include_funding=True)`
with portfolio_erc=False and NO Moreira-Muir managed-vol overlay -- i.e. the pure
base whose "vol-targeting" is the INTRINSIC per-leg inverse-vol sizing. The
managed-vol overlay (vol_target.py, window=12/cap=3.0) and ERC together form the
COMBINED-CAVEATED secondary (TSM-008), which the program found only partly
generalizes (beats base in 3/7 universes). Emits a hashed, source-pinned artifact.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.tsm_trend import TsmTrendConfig  # noqa: E402
from src.research.vol_target import DEFAULT_SCALE_CAP, DEFAULT_VOL_WINDOW  # noqa: E402

OUT = PROJECT_ROOT / "artifacts" / "tsm" / "canonical-config.json"
FROZEN_OUT = PROJECT_ROOT / "artifacts" / "tsm" / "frozen-configs.json"

# Source commit where the exact economic config (include_funding=True) was locked.
SOURCE_COMMIT = "e0779b0"  # TASK-FC-II-008: TSM with funding P&L
_CFG = TsmTrendConfig(include_funding=True)  # the canonical core, straight from defaults


def _hash(economic_block: dict) -> str:
    payload = json.dumps(economic_block, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_core_economic() -> dict:
    """Economic definition of the canonical core -- the block that gets hashed."""
    return {
        "strategy_id": "tsm-canonical-core",
        "variant": "canonical-core",
        "signal_definition": (
            "sign of the 28d (672h) trailing log-price change per symbol; "
            "long if positive, short if negative"
        ),
        "lookbacks": {
            "signal_lookback_hours": _CFG.lookback_hours,  # 672 = 28d
            "realized_vol_window_hours": _CFG.vol_window_hours,  # 168 = 7d
        },
        "rebalance_cadence": f"{_CFG.hold_hours}h (5d)",
        "weighting": (
            "per-leg inverse realized-volatility (7d), signed by the 28d trend, "
            "normalized to unit gross exposure across the long/short book"
        ),
        "volatility_targeting": {
            "type": "intrinsic_per_leg_inverse_vol",
            "enabled": True,
            "realized_vol_window_hours": _CFG.vol_window_hours,
            "managed_vol_overlay": {
                "enabled": False,
                "note": (
                    "Moreira-Muir managed-vol overlay (window="
                    f"{DEFAULT_VOL_WINDOW} rebalances, cap={DEFAULT_SCALE_CAP}) is "
                    "NOT in the canonical core; it belongs to combined-caveated."
                ),
            },
        },
        "portfolio_erc": _CFG.portfolio_erc,  # False
        "regime_filter": _CFG.regime_filter,  # False
        "conviction_sizing": _CFG.conviction_sizing,  # False
        "funding": _CFG.include_funding,  # True
        "universe_policy": (
            "deployment universe = original 20 liquid Binance USDM perps; "
            "generalization validated across thematic/liquidity universes with "
            "FIXED params (zero re-tune)"
        ),
        "cost_policy": f"{_CFG.cost_bps_per_leg} bps per leg, applied on turnover",
    }


def _combined_caveated_economic() -> dict:
    core = _canonical_core_economic()
    core["strategy_id"] = "tsm-combined-caveated"
    core["variant"] = "combined-caveated"
    core["portfolio_erc"] = True
    core["volatility_targeting"]["managed_vol_overlay"] = {
        "enabled": True,
        "window_rebalances": DEFAULT_VOL_WINDOW,
        "cap": DEFAULT_SCALE_CAP,
        "target_definition": (
            "expanding causal mean of trailing realized vol; scale = "
            "clip(target/sigma, 0, cap); both sigma and target use shift(1)"
        ),
    }
    core["note"] = (
        "SECONDARY monitoring variant (TSM-008). Only partly generalizes "
        "(beats base in 3/7 universes); NOT the universal core."
    )
    return core


def main() -> int:
    core = _canonical_core_economic()
    combined = _combined_caveated_economic()
    now = datetime.now(UTC).isoformat()

    canonical = {
        **core,
        "source_commit": SOURCE_COMMIT,
        "config_hash": _hash(core),
        "frozen_at_utc": now,
        "provenance": (
            "Reconciled from code (src/research/tsm_trend.py defaults + "
            "include_funding=True) and validation artifacts (TSM-009..015 primary "
            "stream). Managed-vol overlay + ERC excluded from the core per artifact "
            "evidence, not report naming."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(canonical, indent=2, sort_keys=True), encoding="utf-8")

    frozen = {
        "frozen_at_utc": now,
        "source_commit": SOURCE_COMMIT,
        "configs": {
            "canonical-core": {**core, "config_hash": _hash(core)},
            "combined-caveated": {**combined, "config_hash": _hash(combined)},
            "buy-hold-benchmark": {
                "strategy_id": "buy-hold-benchmark",
                "variant": "benchmark",
                "definition": (
                    "equal-weight long-only buy-and-hold of the same universe, "
                    "unit gross, same rebalance grid (reference, not a strategy)"
                ),
                "config_hash": _hash({"benchmark": "buy_hold_equal_weight"}),
            },
            "cash-benchmark": {
                "strategy_id": "cash-benchmark",
                "variant": "benchmark",
                "definition": "flat / zero-return cash (0% nominal, no funding)",
                "config_hash": _hash({"benchmark": "cash_zero"}),
            },
        },
    }
    FROZEN_OUT.write_text(json.dumps(frozen, indent=2, sort_keys=True), encoding="utf-8")

    combined_hash = frozen["configs"]["combined-caveated"]["config_hash"]
    print(f"canonical-core config_hash = {canonical['config_hash']}")
    print(f"combined-caveated config_hash = {combined_hash}")
    print(f"source_commit = {SOURCE_COMMIT}")
    print(f"Wrote {OUT}\nWrote {FROZEN_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
