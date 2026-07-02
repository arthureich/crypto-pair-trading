# Handoffs

Last updated: 2026-07-02

## HANDOFF - Sprint 8 Backtest Walk-Forward Cost-Aware (Closure)

### Status

DONE (gate PASSA, scoped). TASK-008-08 (raw evidence cleanup) remains BLOCKED.

### Agente

Backtest Agent, Quant Research Agent, Market Data Agent, QA Agent (review), PM Agent (orchestration, fixes)

### Contexto

The previous PM session (quota exhausted mid-task) had already: opened Sprint
8, created TASK-008-01 through TASK-008-08, implemented
`project_control/SPRINT8_UNIVERSE.json`, `src/research/sprint8.py`,
`scripts/run_sprint8_backtest.py`, and 3 test files (14 tests), and run a
first backtest (31 evaluated, 17 approved, portfolio net_pnl_bps=-125.83). It
was interrupted while fixing a ruff issue on the runner. This session:
finished the ruff fix (2 remaining auto-fixable import-order issues), then
dispatched the mandatory reviews the sprint's own `CURRENT_SPRINT.md` calls
for (Backtest Agent, Quant Research Agent, Market Data Agent, QA Agent) before
accepting any of the prior session's unreviewed work as done.

### O que foi encontrado e corrigido

The parallel review returned **three blocking (P1) findings**:

1. **Backtest Agent**: `_one_hour_gross_edge_bps` combined both legs' returns
   1:1, but the entry signal was generated from a beta-weighted Kalman
   spread -- pricing a different, uncontrolled exposure than the one that
   triggered the signal.
2. **Quant Research Agent**: `generate_pair_signal_intents` fit `estimate_ou`
   once on each pair's *entire* 30-day spread series to gate every signal in
   that series, so a regime that only became mean-reverting later in the
   month could retroactively "approve" signals earlier in the same month --
   genuine look-ahead in the trust gate, not just in z-score (which was
   already correctly causal).
3. **Market Data Agent**: execution cost was charged only for opening the
   position (`_causal_symbol_cost_map`), never for closing it one hour later
   -- understating round-trip cost by roughly half.

QA Agent returned PASSA with one P2 (the runner script had zero direct test
coverage, though manual line review found no bugs).

All three P1s were fixed:

1. `_one_hour_gross_edge_bps` now weights leg B's return by `abs(intent.beta)`
   and also returns the exit bar's `open_time`.
2. `generate_pair_signal_intents` now refits OU on a trailing causal window
   (`ou_window`, default 168h) ending at each candidate index, and uses the
   Kalman result's per-index `unstable_points[position]` instead of the
   aggregate `beta_unstable` flag (same class of bug). A new regression test
   (`test_generate_pair_signal_intents_is_causal_across_appended_future_bars`)
   builds a 60-bar prefix and a 100-bar extended version with a sharply
   different trend, and asserts the intents generated inside the original
   60-bar window are identical between the two -- a direct proof of no
   look-ahead, not just a manual code read.
3. `_round_trip_symbol_cost_map` (replacing `_causal_symbol_cost_map`) now
   sums causal cost at both the entry time and the exit time per leg.

Also fixed the P2: renamed the misleading `gate_pass` (`bool(approved)`, true
with just 1 of 31 pairs positive) to `any_pair_backtest_approved`, and added
an explicit `portfolio_gate_pass` (`portfolio_net_pnl_quote > 0`, currently
false) so the two very different claims can never be collapsed into one
"Sprint 8 passed" statement.

Added 6 new tests for the runner (`tests/test_sprint8_backtest_runner.py`)
covering beta-weighted edge, missing-next-bar handling, walk-forward-window
boundary inclusivity, round-trip cost summation, and fail-closed missing-cost
behavior -- closing QA's P2 coverage gap.

A second, independent confirmation review (Backtest Agent + QA Agent
combined) re-verified all three fixes against the Kalman spread definition
and the causal-window logic, judged the new regression test genuine (not a
tautology), and confirmed the round-trip cost sums correctly. One P3 was
investigated further by the PM (not just accepted): `total_trades` stayed at
622 before and after the OU-gate fix, which could have indicated the fix was
a silent no-op. Independently reproduced: for these specific pairs the
full-sample half-life is very short (~1-1.5h), so the pair is strongly
mean-reverting through nearly the entire 30-day window and the causal
trailing-window fit agrees with the full-sample fit at almost every index.
Confirmed not a bug.

### Resultado final

Corrected backtest run: 31 pairs evaluated, 622 trades, **13 pairs
backtest-approved** (net PnL positive after real, causal, round-trip cost),
18 rejected. Portfolio net PnL across all 31 pairs equal-weighted is negative
(`total_net_pnl_bps=-1716.67`, `portfolio_net_pnl_quote=-$171.67`) and is
reported as a separate, explicit `portfolio_gate_pass=false` -- never
collapsed with the pair-level result.

### Arquivos alterados

```text
src/research/sprint8.py
scripts/run_sprint8_backtest.py
tests/test_sprint8_universe.py (pre-existing, unmodified)
tests/test_sprint8_walk_forward.py (pre-existing, unmodified)
tests/test_sprint8_signal_backtest.py (added causal-safety regression test)
tests/test_sprint8_backtest_runner.py (new)
reports/sprint_08_backtest.md (new)
project_control/TASK_BOARD.md
project_control/CURRENT_SPRINT.md
project_control/PROJECT_STATE.md
project_control/RISKS.md
project_control/TEST_MATRIX.md
project_control/DAILY_LOG.md
data/research/binance_public/cost_pilot/sprint8_backtest_results.json (regenerated)
data/research/binance_public/cost_pilot/sprint8_backtest_pair_results.csv (regenerated)
```

### Testes rodados

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests -q
Result: passed, 211 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src scripts tests
Result: passed.

UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint8_backtest.py
Result: passed. 31 pairs, 622 trades, 13 approved, 18 rejected, portfolio
net PnL negative.
```

### Pendencias

```text
TASK-008-08: 17GB of raw checksum-verified Binance archives remain under
data/research/binance_public/cost_pilot/raw/. Do NOT delete without explicit
user acceptance -- disk has 353GB free, not urgent.

Sprint 9 scope/tasks are not yet defined in project_control. Recommend the
user confirm what Sprint 9 should build (e.g. extend backtest window,
paper-trading design, barrier-policy exit modeling) before opening it.

Known limitations carried forward (documented in reports/sprint_08_backtest.md
and RISKS.md): fixed 1-hour exit horizon with no stop/take-profit, cost uses
median spread only (no p95/p99 tail sensitivity run), max_drawdown_bps is
per-pair only.
```

## HANDOFF - Sprint 8 Opening / Next Dispatch

### Status

OPENED

### Agente

PM Agent

### Contexto

Sprint 7 is complete for the research base and execution-cost evidence gate.
Sprint 8 is now opened as a scoped offline backtest sprint. The only
cost-gated universe allowed for Sprint 8 is the 31 pairs that passed the
expanded June-2023 cost gate. The 10 ADAUSDT pairs remain blocked by
`WIDE_MEDIAN_SPREAD`.

### O que foi feito

- Replaced `project_control/CURRENT_SPRINT.md` with Sprint 8 scope, gates,
  allowed/prohibited work, universe, evidence artifacts, and tasks.
- Updated `project_control/PROJECT_STATE.md` from Sprint 7 to Sprint 8.
- Added Sprint 8 rows to `project_control/TASK_BOARD.md`.
- Created 8 task files in `tasks/sprint_08/`.
- Marked only TASK-008-01 as READY; all later tasks are BLOCKED by explicit
  dependencies.

### Proxima tarefa executavel

```text
TASK-008-01 - Congelar universo e contrato de evidencia
Agent: PM Agent
Reviewer: Backtest Agent + Market Data Agent
Status: READY
```

### Arquivos criados

```text
tasks/sprint_08/TASK-008-01-freeze-universe-evidence.md
tasks/sprint_08/TASK-008-02-walk-forward-split.md
tasks/sprint_08/TASK-008-03-offline-signal-intent.md
tasks/sprint_08/TASK-008-04-cost-aware-backtest.md
tasks/sprint_08/TASK-008-05-metrics-ranking.md
tasks/sprint_08/TASK-008-06-qa-tests.md
tasks/sprint_08/TASK-008-07-report-gate.md
tasks/sprint_08/TASK-008-08-evidence-cleanup-plan.md
```

### Gate policy

```text
Sprint 8 does not authorize paper/live trading.
Sprint 8 does not touch ledger, recovery, execution engine, live engine, ML,
or exchange trading endpoints.
Sprint 8 decides only which of the 31 cost-gated pairs survive offline
walk-forward backtest with cost.
```

## HANDOFF - TASK-007-10 Expanded All-Candidate Cost Gate (Sprint 8 Scoped Unblock)

### Status

DONE

### Agente

PM Agent, Market Data Agent, QA Agent

### Contexto

After the 6-symbol June-2023 pilot unlocked only 5 pairs, the user asked to do
what was necessary to unblock Sprint 8 while avoiding memory blow-up. The full
36-month cost gate remains impossible from Binance Public Data because
bookTicker coverage does not exist past ~2024-04, but June 2023 can be
expanded to every symbol used by the 41 Sprint 7 statistical candidate pairs.

### O que foi feito

- Hardened `scripts/run_sprint7_execution_cost_download.py` before processing
  BTCUSDT/ETHUSDT: the runner now stream-reads the single CSV member directly
  from each daily ZIP with `zipfile.open`, `BOOK_TICKER_COLUMNS`, and numeric
  dtypes instead of reading the full decompressed member into bytes first.
- Downloaded and verified the 9 missing symbols for June 2023:
  ATOMUSDT, BTCUSDT, DOGEUSDT, ETHUSDT, LINKUSDT, LTCUSDT, SOLUSDT, UNIUSDT,
  XRPUSDT.
- Combined those with the existing 6-symbol pilot, covering all 15 symbols
  that appear in the 41 Sprint 7 candidate pairs.
- Preserved a raw hourly-cost CSV, a duplicate-hour CSV, a deduplicated
  hourly-cost CSV for the gate, a bars CSV, a summary JSON, a local
  checksum-verified source_review JSON, and an archive manifest CSV/JSON.
- Ran the existing cost gate against the 41 candidate pairs, scoped strictly
  to June 2023.

### Evidencia

```text
450 Binance daily bookTicker ZIPs + .CHECKSUM files present.
17.98GB compressed archive bytes.
10827 raw hourly rows.
27 duplicate symbol-hours / 54 duplicate rows at day boundaries.
10800 deduplicated hourly rows used by the gate.
10800 June-2023 1h bars for 15 symbols.
```

Artifacts:

```text
data/research/binance_public/cost_pilot/all_candidates_202306_hourly_cost_raw.csv
data/research/binance_public/cost_pilot/all_candidates_202306_hourly_cost.csv
data/research/binance_public/cost_pilot/all_candidates_202306_duplicate_hours.csv
data/research/binance_public/cost_pilot/all_candidates_202306_bars.csv
data/research/binance_public/cost_pilot/all_candidates_202306_summary.json
data/research/binance_public/cost_pilot/all_candidates_202306_archive_manifest.csv
data/research/binance_public/cost_pilot/all_candidates_202306_manifest.json
data/research/binance_public/cost_pilot/all_candidates_202306_source_review.json
data/research/binance_public/cost_pilot/all_candidates_202306_execution_cost_gate.json
data/research/binance_public/cost_pilot/all_candidates_202306_execution_cost_gate.csv
```

### Resultado

```text
cost_gated_pass=true
pairs_passed=31
pairs_failed=10
symbol_count=15
normalized_cost_rows=10800
source_review.complete_for_window=true
```

Failed pairs:

```text
ADAUSDT/DOTUSDT
ADAUSDT/AVAXUSDT
ADAUSDT/ETCUSDT
ADAUSDT/LINKUSDT
ADAUSDT/DOGEUSDT
ADAUSDT/ETHUSDT
ADAUSDT/ARBUSDT
ADAUSDT/XRPUSDT
ADAUSDT/ATOMUSDT
ADAUSDT/SOLUSDT
```

All failures are expected and conservative: ADAUSDT fails the symbol-level
spread gate (`WIDE_MEDIAN_SPREAD`, median spread 3.52bps > 3.0bps).

### Testes rodados

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests --basetemp=pytest_temp_sprint8_gate_expand -o cache_dir=pytest_temp_sprint8_gate_expand/.pytest_cache
Result: 190 passed, 1 pytest config warning.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src tests scripts
Result: passed.

git diff --check
Result: passed.
```

### Decisao e proximo passo

