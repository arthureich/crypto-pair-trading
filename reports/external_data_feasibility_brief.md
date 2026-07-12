# External-Data Feasibility Brief -- the report's remaining factor families

**Purpose.** The public-data family sweep is now complete (Families A/B/C/D/E/
I-bars/J all CONCLUÍDA on data we already have; see the ledger family matrix).
Every remaining family from the external report needs data we do **not** have on
disk, and acquiring it is an investment decision that is **yours**, not mine.
This brief lays out — without downloading or spending anything — what each
family needs, where it comes from, rough cost/effort, and my recommendation, so
you can decide. **This is the stop point.**

**Honesty caveat.** This environment is offline, so I could not run live
availability/price probes. The sources and price tiers below are from
established public knowledge as of the project's cutoff and should be confirmed
in an online session before any purchase. Nothing here commits spend.

---

## The four candidate families (report ranking)

| # | Family | Core signal | Data needed | Free/cheap start? | Full/paid source | Effort | Prior |
|---|---|---|---|---|---|---|---|
| 1 | **F — Options / VRP** | Variance risk premium (IV² − RV²); IV skew; term structure | Implied-vol surface / IV index (BTC, ETH mainly) | Deribit **DVOL** index history (free-ish); Deribit public API (recent) | Tardis.dev, Amberdata, Laevitas, Block Scholes (full surface = $$$/subscription) | Medium–High | **Highest** in report — but see instrument caveat |
| 2 | **G — On-chain** | Exchange net-flows, stablecoin supply, SOPR, active addresses, miner flows | Chain-level metrics aligned to hourly | **Coin Metrics community** + **Dune** (free tiers, real coverage) | Glassnode / CryptoQuant / Nansen (premium metrics paid) | Medium | Medium–High (BTC/ETH-centric; thin for the 18 alt perps) |
| 4 | **Flow — cross-venue** | Cross-exchange CVD, funding **dispersion** across venues, aggregated OI, spot-perp basis across exchanges | Multi-venue perp/spot tick or 1m | Coinalyze / Coinglass APIs (rate-limited free) | Kaiko / Amberdata (tick = $$$) | Medium–High | Medium — the incremental bet after single-venue OI/funding/flow all came back SEM_INFO |
| — | **H — Sentiment** | Fear&Greed, social volume, news tone | Index + social feeds | Fear&Greed index (free); funding-as-sentiment (already have) | LunarCrush / Santiment (paid) | Low–Medium | Low (noisy; overlaps signals already tested) |

---

## The one caveat that outranks the ranking: instrument class

The report ranks **Options/VRP #1**, and the academic evidence for a crypto
variance risk premium is genuinely the strongest of the four. But VRP is
**not a perp pair-trade** — harvesting it means *selling options* (or trading
DVOL/variance products) on an options venue. That is a different instrument,
different execution, different margin/risk model, and different tail profile
(short-vol = picking up pennies with occasional large losses) from everything
this project has built (dollar-neutral perp pairs). Adopting it is a **strategy-
class pivot**, not just a data purchase. It can still be worth it — but the
decision is "do we open an options book?", which is much bigger than "do we buy
a data feed?" and is squarely your call.

The other three families (on-chain, cross-venue flow, sentiment) stay within
the current perp-pair instrument: they would feed **new features into the same
kind of directional/relative-value signal** we already test. So they are
cheaper to *integrate* even where the raw data costs money.

---

## My recommendation (for your decision, not to execute)

1. **Do not buy the expensive tick/surface feeds yet.** Every paid-tick family
   (Tardis options surface, Kaiko cross-venue tick) is a real recurring cost
   against a project whose single credible lead (vol-targeted TSM) is *free*
   and merely OOS-gated. Spend nothing until a cheap probe says the signal is
   there.

2. **If you want to keep exploring within the current instrument (my default
   recommendation): start with the free tiers of Family G (on-chain) and
   cross-venue flow.** Coin Metrics community + Dune (on-chain) and
   Coinalyze/Coinglass (cross-venue funding dispersion, aggregated OI) can
   produce a real *information-content diagnostic* — same ADR-0019 methodology,
   same |rho|≥0.03 + 3-sub-period bar — at **zero or near-zero cost**. If a
   feature clears the bar on the free slice, *that* is the evidence that
   justifies paying for the fuller feed. If it doesn't, we've spent nothing.
   Note honestly: single-venue OI, funding, and flow all came back SEM_INFO, so
   the prior on cross-venue is only moderate; on-chain is the fresher bet.

3. **Treat Options/VRP as a separate, larger strategic question.** If the VRP
   edge interests you, the cheap first step is the **free Deribit DVOL index
   history** (BTC/ETH) to check whether a simple RV-vs-IV signal even points the
   right way, *before* any surface purchase or any decision to open an options
   book. But flag it as the instrument-class pivot it is.

4. **Deprioritize Sentiment (H).** Low prior, noisy, and it overlaps signals we
   already have (funding-as-positioning). Only worth the free Fear&Greed index
   as a throw-in feature if we're already building an on-chain diagnostic.

**In one line:** the disciplined next move is a *free-tier* on-chain +
cross-venue information-content diagnostic (I can build it exactly like the ALT
series, no spend), and to keep Options/VRP as a distinct "do we open an options
book?" decision. But whether to spend anything at all — and on which family
first — is your investment call. **I am stopping here for that decision.**

---

## What I can do next without any spend (if you say go)

- Build a Family G / cross-venue **information-content diagnostic** against the
  **free-tier** APIs (Coin Metrics community, Dune, Coinalyze), pre-registered
  under a new ADR, same methodology as TASK-ALT-001..008. Zero cost, zero paid
  data. (Requires network access in an interactive session, since this
  environment is offline.)
- Pull **free Deribit DVOL** history and run a first RV-vs-IV directional check
  for the VRP question — again pre-registered, zero spend.
- Keep the TSM and funding-carry forward paper tracks accruing (already
  automated; re-run monthly as new months download).

Tell me which, if any — or that you'd rather wait and let the free forward
tracks accrue before spending attention here at all.
