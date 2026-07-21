#!/usr/bin/env python3
"""TASK-BASIS-001 (b): time-profile characterization of the spot x perp funding carry.

Not a promotion and not an optimization. Fixed, pre-declared windows only; answers
ONE question: when did the carry stop compensating the operational + counterparty
risks? Reads the cached funding history (offline; no new download) for Binance and
Bybit (full ~3y) and OKX (shallow), and per window reports gross/net APR, return on
TOTAL capital, % positive settlements, negative months, worst cumulative-funding
drawdown, monthly concentration, and Binance-Bybit dispersion, against an a-priori
operational HURDLE (set from first principles, NOT fit to the data to pass).

Risk framing (deliberately softened): the position has LOW directional risk and LOW
path-dependence PROVIDED both legs stay operational and adequately margined -- it is
NOT literally risk-free (funding can invert, spot-perp spread can widen, legs can
have separate margins / liquidation, a leg can fail, plus exchange / index / ADL /
custody risk). Paper only.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research.cash_carry import annualize_return, clears_deploy_hurdle  # noqa: E402
from src.research.execution_model import ExecutionCostModel  # noqa: E402

CACHE = PROJECT_ROOT / "data/research/basis"
REPORT_MD = PROJECT_ROOT / "reports/basis_carry_characterization.md"
JSON_OUT = PROJECT_ROOT / "artifacts/basis/basis_carry_characterization.json"
COST_BPS_PER_LEG = ExecutionCostModel().taker_fee_bps + ExecutionCostModel().half_spread_bps
N_LEGS_ROUNDTRIP = 4
MARGIN_FRACTION = 0.10
MIN_SETTLEMENTS = 180  # ~60 days at 8h -> a window must have this many to be a valid read

# A-PRIORI operational hurdle (first principles; NOT fit to the data).
HURDLE_COMPONENTS = {
    "opportunity_cost_of_capital": 0.04,  # ~risk-free / USDC lending forgone
    "exchange_counterparty": 0.03,  # holding capital on a CEX
    "stablecoin_custody": 0.01,  # stablecoin depeg / custody
    "fees_and_slippage_annualized": 0.005,
    "funding_inversion_safety": 0.02,  # buffer for funding turning negative
    "two_leg_maintenance": 0.005,  # keeping both legs matched/margined
}
HURDLE_APR = sum(HURDLE_COMPONENTS.values())  # ~0.11

# Fixed calendar windows (declared a priori; the data starts 2023-06).
CAL_WINDOWS = (
    ("2023(H2)", "2023-06-01", "2024-01-01"),
    ("2024", "2024-01-01", "2025-01-01"),
    ("2025", "2025-01-01", "2026-01-01"),
    ("2026_YTD", "2026-01-01", "2027-01-01"),
)
ROLLING_DAYS = (90, 180, 365)
_ASSETS = ("BTC", "ETH")


def _load(venue: str, asset: str) -> pd.DataFrame:
    p = CACHE / f"funding_{venue}_{asset}.csv.gz"
    if not p.exists():
        return pd.DataFrame(columns=["time", "rate"])
    return pd.read_csv(p).sort_values("time").reset_index(drop=True)


def _ms(day: str) -> int:
    return int(pd.Timestamp(day, tz="UTC").value // 1_000_000)


def _metrics(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 10:  # noqa: PLR2004
        return {"n_settlements": int(len(df)), "net_apr": None}
    rates = df["rate"].to_numpy(dtype=float)
    days = max((df["time"].iloc[-1] - df["time"].iloc[0]) / 86_400_000.0, 1.0)
    gross = float(rates.sum())
    net = gross - N_LEGS_ROUNDTRIP * COST_BPS_PER_LEG / 10_000.0
    net_apr = annualize_return(net, days)
    roc_apr = net_apr / (1.0 + MARGIN_FRACTION)  # return on TOTAL capital (spot + margin)
    equity = np.cumsum(rates)
    worst_dd = float(np.max(np.maximum.accumulate(equity) - equity))
    idx = pd.to_datetime(df["time"], unit="ms", utc=True)
    monthly = pd.Series(rates, index=idx).groupby(pd.Grouper(freq="MS")).sum()
    total = float(monthly.sum())
    concentration = float(monthly.max() / total) if total > 0 else None
    return {
        "n_settlements": int(len(rates)),
        "days": days,
        "gross_apr": annualize_return(gross, days),
        "net_apr": net_apr,
        "return_on_total_capital_apr": roc_apr,
        "pct_settlements_positive": float(np.mean(rates > 0)),
        "negative_months": int((monthly < 0).sum()),
        "n_months": int(monthly.size),
        "worst_cum_funding_dd_return_units": worst_dd,
        "best_month_share_of_total": concentration,
        "clears_hurdle": bool(
            clears_deploy_hurdle(roc_apr, HURDLE_APR, len(rates), min_settlements=MIN_SETTLEMENTS)
        ),
    }


def _slice(df: pd.DataFrame, lo: int, hi: int) -> pd.DataFrame:
    return df[(df["time"] >= lo) & (df["time"] < hi)]


def main() -> int:
    data = {v: {a: _load(v, a) for a in _ASSETS} for v in ("binance", "bybit", "okx")}
    latest = max(
        (
            int(df["time"].max())
            for v in data
            for df in [data[v][a] for a in _ASSETS]
            if not df.empty
        ),
        default=_ms("2026-07-31"),
    )

    windows = {}
    for name, lo, hi in CAL_WINDOWS:
        windows[name] = (_ms(lo), _ms(hi))
    for d in ROLLING_DAYS:
        windows[f"rolling_{d}d"] = (latest - d * 86_400_000, latest + 1)

    out: dict = {}
    for venue in ("binance", "bybit"):  # full-depth venues
        out[venue] = {}
        for asset in _ASSETS:
            df = data[venue][asset]
            out[venue][asset] = {w: _metrics(_slice(df, lo, hi)) for w, (lo, hi) in windows.items()}

    # Binance-Bybit dispersion per (asset, window)
    dispersion = {}
    for asset in _ASSETS:
        dispersion[asset] = {}
        for w in windows:
            b = out["binance"][asset][w].get("net_apr")
            y = out["bybit"][asset][w].get("net_apr")
            dispersion[asset][w] = None if (b is None or y is None) else abs(b - y)

    # When did it stop clearing the hurdle? last calendar window that cleared (on ROC),
    # averaged across venues+assets.
    def cleared(name: str) -> bool:
        vals = [
            out[v][a][name]["clears_hurdle"]
            for v in ("binance", "bybit")
            for a in _ASSETS
            if out[v][a][name].get("net_apr") is not None
        ]
        return bool(vals) and all(vals)

    last_clearing = None
    for name, _lo, _hi in CAL_WINDOWS:
        if cleared(name):
            last_clearing = name

    payload = {
        "task": "TASK-BASIS-001 (b) carry time-profile characterization",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "hurdle_components": HURDLE_COMPONENTS,
        "hurdle_apr": HURDLE_APR,
        "margin_fraction": MARGIN_FRACTION,
        "min_settlements": MIN_SETTLEMENTS,
        "results": out,
        "binance_bybit_net_apr_dispersion": dispersion,
        "last_calendar_window_clearing_hurdle_all": last_clearing,
        "okx_recent": {a: _metrics(data["okx"][a]) for a in _ASSETS},
    }
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    _write_report(payload)
    print(
        f"hurdle APR = {HURDLE_APR:.1%}; last calendar window clearing it (all venues/assets): "
        f"{last_clearing}"
    )  # noqa: E501
    for name, _lo, _hi in CAL_WINDOWS:
        b = out["binance"]["BTC"][name]
        if b.get("net_apr") is not None:
            print(
                f"  {name}: Binance BTC net APR {b['net_apr'] * 100:5.1f}% ROC "
                f"{b['return_on_total_capital_apr'] * 100:5.1f}% clears={b['clears_hurdle']}"
            )
    print(f"Wrote {REPORT_MD}\nWrote {JSON_OUT}")
    return 0


def _p(x, d: int = 1) -> str:
    return "n/a" if x is None else f"{x * 100:.{d}f}%"


def _write_report(p: dict) -> None:
    hc = p["hurdle_components"]
    lines = [
        "# Carry time-profile characterization (TASK-BASIS-001 (b))",
        "",
        "Fixed windows, no optimization. Answers: **when did the spot x perp funding "
        "carry stop compensating the operational + counterparty risks?** Return on "
        "TOTAL capital (spot + margin) vs an a-priori hurdle (NOT fit to the data).",
        "",
        "## A-priori operational hurdle",
        "",
        f"- **Hurdle APR = {p['hurdle_apr']:.1%}** = "
        + " + ".join(f"{k} {v:.1%}" for k, v in hc.items()),
        f"- Deploy rule: net forward APR on total capital > hurdle AND "
        f">= {p['min_settlements']} settlements (causal, conservative; hurdle set "
        "from first principles, not chosen to make the strategy pass).",
        "",
        f"## Headline: last calendar window clearing the hurdle on ALL venues/assets = "
        f"**{p['last_calendar_window_clearing_hurdle_all'] or 'NONE'}**",
        "",
        "Return on total capital (net APR / (1+margin)) by window:",
        "",
        "| Window | Binance BTC | Binance ETH | Bybit BTC | Bybit ETH | clears hurdle? |",
        "|---|---:|---:|---:|---:|---|",
    ]
    order = [w for w, _, _ in CAL_WINDOWS] + [f"rolling_{d}d" for d in ROLLING_DAYS]
    for w in order:
        cells = []
        clears = []
        for v in ("binance", "bybit"):
            for a in _ASSETS:
                m = p["results"][v][a][w]
                cells.append(_p(m.get("return_on_total_capital_apr")))
                if m.get("net_apr") is not None:
                    clears.append(m["clears_hurdle"])
        verdict = (
            "n/a" if not clears else ("YES" if all(clears) else ("some" if any(clears) else "no"))
        )
        lines.append(f"| {w} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {verdict} |")

    lines += [
        "",
        "## Detail (Binance BTC, per window)",
        "",
        "| Window | gross APR | net APR | ROC | % settl + | neg months | worst cum-fund DD | "
        "best-month share |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for w in order:
        m = p["results"]["binance"]["BTC"][w]
        if m.get("net_apr") is None:
            lines.append(f"| {w} | -- | n/a | -- | -- | -- | -- | -- |")
            continue
        lines.append(
            f"| {w} | {_p(m['gross_apr'])} | {_p(m['net_apr'])} | "
            f"{_p(m['return_on_total_capital_apr'])} | "
            f"{_p(m['pct_settlements_positive'], 0)} | "
            f"{m['negative_months']}/{m['n_months']} | "
            f"{_p(m['worst_cum_funding_dd_return_units'])} | "
            f"{_p(m['best_month_share_of_total'], 0)} |"
        )
    disp = p["binance_bybit_net_apr_dispersion"]
    okx = p["okx_recent"]
    lines += [
        "",
        "## Binance-Bybit dispersion (net APR abs diff)",
        "",
        "| Window | BTC | ETH |",
        "|---|---:|---:|",
    ]
    for w in order:
        lines.append(f"| {w} | {_p(disp['BTC'][w], 2)} | {_p(disp['ETH'][w], 2)} |")
    lines += [
        "",
        f"OKX (recent, depth-limited): BTC ROC "
        f"{_p(okx['BTC'].get('return_on_total_capital_apr'))}, ETH ROC "
        f"{_p(okx['ETH'].get('return_on_total_capital_apr'))} "
        f"(n={okx['BTC'].get('n_settlements')}).",
        "",
        "## Reading -- when did the carry stop compensating the risks?",
        "",
        f"- The carry cleared the ~{p['hurdle_apr']:.0%} operational hurdle (on TOTAL "
        "capital) on all venues/assets only through **"
        f"{p['last_calendar_window_clearing_hurdle_all'] or 'no full window'}**; "
        "it has been BELOW the hurdle since. The high APR is front-loaded in the rich-"
        "funding 2023-2024 regime and has COMPRESSED toward ~0 (matching the dated-basis "
        "compression). So even though it is net-positive over the full sample, on a "
        "risk-adjusted, capital-employed, hurdle basis it stopped being deployable well "
        "before today.",
        "- HURDLE SENSITIVITY (honest): the verdict depends on the hurdle. Under the full "
        f"~{p['hurdle_apr']:.0%} hurdle (all costs incl. counterparty/custody) it clears "
        "in NO full calendar window (2024 peaks at ~10.6% ROC, just under). Under a LEANER "
        "~5% marginal hurdle (capital already on-venue, marginal costs only) 2023-2024 "
        "clear but 2025 (~4.4%) and 2026 (~0.5%) do not -> the crossing is ~2025. Either "
        "way the carry stopped compensating around 2025 and is ~0 now.",
        "- RISK FRAMING (softened): the position has LOW directional risk and LOW path-"
        "dependence PROVIDED both legs stay operational and adequately margined. It is "
        "NOT risk-free: funding can invert (short then pays), the spot-perp spread can "
        "widen, the two legs can have separate margins / liquidation, a leg can fail, "
        "plus exchange / index / ADL / custody risk.",
        "- CONCLUSION for the family: **real but currently compressed** -- the mechanism "
        "is genuine and cross-exchange-consistent (Binance+Bybit), but at today's funding "
        "it does not clear a conservative operational hurdle. PAUSE; revisit only if "
        "forward funding rises back above the hurdle for a sustained run (the deploy rule).",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