```text
Sprint 8 may now open, SCOPED to the 31 candidate pairs with genuine
June-2023 cost-gated evidence. The 10 ADAUSDT failed pairs and any month
outside June 2023 remain statistical-only / blocked from cost-gated claims.

Do not delete raw ZIPs yet unless the user explicitly approves after accepting
the evidence state. For future cleanup, keep the manifest, source_review,
summary, gate JSON/CSV, bars CSV, deduped hourly-cost CSV, and duplicate-hours
CSV.
```

## HANDOFF - TASK-007-10 Real Cost-Gated Pilot (ADR-0007, Sprint 8 Scoped Unblock)

### Status

DONE

### Agente

Market Data Agent (implementation + review), QA Agent (independent genuineness review), PM Agent (ADR-0007, orchestration)

### Contexto

Following the definitive `SOURCE_INCOMPLETE_FAIL_CLOSED` finding (see the
TASK-007-10 closure handoff below), the user asked to do what's needed to
advance safely. Downloading the full verified ~11-month/20-symbol bookTicker
set was estimated at ~273GB compressed and infeasible in this session. A first
attempt to download one MONTH of bookTicker for one symbol (ETCUSDT, the
smallest target) caused an out-of-memory kill (exit 137) because
`read_zip_csv` loads the whole decompressed CSV into memory at once, and a
monthly archive for a mid-cap symbol decompresses into multiple GB.

### O que foi feito

- Wrote ADR-0007 in `DECISIONS.md`: cost-gated PASS claims must be scoped to
  the exact verified evidence window (symbols/dates/granularity), not implied
  to cover the full 36-month backtest window; historical bookTicker ingestion
  must use daily archives processed one symbol-day at a time, never a whole
  month in memory; going forward, the existing live Market Data Plane
  (Sprint 5/6 `BookFeatures`) is the source of truth for forward cost
  evidence.
- Added `BinanceDataFamily.BOOK_TICKER` to `src/research/historical_dataset.py`
  (purely additive: new enum member + filename/relative_path branches; default
  families list in `build_archive_plan` unchanged, so existing callers are
  unaffected).
- Wrote `scripts/run_sprint7_execution_cost_download.py`: downloads daily
  bookTicker archives (not monthly), verifies SHA256 checksum before
  normalizing (reusing `verify_checksum_file`/`read_zip_csv` from
  `historical_dataset.py`), normalizes and aggregates one symbol-day at a
  time, and frees the raw tick-level frame (`del raw, normalized`) before the
  next day -- bounding peak memory to one symbol-day regardless of scope.
- Ran it for real (live network, real checksums) for 6 non-BTC/ETH top
  candidate symbols (ARBUSDT, OPUSDT, ADAUSDT, DOTUSDT, ETCUSDT, AVAXUSDT) for
  June 2023 (within the verified sub-window). Produced 4326 real hourly spread
  rows with no errors.
- Built a scoped bars/summary input (6 symbols, June 2023, 4320 bars) and ran
  the existing `scripts/run_sprint7_execution_cost_evidence.py` against the
  real hourly cost data with a scoped `--probe-binance-source` (returns
  `complete_for_window=true` for this narrow scope, correctly, since the
  archives really do exist for it).
- Result: `cost_gated_pass=true` overall; 5 of 6 candidate pairs pass
  (ARBUSDT/OPUSDT, ARBUSDT/ETCUSDT, ARBUSDT/DOTUSDT, AVAXUSDT/DOTUSDT,
  DOTUSDT/ETCUSDT); ADAUSDT/DOTUSDT correctly rejected because ADAUSDT's
  median spread (3.52bps) exceeds the 3.0bps threshold.
- Market Data Agent reviewed the new download code and enum change: PASSA.
  One P3 (non-blocking): `normalize_symbol_archive_files` has no explicit
  guard against `BOOK_TICKER` being misused via the kline-oriented
  `build_archive_plan`/`normalize_archive_plan` path; not exercised by the
  actual code path used here.
- QA Agent independently re-verified the result was not fabricated: checked
  sample counts (tens of thousands to ~560k ticks/hour, consistent with real
  bookTicker volume), spread variance across hours/symbols (hundreds of
  distinct values, no repeated/interpolated pattern), and confirmed the
  ADAUSDT rejection arithmetic matches the stated threshold exactly. PASSA,
  explicitly confirmed the result is genuine and correctly scoped to
  June 2023 / 6 symbols only.

### Arquivos alterados

```text
src/research/historical_dataset.py
scripts/run_sprint7_execution_cost_download.py
tests/test_historical_dataset.py
tests/test_execution_cost_download.py
data/research/binance_public/cost_pilot/raw/ (real downloaded archives, checksummed)
data/research/binance_public/cost_pilot/pilot_202306_hourly_cost.csv
data/research/binance_public/cost_pilot/pilot_202306_bars.csv
data/research/binance_public/cost_pilot/pilot_202306_summary.json
data/research/binance_public/cost_pilot/pilot_202306_source_review.json
data/research/binance_public/cost_pilot/pilot_202306_execution_cost_gate.json
data/research/binance_public/cost_pilot/pilot_202306_execution_cost_gate.csv
project_control/DECISIONS.md (ADR-0007)
project_control/TASK_BOARD.md
project_control/CURRENT_SPRINT.md
project_control/PROJECT_STATE.md
project_control/BLOCKERS.md
project_control/RISKS.md
project_control/TEST_MATRIX.md
project_control/DAILY_LOG.md
reports/research_sprint_07.md
```

### Testes rodados

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests -q
Result: passed, 190 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research scripts tests
Result: passed.

Real network run (not a test): scripts/run_sprint7_execution_cost_download.py
for 6 symbols x 30 days = 180 symbol-days, June 2023. No errors, no OOM.
```

### Decisao e proximo passo

```text
At this handoff's original close, BLOCKER-2026-06-30-S7-REAL-DATASET-GATE was
downgraded from ACTIVE/P1 to PARTIALLY RESOLVED/P2 with a 5-pair scope. This
was superseded by the 2026-07-02 expanded all-candidate June-2023 run recorded
above: Sprint 8 may now open for 31 cost-gated pairs. Any broader claim
(failed ADAUSDT pairs, other months, the full 36-month window) remains
statistical-only and requires either repeating this same real-download
process for more scope, an alternative verified source for 2024-05 through
2026-05, or live Market Data Plane capture once paper/live trading exists.

This older note is superseded by `HANDOFF - Sprint 8 Opening / Next Dispatch`
above. Sprint 8 is now opened in `CURRENT_SPRINT.md`, and TASK-008-01 is the
next READY task.
```

## HANDOFF - TASK-007-10 Historical Execution-Cost Evidence (Closure)

### Status

DONE

### Agente

Market Data Agent (implementation), QA Agent (independent re-review), PM Agent (independent verification against live source)

### O que foi feito

- Implemented `src/research/execution_cost_evidence.py` and
  `scripts/run_sprint7_execution_cost_evidence.py` to probe the real Binance
  Public Data bookTicker archive (monthly and daily S3 prefixes) for all 20
  Sprint 7 accepted symbols across the full 2023-06 through 2026-05 window,
  and to compute a fail-closed cost-gated PASS decision per candidate pair.
- Ran the real probe. Result: `SOURCE_INCOMPLETE_FAIL_CLOSED`. Verified
  top-of-book/L2 coverage exists for only 11 of the 36 required months
  (2023-06 through approximately 2024-04), identically for every one of the
  20 symbols. Binance Public Data does not publish bookTicker archives past
  that point for any of the checked symbols.
- `cost_gated_pass=false` for all 41 candidate pairs, enforced unconditionally
  whenever `source_review.complete_for_window` is false — no code path treats
  missing/incomplete evidence as approved.
- PM independently verified this against the live Binance S3 endpoint
  (`curl` against `s3-ap-northeast-1.amazonaws.com/data.binance.vision`) for
  BTCUSDT: monthly prefix `KeyCount=24, MaxKeys=1000, IsTruncated=false`
  (last archive `2024-04`), daily prefix `KeyCount=640, MaxKeys=1000,
  IsTruncated=false` (last archive `2024-03-30`). This rules out a pagination
  artifact — the coverage gap is real, not a truncated listing.
- QA Agent performed an independent second re-review focused specifically on
  whether S3 pagination (`IsTruncated`/`NextContinuationToken`) could be
  hiding additional months, and whether any code path defaults to "approved"
  on missing evidence. Result: PASSA, confirmed both concerns are unfounded
  for this run.

### Arquivos alterados

```text
src/research/execution_cost_evidence.py
scripts/run_sprint7_execution_cost_evidence.py
tests/test_execution_cost_evidence.py
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_execution_cost_source_review.json
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_execution_cost_gate.json
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_execution_cost_gate.csv
reports/research_sprint_07.md
project_control/TASK_BOARD.md
project_control/CURRENT_SPRINT.md
project_control/PROJECT_STATE.md
project_control/BLOCKERS.md
project_control/RISKS.md
project_control/TEST_MATRIX.md
project_control/DAILY_LOG.md
```

### Testes rodados

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_execution_cost_evidence.py -q
Result: passed, 4 tests (QA re-review independently re-ran and confirmed).

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests -q
Result: passed, 186 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research/execution_cost_evidence.py tests/test_execution_cost_evidence.py scripts/run_sprint7_execution_cost_evidence.py
Result: passed.
```

### Findings nao bloqueantes (P2, follow-up recomendado)

```text
1. _fetch_s3_objects/parse_s3_list_objects do not handle S3 pagination
   (IsTruncated/NextContinuationToken). Harmless today because KeyCount is
   far below MaxKeys=1000 for both prefixes checked, but could silently
   under-count coverage in the future if per-symbol object counts grow past
   1000 (e.g. years of accumulated daily archives). Add continuation-token
   handling before depending on this probe at larger scale.
2. Result is identical (11/36 months, 30.56% coverage) across all 20 symbols,
   which is expected given Binance appears to have stopped publishing
   bookTicker archives (both granularities) for USD-M futures symbols
   around 2024-04 broadly, not per-symbol.
```

### Decisao pendente (nao e tarefa de execucao)

```text
This finding is definitive, not a pending-execution gap. TASK-007-10 cannot be
advanced further by re-running the same probe. Sprint 8 start now depends on a
PM/stakeholder policy decision:
a. find and verify an alternative top-of-book/L2 source covering the full
   window;
b. shrink the Sprint 7 research window to the verified ~11-month sub-period
   and rerun the statistical + cost gate on it;
c. redefine cost-gated PASS policy via a new ADR (e.g. accept forward-collected
   live execution-cost evidence instead of retroactive historical coverage);
d. keep Sprint 8 blocked indefinitely.
See BLOCKER-2026-06-30-S7-REAL-DATASET-GATE for the full blocker record.
```

## HANDOFF - TASK-007-09 Historical Binance Loader/Normalizer (Closure)

### Status

DONE

### Agente

Market Data Agent (review), QA Agent (review), PM Agent (fallback implementation)

### O que foi feito

- Market Data Agent reviewed `src/research/historical_dataset.py` for
  Binance path/URL correctness, checksum-before-normalization enforcement,
  funding as-of join correctness (no look-ahead), sidecar completeness, and
  global mutable state. Result: PASSA. Two P3 findings (optional
  `funding_mark_price` field not populated; one indirect fail-closed fallback
  path in `_coerce_funding_columns` that could be more explicit). No P1/P2.
- QA Agent reviewed the same module plus `tests/test_historical_dataset.py`
  and `tests/test_pair_selection.py` for fail-closed behavior: checksum
  mismatch, headerless-CSV handling, gap no-forward-fill, runner smoke, and
  `select_pairs` integration. Result: PASSA. Two P2 findings (no direct
  regression test for `LONG_HISTORY_GAP` rejection in pair selection, though
  manually verified correct; zero test coverage — not even mocked — for the
  real-network `download_archives` path, safe for offline CI but untested
  error handling) and one P3 (checksum-mismatch test could be split from the
  malformed-CSV case). No P1.
- Both reviews returned no blocking findings. TASK-007-09 moved to DONE.

### Arquivos alterados

```text
project_control/TASK_BOARD.md
project_control/CURRENT_SPRINT.md
project_control/PROJECT_STATE.md
project_control/RISKS.md
project_control/TEST_MATRIX.md
project_control/DAILY_LOG.md
```

### Findings nao bloqueantes (follow-up recomendado, nao bloqueia DONE)

```text
P3: populate funding_mark_price when present in Binance funding CSV.
P3: make the _coerce_funding_columns fallback path more explicit.
P2: add a direct regression test for LONG_HISTORY_GAP rejection in
    tests/test_pair_selection.py.
P2: add a mocked-network regression test for download_archives/
    _download_archive error handling (timeout, checksum mismatch
    post-download) before relying on this path for unattended real downloads.
```

## HANDOFF - TASK-007-10 Historical Execution-Cost Evidence (superseded, see closure above)

### Status

IN_PROGRESS

### Agente

Market Data Agent

### Sprint atual

Sprint 7 - Research base: pair selection, Kalman e OU

### Task

Produzir evidencia historica verificavel de top-of-book/L2, spread e custo de
execucao para os 41 pares estatisticos gerados pelo Sprint 7 real-dataset gate.

### Contexto obrigatorio

```text
TASK-007-09 executou o dataset real 2023-06 through 2026-05:
- 20 simbolos aceitos;
- 526080 barras 1h normalizadas;
- 41 pares estatisticos aceitos;
- 149 pares rejeitados por pair selection.

O bloqueio atual e cost_gated_pass=false por falta de evidencia historica
verificada de top-of-book/L2/spread/custo. Nao avance Sprint 8 com candidatos
estatisticos sem essa evidencia.
```

### Arquivos permitidos

```text
src/research/
tests/
scripts/
reports/
docs/historical_dataset.md
project_control/
tasks/sprint_07/
data/research/
```

### Arquivos proibidos

```text
src/live/
src/execution/
src/ledger/
src/models/
notebooks/
```

### Criterio de pronto

```text
1. Fonte historica de custo documentada com periodo, simbolos, granularidade,
   campos, checksums/proveniencia e limites.
2. Se a fonte existir, dados normalizados com schema estavel.
3. Join com barras/pairs sem look-ahead.
4. Median, p95 e p99 de spread/custo calculados por simbolo e par.
5. Cobertura temporal, gaps e stale stats reportados.
6. Evidencia ausente/incompleta falha fechada.
7. cost_gated_pass=true somente para pares com evidencia completa e dentro dos
   limites.
8. Relatorio, blocker, test matrix e handoff atualizados.
```

### Testes obrigatorios

```text
pytest tests/test_pair_selection.py
pytest tests/test_historical_dataset.py
pytest <novo teste de custo historico>
ruff check src/research tests scripts
```

### Handoff esperado

```text
Informar fonte avaliada, artefatos gerados, pares aprovados/reprovados por
custo, testes rodados, risco residual e decisao do gate Sprint 8.
```

## HANDOFF - TASK-007-09 Historical Binance Loader/Normalizer (superseded, see closure above)

### Status

IN_REVIEW (superseded by DONE closure above)

### Agente

PM Agent fallback for Quant Research Agent

### O que foi feito

- Implemented and hardened the Binance Public Data historical loader path in
  `src/research/historical_dataset.py`.
- Kept deterministic monthly URL/path planning for OHLCV, mark price, index
  price, premium index, and funding families.
- Kept SHA256 verification before archive normalization.
- Updated checksum parsing to accept sha256sum-style `*filename` markers.
- Updated ZIP CSV reading to preserve the first row for headerless Binance
  public-data files.
- Preserved no-forward-fill return behavior across hourly gaps.
- Verified normalized archive plans can feed `select_pairs`.
- Verified `scripts/run_sprint7_historical_dataset.py` with a local
  no-download smoke using synthetic ZIP/checksum fixtures.
- Added `scripts/run_sprint7_research_gate.py` to run stationarity, Kalman, OU,
  and rolling z-score diagnostics against real normalized candidate pairs.
- Ran the full 2023-06 through 2026-05 Binance USD-M dataset and generated the
  statistical Sprint 7 research gate artifacts.

### Arquivos alterados

```text
src/research/historical_dataset.py
tests/test_historical_dataset.py
scripts/run_sprint7_historical_dataset.py
scripts/run_sprint7_research_gate.py
reports/research_sprint_07.md
project_control/CURRENT_SPRINT.md
project_control/DAILY_LOG.md
project_control/HANDOFFS.md
project_control/PROJECT_STATE.md
project_control/TASK_BOARD.md
project_control/TEST_MATRIX.md
tasks/sprint_07/TASK-007-09-historical-loader-runner.md
```

### Testes rodados

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_historical_dataset.py tests/test_pair_selection.py --basetemp=pytest_temp_run_task00709_focus -o cache_dir=pytest_temp_run_task00709_focus/.pytest_cache
Result: passed, 21 tests, 1 pytest config warning for unknown asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_historical_dataset.py tests/test_pair_selection.py --basetemp=pytest_temp_run_task00709_gate_focus -o cache_dir=pytest_temp_run_task00709_gate_focus/.pytest_cache
Result: passed, 22 tests, 1 pytest config warning for unknown asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests --basetemp=pytest_temp_run_sprint7_real_gate_all -o cache_dir=pytest_temp_run_sprint7_real_gate_all/.pytest_cache
Result: passed, 182 tests, 1 pytest config warning for unknown asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research/historical_dataset.py tests/test_historical_dataset.py scripts/run_sprint7_historical_dataset.py
Result: passed.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research/historical_dataset.py tests/test_historical_dataset.py scripts/run_sprint7_historical_dataset.py scripts/run_sprint7_research_gate.py
Result: passed.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check .
Result: failed on pre-existing notebook lint issues in notebooks/01_pair_selection.ipynb
and notebooks/02_kalman_ou.ipynb (`E402`, `E501`, and one unused import). These
notebook lint issues were not introduced by TASK-007-09 and were not changed in
this task.

UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_historical_dataset.py --symbols BTCUSDT --start-month 2023-06 --end-month-exclusive 2023-07 --dataset-version sprint7_real_smoke_202306_btcusdt --data-root /tmp/crypto_pair_trading_sprint7_real_smoke --correlation-window 2
Result: passed.
```

### Execucao real/smoke

```text
Local smoke:
tests/test_historical_dataset.py runs scripts/run_sprint7_historical_dataset.py
with --no-download against synthetic Binance-like ZIP and .CHECKSUM fixtures.

Real one-month smoke:
Downloaded and checksumed BTCUSDT 2023-06 klines, markPriceKlines,
indexPriceKlines, premiumIndexKlines, and fundingRate from Binance Public Data.
Normalized output:
/tmp/crypto_pair_trading_sprint7_real_smoke/normalized/sprint7_real_smoke_202306_btcusdt_bars.csv
Result: 720 normalized bars, BTCUSDT accepted in one-symbol statistical smoke,
no candidate pairs because only one symbol was included.

Real Binance 36 complete-month dataset:
Downloaded, checksumed, normalized, and run for 20 Binance USD-M seed symbols
from 2023-06 through 2026-05.

Normalized bars:
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv
526080 rows plus header.

Pair-selection summary:
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_summary.json
20 accepted symbols, 0 rejected symbols, 41 statistical candidate pairs, 149
rejected pairs.

Research gate:
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.json
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.csv
41 pairs evaluated; 41 statistical-only accepts; 0 statistical rejects;
cost_gated_pass=false because verified historical top-of-book/L2
execution-cost evidence is unavailable.
```

### Revisoes necessarias

```text
Market Data Agent:
- verify Binance Public Data family paths and checksum assumptions;
- verify headerless/headered CSV behavior is acceptable for public archives;
- verify funding as-of semantics and unavailable execution-cost labeling.

QA Agent:
- verify checksum mismatch fail-closed behavior;
- verify no future funding joins;
- verify no forward-fill across gaps;
- verify runner smoke and select_pairs integration.
```

### Pendencias

```text
Formal Market Data Agent review.
Formal QA Agent review.
reports/research_sprint_07.md update with real approved/rejected pair tables.
Final full-suite verification after report/control updates.
Verified historical top-of-book/L2 execution-cost evidence, or explicit
decision to keep Sprint 8 blocked.
```

### Riscos

```text
Cost-gated Sprint 7 PASS remains impossible without verified historical
top-of-book/L2 execution-cost evidence.
Statistical-only accepts prove the research pipeline can rank candidates, but
they do not prove executable edge after spread/slippage/fill costs.
Global ruff currently fails on pre-existing notebook lint issues outside the
TASK-007-09 code path; scoped TASK-007-09 ruff passes.
TASK-007-09 must not touch ledger, execution, live engine, or models.
```

### Proximo passo recomendado

Update the Sprint 7 report with the real run, request Market Data Agent and QA
Agent review for TASK-007-09, then decide whether to add a separate historical
execution-cost evidence task or keep Sprint 8 blocked.

## HANDOFF - TASK-007-06 TASK-007-07 TASK-007-08 Sprint 7 Notebooks, Tests, and Report

### Status

DONE

### Agente

Quant Research Agent + QA Agent + Documentation Agent + PM Agent

### O que foi feito

- Created `notebooks/01_pair_selection.ipynb` with a deterministic synthetic
  normalized-bars workflow using `src/research/pair_selection.py`.
- Created `notebooks/02_kalman_ou.ipynb` with deterministic synthetic Kalman and
  OU diagnostics using `src/research/kalman.py`, `src/research/ou.py`, and
  `src/research/stationarity.py`.
- Updated `reports/research_sprint_07.md` with dataset contract, cleaning
  summary, filters, module status, notebook status, synthetic smoke examples,
  verification, risks, and final conclusion.
- Kept synthetic examples explicitly out of the Sprint 8 gate.
- Updated control state to mark TASK-007-06, TASK-007-07, and TASK-007-08 DONE.
- Added `BLOCKER-2026-06-30-S7-REAL-DATASET-GATE` to prevent Sprint 8 from
  starting before real historical data is run.

### Arquivos alterados

```text
notebooks/01_pair_selection.ipynb
notebooks/02_kalman_ou.ipynb
reports/research_sprint_07.md
project_control/BLOCKERS.md
project_control/CURRENT_SPRINT.md
project_control/DAILY_LOG.md
project_control/HANDOFFS.md
project_control/PROJECT_STATE.md
project_control/TASK_BOARD.md
project_control/TEST_MATRIX.md
```

### Testes rodados

```text
UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_pair_selection.py tests/test_stationarity.py tests/test_kalman.py tests/test_ou.py --basetemp=pytest_temp_run_sprint7_final_core -o cache_dir=pytest_temp_run_sprint7_final_core/.pytest_cache
Result: passed, 31 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests --basetemp=pytest_temp_run_sprint7_final_all -o cache_dir=pytest_temp_run_sprint7_final_all/.pytest_cache
Result: passed, 171 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with ruff ruff check src/research tests/test_pair_selection.py tests/test_stationarity.py tests/test_kalman.py tests/test_ou.py
Result: passed.

Notebook code-cell execution check:
notebooks/01_pair_selection.ipynb: code cells ok.
notebooks/02_kalman_ou.ipynb: code cells ok.
```

### Revisoes

```text
Documentation Agent initial review requested a cleaning-summary section in the
Sprint 7 report.
PM added the cleaning summary.
Documentation Agent re-review returned PASSA.
Quant Research Agent review returned PASSA for TASK-007-07 test coverage.
PM report review result: technical implementation PASSA, Sprint 8 gate NAO
PASSA until verified execution-cost evidence and TASK-007-09 review.
```

### Pares aprovados

```text
Real Binance USD-M dataset: 41 statistical-only accepts after TASK-007-09
research gate; none are cost-gated approved because verified top-of-book/L2
execution-cost evidence is unavailable.
Synthetic smoke example only: BTCUSDT/ETHUSDT candidate with score 0.998467.
```

### Pares rejeitados

```text
Real Binance USD-M dataset: 149 pairs rejected by pair selection.
Synthetic smoke example only:
- BTCUSDT/SOLUSDT rejected for LOW_CORRELATION.
- ETHUSDT/SOLUSDT rejected for LOW_CORRELATION.
- WEAKUSDT rejected for liquidity and funding reasons.
```

### Pendencias

```text
Historical note: at this earlier point, TASK-007-09 review and verified
execution-cost evidence were still required, so Sprint 8 remained blocked.
This was superseded by TASK-007-10 and the 2026-07-02 Sprint 8 opening handoff.
```

### Riscos

```text
Synthetic examples prove workflow shape only, not market edge.
Cost-gated PASS remains impossible without verified historical execution-cost
evidence.
Full-sample diagnostics are exploratory only.
```

### Proximo passo recomendado

Implement or run the historical dataset pipeline for the documented 36
complete-month Binance USD-M window, then repeat the Sprint 7 real-dataset gate.

## HANDOFF - TASK-007-02 TASK-007-03 TASK-007-04 TASK-007-05 Research Core

### Status

DONE

### Agente

Quant Research Agent + PM Agent fallback integration

### O que foi feito

- Implemented `src/research/pair_selection.py` with in-memory normalized-bar
  pair selection, symbol rejection reasons, pair rejection reasons,
  deterministic ranking, rolling no-look-ahead correlation, exploratory
  full-sample correlation marking, conditional execution-cost filters, and
  conservative direction-agnostic funding carry.
- Implemented `src/research/stationarity.py` with standardized ADF/KPSS
  wrappers, preliminary half-life, rolling correlation, spread stability, and
  combined stationarity decisions.
- Implemented `src/research/kalman.py` with sequential dynamic beta/alpha
  estimation, spread_t, innovation, innovation variance, state covariance, and
  beta instability flags.
- Implemented `src/research/ou.py` with OU theta/mu/sigma/half-life estimation,
  theta <= 0 rejection/warning, rolling no-look-ahead z-score, and exploratory
  full-sample z-score marking.
- Updated `src/research/__init__.py` exports for pair selection, stationarity,
  Kalman, and OU helpers.
- Added focused tests for pair selection, stationarity, Kalman, and OU.
- Addressed Backtest review findings by making rolling correlation explicitly
  no-look-ahead, failing closed on partial execution-cost quality evidence, and
  requiring real tail-spread evidence for verified p95/p99 spread filters.
- Addressed QA review finding by correcting OU continuous sigma scaling for
  non-unit `dt`.

### Arquivos alterados

```text
src/research/__init__.py
src/research/pair_selection.py
src/research/stationarity.py
src/research/kalman.py
src/research/ou.py
tests/test_pair_selection.py
tests/test_stationarity.py
tests/test_kalman.py
tests/test_ou.py
project_control/CURRENT_SPRINT.md
project_control/DAILY_LOG.md
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
project_control/PROJECT_STATE.md
project_control/TEST_MATRIX.md
```

### Testes rodados

```text
UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_pair_selection.py tests/test_stationarity.py tests/test_kalman.py tests/test_ou.py --basetemp=pytest_temp_run_sprint7_core2 -o cache_dir=pytest_temp_run_sprint7_core2/.pytest_cache
Result: passed, 28 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests --basetemp=pytest_temp_run_sprint7_all -o cache_dir=pytest_temp_run_sprint7_all/.pytest_cache
Result: passed, 168 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with ruff ruff check src/research tests/test_pair_selection.py tests/test_stationarity.py tests/test_kalman.py tests/test_ou.py
Result: passed.

UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_pair_selection.py tests/test_stationarity.py tests/test_kalman.py tests/test_ou.py --basetemp=pytest_temp_run_sprint7_core_reviewed2 -o cache_dir=pytest_temp_run_sprint7_core_reviewed2/.pytest_cache
Result: passed, 31 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests --basetemp=pytest_temp_run_sprint7_full_reviewed -o cache_dir=pytest_temp_run_sprint7_full_reviewed/.pytest_cache
Result: passed, 171 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_pair_selection.py tests/test_stationarity.py tests/test_kalman.py tests/test_ou.py --basetemp=pytest_temp_run_sprint7_final_core -o cache_dir=pytest_temp_run_sprint7_final_core/.pytest_cache
Result: passed, 31 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests --basetemp=pytest_temp_run_sprint7_final_all -o cache_dir=pytest_temp_run_sprint7_final_all/.pytest_cache
Result: passed, 171 tests, 1 pytest config warning for asyncio_mode.
```

### Revisoes

```text
Backtest Agent initial review requested changes:
- rolling_correlation included the current row while claiming no-look-ahead;
- VERIFIED execution-cost quality did not fail closed on partial missing quality;
- p95/p99 spread could be fabricated from median-only evidence.

PM fixes applied with regression tests.
Backtest Agent re-review returned PASSA.

QA Agent initial review requested changes:
- OU continuous sigma formula incorrectly multiplied by dt after theta already
  included dt.

PM fix applied with non-unit-dt regression test.
QA Agent re-review returned PASSA.
```

### Pendencias

```text
TASK-007-06 notebooks, TASK-007-07 research test review, and TASK-007-08 final
report remain pending.
```

### Riscos

```text
Pair selection currently consumes normalized in-memory data only; actual
downloaders/loaders remain future work.
Full-sample correlation and full-sample z-score are explicitly exploratory and
must not be used as no-look-ahead signal evidence.
Execution-spread filters are conditional and fail closed for cost-gated PASS
when historical top-of-book/L2 evidence is unavailable.
Kalman and OU parameters are research estimates, not live trading permission.
```

## HANDOFF - TASK-007-01 Historical Dataset Minimum

### Status

DONE

### Agente

Quant Research Agent

### O que foi definido

- Defined the minimum Sprint 7 historical research dataset for Binance USD-M
  futures pairs.
- Defined the initial seed universe with 20 USDT perpetual symbols.
- Defined the canonical research window as 36 complete UTC months:
  `2023-06-01T00:00:00Z <= open_time < 2026-06-01T00:00:00Z`.
- Defined `1h` UTC bars as the canonical research frequency.
- Defined OHLCV, mark price, index price, premium index, and funding as
  required dataset families.
- Defined historical top-of-book/L2 spread evidence as conditional: required for
  cost-gated Sprint 7 PASS, but not assumed available from Binance Public Data.
- Defined required fields, checksum/provenance fields, cleaning rules, gap
  rules, and no-forward-fill constraints.
- Defined minimum history, liquidity, conditional spread, funding, and pair
  pre-filters.
- Defined conservative absolute funding carry as the pair pre-filter formula.
- Documented explicit look-ahead controls for full-sample exploration,
  rolling/expanding features, funding as-of joins, optional execution-spread
  joins, and universe selection.

### Review findings addressed

```text
Market Data Agent requested changes:
P1: Binance Public Data does not provide complete verified bookTicker coverage
    for the full 2023-06 through 2026-05 window.
P2: Original 2023-07-01 through 2026-06-30 window was not 36 complete months.
P3: Pair funding carry needed an explicit bps/day formula.

PM corrected the dataset contract. Market Data Agent re-review passed with no
remaining P1/P2/P3 findings.
```

### Fonte / periodo / frequencia

```text
Source: Binance Public Data archive, https://data.binance.vision/
OHLCV: data/futures/um/monthly/klines/{SYMBOL}/1h/
Mark price: data/futures/um/monthly/markPriceKlines/{SYMBOL}/1h/
Index price: data/futures/um/monthly/indexPriceKlines/{SYMBOL}/1h/
Premium index: data/futures/um/monthly/premiumIndexKlines/{SYMBOL}/1h/
Funding: data/futures/um/monthly/fundingRate/{SYMBOL}/
Optional execution spread: verified historical top-of-book/L2 source only.
Period: 2023-06-01T00:00:00Z <= open_time < 2026-06-01T00:00:00Z
Frequency: canonical 1h UTC bars; funding event-time as-of sidecar.
```

### Arquivos alterados

```text
docs/historical_dataset.md
docs/index.md
reports/research_sprint_07.md
project_control/HANDOFFS.md
```

### Testes rodados

```text
No automated tests are required for TASK-007-01.
Documentation-only task; no data was downloaded and no exchange client was
implemented.
```

### Pendencias

```text
Future implementation tasks must create actual loaders/normalizers separately
and preserve checksumed dataset versioning.
Pair selection, stationarity, Kalman, OU, notebooks, and final research report
sections remain pending Sprint 7 work.
```

### Riscos

```text
The seed universe is biased toward symbols known to be liquid on 2026-06-30;
walk-forward evaluation must avoid survivorship bias.
Public archive files can be corrected after publication; checksums and dataset
versions are mandatory.
OHLCV/mark/index/premium data alone cannot prove executable cost; verified
top-of-book/L2 evidence is required before claiming cost-gated acceptance.
Funding may dominate apparent mean reversion and must be included in pair
pre-filters.
Any full-sample ranking is exploratory only and must not be treated as
no-look-ahead signal evidence.
```

### Proximo passo recomendado

TASK-007-02 can implement pair selection against this documented dataset
contract.

## HANDOFF - Sprint 7 Opening

### Status

READY

### Agente

PM Agent

### O que foi feito

- Pre-Sprint 7 gate for Sprints 5 and 6 was revalidated and passed.
- `project_control/PROJECT_STATE.md` was moved to Sprint 7 - Research base.
- `project_control/CURRENT_SPRINT.md` was updated with Sprint 7 scope, gate,
  deliverables, tests, and task table.
- `project_control/TASK_BOARD.md` was updated with TASK-007-01 through
  TASK-007-08 in READY.
- `tasks/sprint_07/` was created with task templates for dataset definition,
  pair selection, stationarity, Kalman, OU, notebooks, tests, and report.
- `project_control/TEST_MATRIX.md` was updated with Sprint 7 required checks.

### Arquivos alterados

```text
project_control/PROJECT_STATE.md
project_control/CURRENT_SPRINT.md
project_control/TASK_BOARD.md
project_control/TEST_MATRIX.md
project_control/HANDOFFS.md
tasks/sprint_07/TASK-007-01-historical-dataset.md
tasks/sprint_07/TASK-007-02-pair-selection.md
tasks/sprint_07/TASK-007-03-stationarity.md
tasks/sprint_07/TASK-007-04-kalman-filter.md
tasks/sprint_07/TASK-007-05-ou-estimator.md
tasks/sprint_07/TASK-007-06-exploratory-notebooks.md
tasks/sprint_07/TASK-007-07-research-tests.md
tasks/sprint_07/TASK-007-08-research-report.md
```

### Testes rodados

```text
No Sprint 7 implementation tests exist yet.
Pre-Sprint 7 gate verification is recorded in the Sprint 5/6 Gate Correction
handoff below.
```

### Proximo passo recomendado

Delegate TASK-007-01 to Quant Research Agent and require Market Data Agent
review before implementation tasks consume the dataset definition.

## HANDOFF - TASK-031 TASK-032 TASK-033 Sprint 5/6 Gate Correction

### Status

DONE

### Agente

Market Data Agent + Execution / Risk Agent + PM Agent

### O que foi feito

- Added `LocalOrderBook` / `BookBuilder` with deterministic snapshot and diff
  application.
- Added explicit local-book top-of-book accessors: `best_bid`, `best_ask`,
  `best_bid_level`, and `best_ask_level`.
- Added local-book sequence handling: old updates are discarded, sequence gaps
  invalidate the book, and a new snapshot can resync state.
- Added zero-quantity level removal.
- Added local-book age/staleness helpers: `book_age_ms`, `is_stale`, and
  `valid_at`.
- Added explicit `book_age_ms` and `in_sync` fields to
  `BookExecutionFeatures`.
- Preserved fail-closed execution feature behavior for stale, invalid,
  resync-required, malformed, crossed, or empty books.
- Added focused regression tests for the corrected gate checklist.

### Arquivos alterados

```text
src/market_data/book_builder.py
src/market_data/__init__.py
src/features/execution_features.py
tests/test_book_builder.py
tests/test_execution_features.py
project_control/BLOCKERS.md
project_control/DAILY_LOG.md
project_control/HANDOFFS.md
project_control/PROJECT_STATE.md
project_control/TASK_BOARD.md
tasks/sprint_05/TASK-031-local-order-book-gate-correction.md
tasks/sprint_06/TASK-032-bookfeatures-health-fields.md
tasks/sprint_06/TASK-033-revalidate-s5-s6-gate.md
```

### Testes rodados

```text
UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_book_health.py tests/test_execution_features.py tests/test_slippage_estimator.py --basetemp=pytest_temp_run_s7_gate_precheck -o cache_dir=pytest_temp_run_s7_gate_precheck/.pytest_cache
Result: passed, 37 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_book_builder.py tests/test_book_health.py tests/test_execution_features.py tests/test_slippage_estimator.py --basetemp=pytest_temp_run_s5s6_gate_fix -o cache_dir=pytest_temp_run_s5s6_gate_fix/.pytest_cache
Result: passed, 47 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests --basetemp=pytest_temp_run_s5s6_gate_fix_all -o cache_dir=pytest_temp_run_s5s6_gate_fix_all/.pytest_cache
Result: passed, 140 tests, 1 pytest config warning for asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --with ruff ruff check src/market_data src/features src/execution/slippage_estimator.py tests/test_book_builder.py tests/test_book_health.py tests/test_execution_features.py tests/test_slippage_estimator.py
Result: passed.

UV_CACHE_DIR=.uv-cache uv run --with ruff ruff check .
Result: passed.
```

### Revisoes

```text
Market Data Agent completed TASK-031.
Execution / Risk Agent completed TASK-032.
QA / Chaos Testing Agent re-review passed TASK-033 and found no P1/P2/P3
issues.
```

### Pendencias

```text
None for the Sprint 5/6 gate correction.
BLOCKER-2026-06-30-S5S6-GATE-LOCAL-BOOK was closed.
```

### Riscos encontrados

```text
LocalOrderBook is an in-memory pure helper only; it does not fetch snapshots,
connect to WebSocket streams, persist book state, or attempt automatic gap
recovery without a fresh snapshot.
FeatureCache remains in-memory only.
The pytest asyncio_mode warning remains because pytest-asyncio is not installed
in the ephemeral test environment.
```

### Proximo passo recomendado

Sprint 7 control state was opened. Do not start Sprint 8 without explicit user
authorization.

## HANDOFF - TASK-026 TASK-027 TASK-028 TASK-029 TASK-030 Sprint 6 Execution Features and Slippage

### Status

DONE

### Agente

Execution Features / Slippage Implementer

### O que foi feito

- Created `src/features/execution_features.py` with `BookExecutionFeatures`, book levels, depth buckets, volatility state, and pure helper functions.
- Implemented correct `mid_price` and `spread_bps`.
- Implemented 5bps and 10bps bid/ask depth aggregation.
- Implemented deterministic order book imbalance.
- Implemented rolling `volatility_1s` and `volatility_5s` without future data and without DataFrame/Pandas hot path.
- Implemented fail-closed execution feature usability for stale, invalid, crossed/empty, or resync-required book evidence.
- Created `src/execution/slippage_estimator.py` with deterministic book consumption: buys consume asks and sells consume bids.
- Returned explicit `INSUFFICIENT_LIQUIDITY` and `INVALID_REQUEST` failure reasons from slippage estimation.
- Created `src/market_data/feature_cache.py` with latest-by-symbol storage and stale fail-closed lookups.
- Added focused Sprint 6 tests.
- PM corrected QA P1 findings so malformed book levels fail closed and invalid slippage requests return `INVALID_REQUEST`.
- Updated control files to `DONE`; Sprint 7 was not opened.

### Arquivos alterados

```text
src/features/execution_features.py
src/features/__init__.py
src/execution/slippage_estimator.py
src/execution/__init__.py
src/market_data/feature_cache.py
src/market_data/__init__.py
tests/test_execution_features.py
tests/test_slippage_estimator.py
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
project_control/PROJECT_STATE.md
project_control/TEST_MATRIX.md
```

### Testes rodados

```text
pytest tests/test_execution_features.py
Result: passed, 10 tests.

pytest tests/test_slippage_estimator.py
Result: passed, 7 tests.

pytest tests/test_execution_features.py --basetemp=pytest_temp_run_s6_features2 -o cache_dir=pytest_temp_run_s6_features2/.pytest_cache
Result: passed, 7 tests.

pytest tests/test_slippage_estimator.py --basetemp=pytest_temp_run_s6_slippage2 -o cache_dir=pytest_temp_run_s6_slippage2/.pytest_cache
Result: passed, 5 tests.

pytest tests --basetemp=pytest_temp_run_s6_all2 -o cache_dir=pytest_temp_run_s6_all2/.pytest_cache
Result: passed, 125 tests.

pytest tests --basetemp=pytest_temp_run_s6_p1_all -o cache_dir=pytest_temp_run_s6_p1_all/.pytest_cache
Result: passed, 130 tests after PM P1 corrections.

ruff check src\features src\execution\slippage_estimator.py src\market_data\feature_cache.py tests\test_execution_features.py tests\test_slippage_estimator.py
Result: passed.
```

### Revisoes

```text
Execution / Risk Agent review passed TASK-026 and TASK-029 with no blocking findings.
Market Data Agent review passed TASK-027 and TASK-028 with no blocking findings.
QA / Chaos Testing Agent found P1 gaps for malformed book levels and invalid slippage requests.
PM Agent corrected the P1 gaps with regression tests.
QA / Chaos Testing Agent re-review passed TASK-030 and Sprint 6 gate with no remaining blockers.
The TEST_MATRIX row "Book stale bloqueia entrada" remains pending because full Execution Risk Gate is explicitly out of Sprint 6 implementation scope.
```

### Riscos encontrados

```text
Helpers are pure and do not query exchanges, Ledger, live connectors, or persistence; future callers must provide trusted local book health, staleness, and snapshot resync evidence.
FeatureCache is in-memory only and fail-closed on stale lookups; persistence and cross-process sharing remain future work.
Default pytest_temp cache path can emit Windows cache permission warnings; fresh --basetemp runs pass cleanly apart from the existing asyncio_mode config warning.
```

### Proximo passo recomendado

Sprint 6 gate passed. Wait for explicit user confirmation before starting Sprint 7 - Research Base.

## HANDOFF - TASK-021 TASK-022 TASK-023 Market Data Book Health Helpers

### Status

DONE

### Agente

Market Data Agent

### O que foi feito

- Created `src/market_data/book_health.py` with pure L2 book health helpers.
- Added frozen dataclasses for `L2BookUpdate`, `BookHealthState`, `SnapshotEvidence`, and decision results.
- Added `BookHealthStatus`, `BookHealthReason`, and `SnapshotResyncDecisionType` enums.
- Classified initial and in-sequence L2 updates as healthy/valid and entry eligible.
- Classified sequence gaps as invalid, preserving previous good sequence and blocking entry eligibility.
- Classified stale book evidence as invalid and entry ineligible.
- Required snapshot resync for incomplete snapshot evidence, snapshot/local sequence mismatch, or invalid local book status.
- Exported the market-data API from `src/market_data/__init__.py`.
- Added focused Sprint 5 unit coverage in `tests/test_book_health.py`.
- Updated Sprint 5 control files without advancing to Sprint 6.

### Arquivos alterados

```text
src/market_data/book_health.py
src/market_data/__init__.py
tests/test_book_health.py
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
project_control/CURRENT_SPRINT.md
project_control/PROJECT_STATE.md
project_control/TEST_MATRIX.md
```

### Testes rodados

```text
pytest tests/test_book_health.py
Result: passed, 20 tests after PM-added missing snapshot sequence regression.

pytest tests
Result: failed before EventStore tests because pytest could not remove default pytest_temp on Windows: PermissionError [WinError 5].

pytest tests --basetemp=pytest_temp_run_s5_market_final -o cache_dir=pytest_temp_run_s5_market_final\.pytest_cache
Result: passed, 112 tests.

pytest tests --basetemp=pytest_temp_run_s5_gate_all -o cache_dir=pytest_temp_run_s5_gate_all/.pytest_cache
Result: passed, 113 tests.

ruff check src\market_data tests\test_book_health.py
Result: passed.
```

### Revisoes

```text
Execution / Risk Agent review passed TASK-021 and TASK-023 with no blocking findings.
QA / Chaos Testing Agent review passed TASK-022 and TASK-024 with no blocking findings.
PM gate review passed TASK-025.
```

### Riscos encontrados

```text
Helpers are pure and do not query exchanges, Ledger, execution, live connectors, or persistence; future callers must supply complete sequence, staleness, and snapshot evidence.
Default pytest_temp can be locked in this Windows environment; use a fresh --basetemp for full-suite verification when needed.
```

### Proximo passo recomendado

Sprint 6 - Execution Features and Slippage has started.

## HANDOFF - TASK-024 TASK-025 Sprint 5 Tests and Gate Review

### Status

DONE

### Agente

QA / Chaos Testing Agent + PM Agent

### O que foi feito

- Reviewed Sprint 5 focused coverage for gap, stale book, snapshot mismatch, incomplete snapshot, missing snapshot sequence, and healthy no-resync behavior.
- Confirmed Execution / Risk review passed entry-blocking semantics.
- Confirmed QA / Chaos review passed gap/stale/resync behavior.
- Updated `project_control/TEST_MATRIX.md`.
- Created `reports/sprint_05_review.md`.
- Moved TASK-021 through TASK-025 to DONE.
- Opened Sprint 6 control state without starting Sprint 7.

### Arquivos alterados

```text
tests/test_book_health.py
project_control/TASK_BOARD.md
project_control/CURRENT_SPRINT.md
project_control/PROJECT_STATE.md
project_control/TEST_MATRIX.md
project_control/HANDOFFS.md
project_control/DAILY_LOG.md
reports/sprint_05_review.md
```

### Testes rodados

```text
pytest tests/test_book_health.py --basetemp=pytest_temp_run_s5_gate -o cache_dir=pytest_temp_run_s5_gate/.pytest_cache
Result: passed, 20 tests.

pytest tests --basetemp=pytest_temp_run_s5_gate_all -o cache_dir=pytest_temp_run_s5_gate_all/.pytest_cache
Result: passed, 113 tests.

ruff check src\market_data tests\test_book_health.py
Result: passed.
```

### Pendencias

```text
Sprint 6 implementation and review remain pending.
```

### Riscos encontrados

```text
Sprint 6 must not expose execution features as usable unless book health, staleness, and resync evidence all allow it.
```

### Proximo passo recomendado

Delegate Sprint 6 feature, slippage, and cache implementation.

## Initialization Handoff

Owner: PM Agent

Status: Complete

Summary:

```text
Created initial project control structure and Sprint 1 task specs.
No trading implementation has started.
Sprint 1 tasks are READY for specialized agents.
```

Files created:

```text
project_control/*
tasks/sprint_01/*
```

Tests run:

```text
Not applicable - documentation/control initialization only.
```

Pending:

```text
Delegate Sprint 1 tasks.
Create docs/ deliverables through assigned agents.
Run documentation review against Sprint 1 gate.
```

## Review Handoff - Sprint 1 Readiness

Owner: PM Agent

Status: Complete

Summary:

```text
Architect, Ledger/Recovery, and QA/Chaos reviewers found no P0 blockers to start Sprint 1.
P1 findings were incorporated into control files and task definitions as closure criteria.
Sprint 1 remains READY; no implementation work has started.
```

Files updated:

```text
project_control/PROJECT_STATE.md
project_control/INTERFACES.md
project_control/DECISIONS.md
project_control/RISKS.md
project_control/TEST_MATRIX.md
tasks/sprint_01/TASK-002-state-machine.md
tasks/sprint_01/TASK-003-event-contracts.md
tasks/sprint_01/TASK-004-risk-limits.md
tasks/sprint_01/TASK-005-recovery-protocol.md
```

Tests run:

```text
Documentation structure and keyword checks only.
```

## TASK-001 Handoff - Architecture Specification

Owner: Architect Agent

Status: DONE

Summary:

```text
Created docs/architecture.md defining the Market Data Plane, Signal Plane, Execution Plane, Ledger Plane, External Dead Man Switch, ML component, and Recovery component.
Documented allowed and forbidden data flows, failure isolation rules, initial deploy assumptions, and core safety invariants.
Kept Signal order prohibition, Ledger transactional truth, durable pre-side-effect ORDER_SENT semantics, ML isolation from exits/hedges/reconciliation, and independent External Dead Man Switch explicit.
```

Files changed:

```text
docs/architecture.md
project_control/HANDOFFS.md
```

Tests/checks run:

```text
rg keyword/invariant checks against docs/architecture.md for required planes, components, data-flow sections, failure isolation, deploy assumptions, and safety invariants.
```

Pending:

```text
None.
```

PM final review:

```text
Passed. Signal/ML order paths are forbidden, ORDER_SENT pre-side-effect semantics are explicit, Ledger truth is explicit, External Dead Man Switch independence is explicit, and initial deploy assumptions are documented.
TASK-001 moved to DONE.
```

## TASK-002 Handoff - State Machine Specification

Owner: Execution / Risk Agent

Status: Ready for Architect review

Summary:

```text
Created docs/state_machine.md defining required trade lifecycle states, inbound/outbound transitions, illegal transition rules, a negative transition matrix, critical failure routing, reconciliation constraints, and ML independence for exits, hedges, lockdown, and recovery.
Updated project_control/INTERFACES.md with the shared Execution/Ledger state machine contract.
Updated project_control/TEST_MATRIX.md with Sprint 1 review checks for state coverage, negative transitions, critical failure routing, and ML-independent safety transitions.
```

Files changed:

```text
docs/state_machine.md
project_control/INTERFACES.md
project_control/HANDOFFS.md
project_control/TEST_MATRIX.md
```

Tests/checks run:

```text
rg -n "IDLE|SIGNAL_ACCEPTED|ENTRY_PENDING|PARTIALLY_FILLED|HEDGING_REQUIRED|POSITION_OPEN|EXIT_PENDING|EXIT_LOCKDOWN|RECONCILING|FLAT|ERROR_SAFE_MODE" docs/state_machine.md project_control/TEST_MATRIX.md project_control/INTERFACES.md
rg -n "ACK_UNKNOWN|partial fill|Partial fill|duplicated fill|Duplicated fill|stale book|Stale book|REST 500/502|Missing WebSocket event|missing WebSocket event|book gap|Book gap|ledger uncertainty|Ledger uncertainty|crash after ORDER_SENT|Crash after ORDER_SENT|crash after partial fill|Crash after partial fill" docs/state_machine.md project_control/TEST_MATRIX.md
rg -n "negative transition matrix|Negative Transition Matrix|ML-independent|ML Independence|No exit, hedge|must not.*ML|depends on ML" docs/state_machine.md project_control/TEST_MATRIX.md project_control/INTERFACES.md
```

Pending:

```text
Architect review.
TASK-002 is now IN_REVIEW after PM intake.
```

## HANDOFF - PM-CONTROL-NORMALIZATION

### Status

DONE

### Agente

PM Agent

### O que foi feito

- Read the updated Multi-Agent Project Manager instructions.
- Created sprint folders `tasks/sprint_01` through `tasks/sprint_28`.
- Normalized key control files to the required PM templates.
- Added versioned contract skeletons to `INTERFACES.md`.
- Recorded ADR-0005 for control file format normalization.
- Moved TASK-002 to IN_REVIEW after local intake and keyword checks.

### Arquivos alterados

- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`
- `project_control/TASK_BOARD.md`
- `project_control/OWNERSHIP.md`
- `project_control/TEST_MATRIX.md`
- `project_control/INTERFACES.md`
- `project_control/DECISIONS.md`
- `project_control/HANDOFFS.md`

### Testes rodados

```text
rg keyword checks for TASK-002 required states, failures, negative matrix, and ML independence.
```

### Pendencias

- Normalize individual Sprint 1 task files to the expanded mandatory task template before delegating the next task.
- Architect review for TASK-002.
- Delegate TASK-003 after task template normalization.

### Riscos encontrados

- Existing task files are clear enough to work, but do not yet exactly match the expanded template from the latest PM instructions.

### Proximo passo recomendado

Normalize Sprint 1 task files, then delegate TASK-003 to the Ledger Agent.

### Proximo agente recomendado

PM Agent, then Ledger Agent.
```

## TASK-003 Handoff - Event Contracts Specification

Owner: Ledger Agent

Status: Ready for Architect review

Summary:

```text
Created docs/event_contracts.md defining P0 lifecycle events and Sprint 1 audit events.
Documented purpose, required fields, idempotency key, producer, and consumer for each P0 event.
Specified durable ORDER_INTENT_CREATED plus ORDER_SENT ordering before exchange side effects, with ORDER_SENT defined as pre-side-effect send attempt and not exchange confirmation.
Specified deterministic, versioned, restart-stable clientOrderId requirements and same-leg slice uncertainty blocking.
Specified ACK_UNKNOWN resolution through reconciliation by clientOrderId, exchange_order_id, and cumulative fills only, with no blind retry.
Specified cumulative executedQty fill reconciliation and delta_fill = max(0, exchange_cum_qty - ledger_cum_qty).
Documented recovery, safe mode, risk-reducing mode, and kill switch audit events.
Added ADR-0006 and linked INTERFACES.md to the detailed event contract.
```

Files changed:

```text
docs/event_contracts.md
project_control/INTERFACES.md
project_control/DECISIONS.md
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
```

Tests/checks run:

```text
rg -n "TRADE_INTENT_CREATED|ORDER_INTENT_CREATED|ORDER_SENT|ORDER_ACKED|ORDER_ACK_UNKNOWN|PARTIAL_FILL_RECONCILED|FILL_RECONCILED|HEDGE_REQUIRED|EXIT_LOCKDOWN|FLAT_RECONCILED" docs/event_contracts.md project_control/INTERFACES.md
rg -n "deterministic|clientOrderId|cumulative executedQty|ACK_UNKNOWN|no blind retry|blind retry|delta_fill|max\(0, exchange_cum_qty - ledger_cum_qty\)|same leg|same-leg|previous slice|ORDER_SENT.*pre-side-effect|ORDER_INTENT_CREATED" docs/event_contracts.md project_control/INTERFACES.md project_control/DECISIONS.md
rg -n "RECOVERY_BOOT_STARTED|RECONCILIATION_COMPLETED|SAFE_MODE_ENTERED|SAFE_MODE_EXITED|RISK_REDUCING_MODE_ENTERED|KILL_SWITCH_TRIGGERED|Recovery|safe mode|risk-reducing|kill switch" docs/event_contracts.md project_control/INTERFACES.md
```

Pending:

```text
Architect review.
Implementation remains out of scope for Sprint 1 TASK-003.
```

Next steps:

```text
Architect Agent reviews docs/event_contracts.md against docs/architecture.md and docs/state_machine.md.
Execution / Risk Agent should consume the event contract when TASK-004 defines risk limits.
Ledger/Recovery tasks should use ADR-0006 before any event store or recovery implementation.
```

## HANDOFF - TASK-004 Risk Limits Specification

### Status

Ready for QA / Chaos Testing review

### Agente

Execution / Risk Agent

### O que foi feito

- Created `docs/risk_limits.md` with MVP risk limits, forbidden configurations, required risk inputs, entry blockers, kill-switch triggers, fail-closed rules, risk-reducing mode, stress-risk proof obligation, escalation behavior, and review checklist.
- Made forbidden configurations explicit: Cross Margin, Kelly, 10x, live multi-exchange, and leverage before Sprint 26.
- Marked daily realized loss and drawdown thresholds as unresolved Sprint 1 gate items that fail closed for live entries until approved.
- Updated `project_control/RISKS.md` with risk-input, risk-reducing, forbidden-configuration, and unresolved-threshold risks.
- Updated `project_control/TEST_MATRIX.md` with Sprint 1 documentation review checks for risk limits.
- Moved TASK-004 to `IN_REVIEW` in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
docs/risk_limits.md
project_control/RISKS.md
project_control/HANDOFFS.md
project_control/TEST_MATRIX.md
project_control/TASK_BOARD.md
```

### Testes rodados

```text
rg keyword checks for forbidden configurations, entry blockers, kill-switch triggers, fail-closed behavior, and risk-reducing proof obligation.
```

### Pendencias

```text
QA / Chaos Testing Agent review.
Sprint 1 gate unresolved before live readiness: numeric daily realized loss threshold.
Sprint 1 gate unresolved before live readiness: numeric drawdown threshold.
No implementation, live engine, exchange connector, or tests/ changes were made.
```

### Riscos encontrados

```text
Daily loss and drawdown thresholds cannot be safely finalized from Sprint 1 context alone; they are documented as live-readiness blockers that fail closed.
```

### Proximo passo recomendado

QA / Chaos Testing Agent should review `docs/risk_limits.md` against stale input, ACK_UNKNOWN, kill-switch, and risk-reducing chaos scenarios.

### Proximo agente recomendado

QA / Chaos Testing Agent.

## HANDOFF - TASK-012 Ledger Idempotency Helpers

### Status

IN_REVIEW

### Agente

Ledger Agent

### O que foi feito

- Created `src/ledger/idempotency.py` with pure deterministic idempotency helpers.
- Added contract key builders for ORDER_INTENT_CREATED, ORDER_SENT, ORDER_ACKED, ORDER_ACK_UNKNOWN, PARTIAL_FILL_RECONCILED, and FILL_RECONCILED.
- Added generic `ledger_event_key()` with sorted field ordering for stable Ledger event idempotency keys.
- Added exchange reconciliation observation keys and cumulative observation classification: NEW_FILL, DUPLICATE, and REGRESSION.
- Exported the helpers from `src/ledger/__init__.py`.
- Created focused tests in `tests/test_idempotency.py`.
- Moved TASK-012 to `IN_REVIEW` at 80% in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
src/ledger/idempotency.py
src/ledger/__init__.py
tests/test_idempotency.py
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
```

### Testes rodados

```text
pytest tests/test_idempotency.py
Result: passed, 11 tests.
```

### Pendencias

```text
QA / Chaos Testing Agent review.
```

### Riscos encontrados

```text
No EventStore persistence changes were made; helpers return strings compatible with existing EventStore.append idempotency behavior.
REGRESSION classification deliberately returns zero delta fill and leaves routing/escalation to future reconciliation code.
```

### Proximo passo recomendado

QA / Chaos Testing Agent should review deterministic key construction, duplicate observation behavior, and invalid-field handling.

### Proximo agente recomendado

QA / Chaos Testing Agent.

## HANDOFF - TASK-005 Recovery Protocol Specification

### Status

Ready for QA / Chaos Testing review

### Agente

Ledger Agent

### O que foi feito

- Created `docs/recovery_protocol.md` covering recovery boot, safe mode, reconciliation order, `ACK_UNKNOWN` resolution, orphan order handling, residual exposure handling, REST/WebSocket failure behavior, and normal resume criteria.
- Specified that the system never boots into normal trading before reconciliation.
- Specified that safe mode permits only cancellation, reconciliation, and proven risk reduction.
- Required cumulative `executedQty` reconciliation and idempotent delta fill application.
- Required safe orphan cancel by exchange order id followed by order/fill/position requery.
- Required REST 5xx, timeout, missing pages, or WebSocket missing event to keep unresolved state in safe mode.
- Updated recovery risks and Sprint 1 documentation review checks.
- Moved TASK-005 to `IN_REVIEW` in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
docs/recovery_protocol.md
project_control/INTERFACES.md
project_control/RISKS.md
project_control/HANDOFFS.md
project_control/TEST_MATRIX.md
project_control/TASK_BOARD.md
```

### Testes rodados

```text
rg keyword checks for recovery boot, safe mode, ACK_UNKNOWN, orphan order, REST 5xx, WebSocket missing event, cumulative executedQty, and FLAT_RECONCILED.
```

### Pendencias

```text
QA / Chaos Testing Agent review.
No implementation, exchange connector, Ledger database, src/, tests/, notebooks/, or models/ changes were made.
```

### Riscos encontrados

```text
Orphan orders without a usable exchange order id require operator review because automated recovery cannot uniquely prove safe cancellation.
REST 5xx, timeout, missing REST pages, and WebSocket missing event remain fail-closed uncertainty sources until exchange evidence is complete.
```

### Proximo passo recomendado

QA / Chaos Testing Agent should review `docs/recovery_protocol.md` against crash-after-send, orphan order, cancel-timeout, REST 5xx, missing WebSocket event, partial fill, and residual exposure scenarios.

### Proximo agente recomendado

QA / Chaos Testing Agent.

## HANDOFF - TASK-006 Initial SQLite Schema

### Status

Ready for Architect review

### Agente

Ledger Agent

### O que foi feito

- Created `migrations/001_initial_schema.sql` with the required Ledger tables: `events`, `orders`, `fills`, `positions`, `trades`, `reconciliation_runs`, and `outbox`.
- Added append-only protections for `events` through no-update and no-delete triggers.
- Added uniqueness for `events.event_id`, `events.idempotency_key`, and per-aggregate sequence via `(aggregate_type, aggregate_id, sequence)`.
- Added projection tables and indexes for open orders, uncertain orders, open positions, trades, fills by cumulative reconciliation state, reconciliation runs, and transactional outbox dispatch.
- Included cumulative fill reconciliation fields: `exchange_cum_qty`, `ledger_cum_qty`, and `delta_fill`.
- Moved TASK-006 to `IN_REVIEW` in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
migrations/001_initial_schema.sql
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
```

### Testes rodados

```text
sqlite3 :memory: ".read migrations/001_initial_schema.sql" ".tables"
Result: passed. SQLite parsed and applied the migration, then listed all required tables.
```

### Pendencias

```text
Architect Agent review.
TASK-007 should wire SQLite WAL bootstrap and connection-level pragmas.
Future EventStore work must keep projection writes and outbox inserts in the same transaction as event append.
```

### Riscos encontrados

```text
SQLite cannot make every projection table append-only because those tables are intentionally mutable read models; immutable truth is enforced on the events table.
Fill delta arithmetic is enforced in the fills table with a CASE-based CHECK matching max(0, exchange_cum_qty - ledger_cum_qty).
```

### Proximo passo recomendado

Architect Agent should review the migration against the Sprint 1 event contracts, then Ledger Agent can proceed to TASK-007.

### Proximo agente recomendado

Architect Agent.

## HANDOFF - TASK-009 EventStore Append and Reads

### Status

IN_REVIEW

### Agente

PM Agent acting as Ledger Agent after subagent quota failure

### O que foi feito

- Created `src/ledger/event_store.py`.
- Implemented transactional `EventStore.append()` for `LedgerEvent`.
- Implemented deterministic idempotency behavior: duplicate `idempotency_key` reloads the existing event and does not insert a second row.
- Implemented `load_trade_events(trade_id)` using persisted SQLite events.
- Implemented `load_open_positions()` using open rows from the `positions` projection table.
- Exported `EventStore` from `src/ledger/__init__.py`.
- Moved TASK-009 to `IN_REVIEW` in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
src/ledger/event_store.py
src/ledger/__init__.py
tasks/sprint_02/TASK-009-event-store-append-read.md
project_control/TASK_BOARD.md
project_control/CURRENT_SPRINT.md
project_control/PROJECT_STATE.md
project_control/HANDOFFS.md
```

### Testes rodados

```text
Focused Python check with temporary file-backed SQLite database bootstrapped through src.ledger.db.bootstrap.
Result: passed.

Checked append of one event.
Result: passed.

Checked duplicate idempotency key does not create a second event and returns the persisted event.
Result: passed.

Checked load_trade_events('trade-1') returns persisted trade event.
Result: passed.

Checked load_open_positions() returns only open position projection rows.
Result: passed.

python -m py_compile src/ledger/event_store.py src/ledger/__init__.py
Result: passed.
```

### Pendencias

```text
Architect Agent review.
QA / Chaos Testing Agent review.
TASK-010 remains blocked until TASK-009 review passes.
```

### Riscos encontrados

```text
Projection writes and outbox insertion are not implemented in TASK-009 and must be handled carefully in later EventStore expansion.
load_trade_events uses SQLite JSON extraction when available and falls back to Python payload filtering if unavailable.
```

### Proximo passo recomendado

Architect Agent and QA / Chaos Testing Agent should review `src/ledger/event_store.py` for transaction, idempotency, persisted reads, and scope boundaries.

### Proximo agente recomendado

Architect Agent + QA / Chaos Testing Agent.

## HANDOFF - TASK-009 QA Corrections

### Status

IN_REVIEW

### Agente

PM Agent acting as Ledger Agent

### O que foi feito

- Addressed QA / Chaos Testing Agent P1 finding for aggregate sequence gaps.
- Added contiguous per-aggregate sequence validation inside the `EventStore.append()` transaction.
- `EventStore.append()` now rejects `sequence=3` after latest persisted sequence `1`; expected sequence is `2`.
- Confirmed failed sequence-gap append rolls back and does not leave a partial event.
- Moved TASK-009 back to `IN_REVIEW` in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
src/ledger/event_store.py
project_control/TASK_BOARD.md
project_control/CURRENT_SPRINT.md
project_control/PROJECT_STATE.md
project_control/HANDOFFS.md
```

### Testes rodados

```text
Focused Python check with temporary file-backed SQLite database bootstrapped through src.ledger.db.bootstrap.
Result: passed.

Checked append of sequence 1.
Result: passed.

Checked duplicate idempotency key does not create a second event.
Result: passed.

Checked sequence gap: sequence 3 after sequence 1.
Result: failed as expected with ValueError and event count remained unchanged.

Checked append of sequence 2 after sequence 1.
Result: passed.

Checked load_trade_events and load_open_positions.
Result: passed.

python -m py_compile src/ledger/event_store.py src/ledger/__init__.py
Result: passed.
```

### Pendencias

```text
QA / Chaos Testing Agent re-review.
Formal pytest file remains planned for TASK-010.
```

### Riscos encontrados

```text
No new EventStore risk found in the correction scope.
```

### Proximo passo recomendado

QA / Chaos Testing Agent should re-review TASK-009 sequence-gap handling.

### Proximo agente recomendado

QA / Chaos Testing Agent.

## HANDOFF - TASK-007 SQLite WAL Bootstrap

### Status

Ready for QA / Chaos Testing review

### Agente

Ledger Agent

### O que foi feito

- Created `src/ledger/db.py` with deterministic SQLite connection bootstrap helpers.
- Enabled and verified `PRAGMA journal_mode = WAL` for file-backed databases.
- Enabled and verified `PRAGMA foreign_keys = ON`.
- Added `PRAGMA synchronous = NORMAL` and `busy_timeout` for basic durability/concurrency behavior.
- Added a transaction-wrapped migration helper for `migrations/001_initial_schema.sql`.
- Added package exports in `src/ledger/__init__.py`.
- Moved TASK-007 to `IN_REVIEW` in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
src/ledger/db.py
src/ledger/__init__.py
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
```

### Testes rodados

```text
Python focused bootstrap check with a temporary file-backed SQLite database:
- bootstrap() applied migrations/001_initial_schema.sql.
- PRAGMA journal_mode returned wal.
- PRAGMA foreign_keys returned 1.
- Required tables existed: events, orders, fills, positions, trades, reconciliation_runs, outbox.
- PRAGMA quick_check returned ok.

python -m py_compile src/ledger/db.py src/ledger/__init__.py
Result: passed.
```

### Pendencias

```text
QA / Chaos Testing Agent review.
No EventStore business logic was implemented.
```

### Riscos encontrados

```text
WAL is intentionally skipped only for SQLite in-memory databases because SQLite cannot use WAL for :memory: connections.
Future EventStore work should keep using explicit transactions for append/projection/outbox writes.
```

### Proximo passo recomendado

QA / Chaos Testing Agent should run failure-case checks around migration errors and verify WAL/foreign_keys on reopened connections.

### Proximo agente recomendado

QA / Chaos Testing Agent.

## HANDOFF - TASK-006 Architect Review Corrections

### Status

Ready for Architect re-review

### Agente

Ledger Agent

### O que foi feito

- Addressed Architect Agent CHANGES_REQUESTED for TASK-006.
- Updated `fills.exchange_order_id` to `TEXT NOT NULL`.
- Added a CASE-based CHECK in `fills` enforcing `delta_fill = max(0, exchange_cum_qty - ledger_cum_qty)`.
- Revalidated append-only triggers on `events`.
- Moved TASK-006 back to `IN_REVIEW` in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
migrations/001_initial_schema.sql
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
```

### Testes rodados

```text
sqlite3 :memory: ".read migrations/001_initial_schema.sql" "PRAGMA quick_check;" ...
Result: passed with quick_check = ok and all required tables listed.

Valid fills insert with exchange_cum_qty=7, ledger_cum_qty=4, delta_fill=3.
Result: passed; SELECT COUNT(*) FROM fills returned 1.

Invalid fills insert with exchange_cum_qty=7, ledger_cum_qty=4, delta_fill=2.
Result: failed as expected on the delta_fill CASE CHECK.

Invalid fills insert with exchange_order_id NULL.
Result: failed as expected on fills.exchange_order_id NOT NULL.

UPDATE on events after insert.
Result: blocked as expected by events append-only trigger.

DELETE on events after insert.
Result: blocked as expected by events append-only trigger.
```

### Pendencias

```text
Architect Agent re-review.
No src/, tests/, docs/, CURRENT_SPRINT.md, PROJECT_STATE.md, INTERFACES.md, DECISIONS.md, or tasks/ files were changed.
```

### Riscos encontrados

```text
No new schema risk found in the requested correction scope.
SQLite NUMERIC equality is exact for the CASE check; future EventStore tests should use the project's final quantity representation consistently.
```

### Proximo passo recomendado

PM Agent should request Architect Agent re-review for TASK-006.

### Proximo agente recomendado

Architect Agent.

## HANDOFF - TASK-008 Ledger Models

### Status

Ready for Architect review

### Agente

Ledger Agent

### O que foi feito

- Created `src/ledger/models.py` with typed dataclass models for Ledger events, trades, orders, fills, positions, reconciliation runs, and outbox messages.
- Matched the Sprint 1 event envelope with `event_id`, `event_type`, `aggregate_type`, `aggregate_id`, `sequence`, `schema_version`, `occurred_at`, `payload`, `idempotency_key`, `correlation_id`, `causation_id`, `producer`, `consumer`, and `raw_payload_ref`.
- Matched Sprint 2 SQLite projection tables from `migrations/001_initial_schema.sql`.
- Preserved cumulative fill reconciliation field names: `exchange_cum_qty`, `ledger_cum_qty`, and `delta_fill`.
- Exported the model classes from `src/ledger/__init__.py`.
- Moved TASK-008 to `IN_REVIEW` in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
src/ledger/models.py
src/ledger/__init__.py
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
```

### Testes rodados

```text
python -c "<import and construct LedgerEvent, TradeRecord, OrderRecord, FillRecord, PositionRecord, ReconciliationRunRecord, and OutboxMessage>"
Result: passed with "model construction ok".

python -m py_compile src/ledger/models.py src/ledger/__init__.py
Result: passed.
```

### Pendencias

```text
Architect Agent review.
No persistence, EventStore append/read behavior, exchange adapter, execution, live, recovery, docs, migrations, or tests/ changes were made.
```

### Riscos encontrados

```text
No new model-scope risk found.
Future EventStore code must serialize/deserialize payloads and NUMERIC fields consistently when mapping these typed models to SQLite rows.
```

### Proximo passo recomendado

Architect Agent should review `src/ledger/models.py` against `docs/event_contracts.md` and `migrations/001_initial_schema.sql`.

### Proximo agente recomendado

Architect Agent.

## HANDOFF - TASK-010 EventStore Tests and Rebuild Checks

### Status

IN_REVIEW

### Agente

QA / Chaos Testing Agent

### O que foi feito

- Created `tests/test_event_store.py` with file-backed SQLite fixtures bootstrapped through `src.ledger.db.bootstrap`.
- Covered migration/bootstrap, WAL, `foreign_keys`, required tables, and `quick_check`.
- Covered EventStore append persistence and append-only event triggers for update/delete attempts.
- Covered duplicate idempotency handling: same idempotency key returns the existing event and does not duplicate state.
- Covered sequence gap rejection and verified no partial insert remains after failure.
- Covered failed append rollback on SQLite constraint failure and verified the next valid contiguous sequence can append.
- Covered `load_trade_events(trade_id)` returning lifecycle events in persisted order.
- Covered `load_open_positions()` returning only open projection rows with typed decimal/bool mapping.
- Updated `project_control/TEST_MATRIX.md`.
- Moved TASK-010 to `IN_REVIEW` in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
tests/test_event_store.py
project_control/TEST_MATRIX.md
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
```

### Testes rodados

```text
pytest tests/test_event_store.py
Result: passed, 7 tests.
```

### Pendencias

```text
Ledger Agent review.
No src/, docs/, migrations/, tasks/, PROJECT_STATE.md, CURRENT_SPRINT.md, INTERFACES.md, or DECISIONS.md changes were made.
```

### Riscos encontrados

```text
No new EventStore test-scope risk found.
Projection writes remain future EventStore expansion work; TASK-010 validates current load behavior against existing projection rows.
```

### Proximo passo recomendado

Ledger Agent should review TASK-010 tests against Sprint 2 Ledger base gate.

### Proximo agente recomendado

Ledger Agent.

## HANDOFF - TASK-015 PM Correction

### Status

IN_REVIEW

### Agente

PM Agent

### O que foi corrigido

- PM review found a real idempotency bug: `ORDER_INTENT_CREATED` keys did not label attempt versus slice domains.
- Updated `src/ledger/idempotency.py` so the final key component is `attempt-*` or `slice-*`.
- Added regression coverage proving `attempt="slice-1"` and `slice_id="slice-1"` do not collide.
- Updated Sprint 3 integration expectations and TEST_MATRIX counts.

### Arquivos alterados

```text
src/ledger/idempotency.py
tests/test_idempotency.py
tests/test_cumulative_reconciliation.py
tests/test_ack_guard.py
project_control/TEST_MATRIX.md
project_control/HANDOFFS.md
project_control/DAILY_LOG.md
```

### Testes rodados

```text
pytest tests/test_idempotency.py
Result: passed, 12 tests.

pytest tests/test_client_order_id.py tests/test_idempotency.py tests/test_cumulative_reconciliation.py tests/test_ack_guard.py
Result: passed, 57 tests.

pytest tests
Result: passed, 64 tests.
```

### Proximo passo recomendado

Ledger Agent should include the attempt/slice idempotency domain correction in TASK-015 review.

## HANDOFF - TASK-016 Detect Unresolved ORDER_SENT After Restart

### Status

IN_REVIEW

### Agente

PM Agent fallback for Ledger Agent

### O que foi feito

- Created `src/recovery/order_state.py` with pure recovery classification for durable `ORDER_SENT` uncertainty.
- Created `src/recovery/__init__.py`.
- Created `tests/test_recovery_order_state.py`.
- Classified `ORDER_SENT` without later resolving evidence as `UNRESOLVED_AFTER_SEND`.
- Treated matching `ORDER_ACKED`, `PARTIAL_FILL_RECONCILED`, `FILL_RECONCILED`, cancel reconciliation, ACK_UNKNOWN resolution, and valid `FLAT_RECONCILED` evidence as resolution.
- Ensured wrong order or wrong lifecycle scope does not clear an unresolved send.
- Covered multiple orders independently.

### Arquivos alterados

```text
src/recovery/order_state.py
src/recovery/__init__.py
tests/test_recovery_order_state.py
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
project_control/CURRENT_SPRINT.md
project_control/PROJECT_STATE.md
project_control/DAILY_LOG.md
tasks/sprint_04/TASK-016-unresolved-order-sent.md
tasks/sprint_04/TASK-017-recovery-boot-gate.md
```

### Testes rodados

```text
pytest tests/test_recovery_order_state.py --basetemp=pytest_temp_run_recovery -o cache_dir=pytest_temp_run_recovery/.pytest_cache
Result: passed, 9 tests.

pytest tests --basetemp=pytest_temp_run -o cache_dir=pytest_temp_run/.pytest_cache
Result: passed, 73 tests.
```

### Pendencias

```text
Execution / Risk Agent + QA / Chaos Testing Agent review.
```

### Riscos encontrados

```text
The helper is pure and depends on future recovery code passing complete Ledger-derived event history.
FLAT_RECONCILED clears only matching lifecycle scope and only when open_orders_count/unresolved_orders_count are zero or omitted.
```

### Proximo passo recomendado

Review TASK-016 while PM continues TASK-017 recovery boot gate helper.

## HANDOFF - TASK-017 Recovery Boot Gate and Resume Classifier

### Status

IN_REVIEW

### Agente

PM Agent fallback for Ledger Agent

### O que foi feito

- Created `src/recovery/recovery_boot.py` with pure recovery boot classification.
- Exported recovery boot helpers from `src/recovery/__init__.py`.
- Created `tests/test_recovery_boot.py`.
- Recovery boot blocks entries before boot start, while unresolved orders exist, while unresolved positions exist, when exchange evidence is incomplete, and until reconciliation is completed.
- Normal resume is allowed only with explicit flat/reconciled truth or explicit intentional reconciled open position.

### Arquivos alterados

```text
src/recovery/recovery_boot.py
src/recovery/__init__.py
tests/test_recovery_boot.py
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
project_control/CURRENT_SPRINT.md
project_control/PROJECT_STATE.md
project_control/DAILY_LOG.md
tasks/sprint_04/TASK-017-recovery-boot-gate.md
tasks/sprint_04/TASK-018-partial-fill-route.md
```

### Testes rodados

```text
pytest tests/test_recovery_boot.py --basetemp=pytest_temp_run_boot -o cache_dir=pytest_temp_run_boot/.pytest_cache
Result: passed, 8 tests.

pytest tests/test_recovery_order_state.py tests/test_recovery_boot.py --basetemp=pytest_temp_run_s4a -o cache_dir=pytest_temp_run_s4a/.pytest_cache
Result: passed, 17 tests.

pytest tests --basetemp=pytest_temp_run_all2 -o cache_dir=pytest_temp_run_all2/.pytest_cache
Result: passed, 81 tests.
```

### Pendencias

```text
QA / Chaos Testing Agent review.
```

### Proximo passo recomendado

Review TASK-017 while PM continues TASK-018 partial-fill route helper.

## HANDOFF - TASK-018 Partial-Fill Route Decision Helper

### Status

IN_REVIEW

### Agente

PM Agent fallback for Execution / Risk Agent

### O que foi feito

- Created `src/recovery/partial_fill_route.py` with deterministic partial-fill route decisions.
- Exported partial-fill route helpers from `src/recovery/__init__.py`.
- Created `tests/test_partial_fill_route.py`.
- Routed unpaired partial-fill exposure with explicit risk-reducing proof to `HEDGING_REQUIRED`.
- Routed residual order uncertainty, missing proof, non-risk-reducing hedge, or absent unpaired exposure proof to `EXIT_LOCKDOWN`.
- Preserved the invariant that normal entry continuation is never allowed by the partial-fill helper.

### Arquivos alterados

```text
src/recovery/partial_fill_route.py
src/recovery/__init__.py
tests/test_partial_fill_route.py
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
project_control/CURRENT_SPRINT.md
project_control/PROJECT_STATE.md
project_control/DAILY_LOG.md
tasks/sprint_04/TASK-018-partial-fill-route.md
tasks/sprint_04/TASK-019-sprint-04-tests.md
```

### Testes rodados

```text
pytest tests/test_partial_fill_route.py --basetemp=pytest_temp_run_partial -o cache_dir=pytest_temp_run_partial/.pytest_cache
Result: passed, 9 tests.

pytest tests/test_recovery_order_state.py tests/test_recovery_boot.py tests/test_partial_fill_route.py --basetemp=pytest_temp_run_s4b -o cache_dir=pytest_temp_run_s4b/.pytest_cache
Result: passed, 26 tests.

pytest tests --basetemp=pytest_temp_run_all3 -o cache_dir=pytest_temp_run_all3/.pytest_cache
Result: passed, 90 tests.
```

### Pendencias

```text
Ledger Agent + QA / Chaos Testing Agent review.
```

### Proximo passo recomendado

Review TASK-018 while PM continues TASK-019 Sprint 4 chaos/integration tests.

## HANDOFF - TASK-019 Sprint 4 Chaos and Integration Tests

### Status

IN_REVIEW

### Agente

PM Agent fallback for QA / Chaos Testing Agent

### O que foi feito

- Added Sprint 4 integration coverage to `tests/test_recovery_boot.py`.
- Added Sprint 4 partial-fill route integration coverage to `tests/test_partial_fill_route.py`.
- Updated `project_control/TEST_MATRIX.md` Sprint 4 rows to passed.
- Confirmed crash after durable `ORDER_SENT` blocks recovery resume.
- Confirmed resolved `ORDER_SENT` plus flat truth allows recovery resume.
- Confirmed reconciled partial fill delta routes to `HEDGING_REQUIRED` only with risk-reducing proof and `EXIT_LOCKDOWN` otherwise.

### Arquivos alterados

```text
tests/test_recovery_boot.py
tests/test_partial_fill_route.py
project_control/TEST_MATRIX.md
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
project_control/CURRENT_SPRINT.md
project_control/PROJECT_STATE.md
project_control/DAILY_LOG.md
tasks/sprint_04/TASK-019-sprint-04-tests.md
```

### Testes rodados

```text
pytest tests/test_recovery_order_state.py tests/test_recovery_boot.py tests/test_partial_fill_route.py --basetemp=pytest_temp_run_s4d -o cache_dir=pytest_temp_run_s4d/.pytest_cache
Result: passed, 29 tests.

pytest tests --basetemp=pytest_temp_run_all5 -o cache_dir=pytest_temp_run_all5/.pytest_cache
Result: passed, 93 tests.

$env:UV_CACHE_DIR='.uv_cache'; uv run ruff check .
Result: passed.
```

### Verificacao nao concluida

```text
uv run pyright --project .
Result: environment permission failure, Node EPERM on lstat C:\Users\arthu before type checking.
```

### Pendencias

```text
PM fallback gate review due subagent usage limit.
```

## HANDOFF - TASK-011 Deterministic clientOrderId

### Status

IN_REVIEW

### Agente

Execution / Risk Agent

### O que foi feito

- Created `src/execution/client_order_id.py` with deterministic `coid.v1` canonical ID generation from venue, account, strategy, trade, leg, phase, symbol, and exactly one attempt or slice id.
- Added versioned deterministic shortening as `coid.v1h:<sha256-base32-prefix>` when a venue length limit is supplied and the canonical ID is too long.
- Returned both exchange-facing ID and full canonical ID so callers can persist shortened venue IDs alongside reconstructable canonical inputs.
- Exported the helper API from `src/execution/__init__.py`.
- Added focused tests for determinism, restart-stability, uniqueness dimensions, attempt/slice separation, no timestamp/randomness calls, and shortening stability.
- Moved TASK-011 to `IN_REVIEW` in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
src/execution/client_order_id.py
src/execution/__init__.py
tests/test_client_order_id.py
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
```

### Testes rodados

```text
pytest tests/test_client_order_id.py
Result: passed, 18 tests.
```

### Pendencias

```text
Architect Agent review.
No exchange connector, order router, ACK_UNKNOWN guard, Ledger, reconciliation, docs, migrations, tasks, PROJECT_STATE.md, CURRENT_SPRINT.md, INTERFACES.md, or DECISIONS.md changes were made.
```

### Riscos encontrados

```text
Shortened IDs require callers to persist `canonical_id` together with the venue-facing `client_order_id`.
The implementation intentionally rejects non-ASCII or delimiter-unsafe components before ID generation.
```

### Proximo passo recomendado

Architect Agent should review the `coid.v1`/`coid.v1h` format and canonical persistence expectation before downstream TASK-014 integration.

### Proximo agente recomendado

Architect Agent.

## HANDOFF - TASK-013 Cumulative Fill Reconciliation

### Status

IN_REVIEW

### Agente

Ledger Agent

### O que foi feito

- Created `src/reconciliation/cumulative_fill.py` with Decimal-safe cumulative fill reconciliation.
- Implemented `delta_fill = max(0, exchange_cum_qty - ledger_cum_qty)`.
- Classified new fills, duplicate observations, exact zero observations, and lower/out-of-order observations.
- Ensured duplicate, exact zero, and lower observations return zero delta and cannot increase Ledger position.
- Rejected float inputs to avoid binary floating-point drift in Ledger quantity math.
- Exported reconciliation helpers from `src/reconciliation/__init__.py`.
- Created focused tests for partial fills, duplicates, lower observations, exact zero behavior, Decimal precision, float rejection, and negative quantity validation.
- Moved TASK-013 to `IN_REVIEW` in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
src/reconciliation/cumulative_fill.py
src/reconciliation/__init__.py
tests/test_cumulative_reconciliation.py
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
```

### Testes rodados

```text
pytest tests/test_cumulative_reconciliation.py
Result: passed, 7 tests.
```

### Pendencias

```text
QA / Chaos Testing Agent review.
Future integration should wire CumulativeFillResult into EventStore/projection writes without bypassing delta_fill.
```

### Riscos encontrados

```text
Lower exchange cumulative quantity is flagged as an inconsistent regression and returns zero delta; routing to RECONCILING or ERROR_SAFE_MODE remains future recovery integration work.
```

### Proximo passo recomendado

QA / Chaos Testing Agent should review duplicate/lower cumulative observation behavior and Decimal boundary handling.

### Proximo agente recomendado

QA / Chaos Testing Agent.

## HANDOFF - TASK-014 ACK_UNKNOWN Retry Guard

### Status

IN_REVIEW

### Agente

Execution / Risk Agent

### O que foi feito

- Created `src/execution/ack_guard.py` with pure dataclass/enum guard semantics.
- Added deterministic blocking for blind retry while `ACK_UNKNOWN` or pre-ACK send state is unresolved.
- Added same-leg slice blocking for unresolved prior slices in the same venue/account/trade/leg scope.
- Allowed retry only from explicit clear states proving no live order/no fill, while allowing same-leg slice checks to clear once prior slice uncertainty is reconciled.
- Exported the guard API from `src/execution/__init__.py`.
- Added focused tests in `tests/test_ack_guard.py`.
- Moved TASK-014 to `IN_REVIEW` at 80% in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
src/execution/ack_guard.py
src/execution/__init__.py
tests/test_ack_guard.py
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
```

### Testes rodados

```text
pytest tests/test_ack_guard.py
Result: passed, 16 tests.
```

### Pendencias

```text
Ledger Agent + QA / Chaos Testing Agent review.
```

### Riscos encontrados

```text
This guard is intentionally pure and does not query Ledger or exchanges; callers must provide complete current order state from durable/reconciled truth.
ACKED, PARTIAL_FILL_RECONCILED, and FILL_RECONCILED clear ACK uncertainty for slice scanning but deliberately do not permit retry of the same order.
Router, persistence writes, recovery boot, and exchange calls remain out of scope.
```

### Proximo passo recomendado

Ledger Agent and QA / Chaos Testing Agent should review retry blocking, same-leg slice scope, resolved-state allow-listing, and invalid input behavior.

### Proximo agente recomendado

Ledger Agent + QA / Chaos Testing Agent.

## HANDOFF - TASK-015 Sprint 3 Integration Tests

### Status

IN_REVIEW

### Agente

QA / Chaos Testing Agent

### O que foi feito

- Added Sprint 3 integration-style tests tying deterministic clientOrderId generation to Ledger idempotency keys, cumulative fill reconciliation, and ACK_UNKNOWN guard behavior.
- Covered duplicate cumulative fill observations so repeated partial or terminal exchange executedQty does not duplicate position delta.
- Covered unresolved ORDER_SENT and ACK_UNKNOWN as fail-closed states that block blind retry and same-leg slice creation.
- Covered resolved no-order/no-fill retry only when an explicit same-scope state is supplied.
- Updated `project_control/TEST_MATRIX.md` Sprint 3 rows to passed and recorded the focused and current-suite pytest runs.
- Moved TASK-015 to `IN_REVIEW` at 80% in `project_control/TASK_BOARD.md`.

### Arquivos alterados

```text
tests/test_cumulative_reconciliation.py
tests/test_ack_guard.py
project_control/TEST_MATRIX.md
project_control/HANDOFFS.md
project_control/TASK_BOARD.md
```

### Testes rodados

```text
pytest tests/test_client_order_id.py tests/test_idempotency.py tests/test_cumulative_reconciliation.py tests/test_ack_guard.py
Result: passed, 57 tests.

pytest tests
Result: passed, 64 tests.
```

### Pendencias

```text
Ledger Agent review.
```

### Riscos cobertos

```text
Duplicate fill observations do not duplicate Ledger position/delta.
ACK_UNKNOWN and unresolved sends cannot become blind retries.
Same-leg slice creation remains blocked while the previous slice is uncertain.
Retry after no-order/no-fill reconciliation requires explicit same-scope durable state.
ORDER_INTENT_CREATED idempotency keys separate attempt-* and slice-* domains to avoid attempt/slice collisions.
```

### Proximo passo recomendado

Ledger Agent should review TASK-015 test coverage against Sprint 3 gate criteria.

### Proximo agente recomendado

Ledger Agent.
