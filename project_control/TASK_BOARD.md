# TASK_BOARD

Last updated: 2026-07-02

## Status permitidos

```text
BACKLOG
READY
IN_PROGRESS
BLOCKED
IN_REVIEW
CHANGES_REQUESTED
DONE
ARCHIVED
```

## Regras

- Agent can start only tasks in READY.
- Task cannot be READY without definition of done.
- Task cannot be READY without allowed files.
- Critical-area tasks require a mandatory reviewer.
- Blocked tasks must include a clear blocker.
- No task can be DONE without review and handoff.

## Quadro

| ID | Sprint | Tarefa | Dono | Status | Branch | Revisor | Bloqueio |
|---|---:|---|---|---|---|---|---|
| TASK-001 | 1 | Criar architecture.md | Architect Agent | DONE | - | PM Agent | nenhum |
| TASK-002 | 1 | Definir state machine | Execution / Risk Agent | DONE | - | Architect Agent | nenhum |
| TASK-003 | 1 | Definir event contracts | Ledger Agent | DONE | - | Architect Agent | nenhum |
| TASK-004 | 1 | Definir risk limits | Execution / Risk Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-005 | 1 | Definir recovery protocol | Ledger Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-006 | 2 | Criar schema SQLite inicial | Ledger Agent | DONE | - | Architect Agent | nenhum |
| TASK-007 | 2 | Implementar bootstrap SQLite WAL | Ledger Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-008 | 2 | Definir modelos do Ledger | Ledger Agent | DONE | - | Architect Agent | nenhum |
| TASK-009 | 2 | Implementar EventStore append/read | Ledger Agent | DONE | - | Architect Agent + QA / Chaos Testing Agent | nenhum |
| TASK-010 | 2 | Testar EventStore e rebuild basico | QA / Chaos Testing Agent | DONE | - | Ledger Agent | nenhum |
| TASK-011 | 3 | Implementar clientOrderId deterministico | Execution / Risk Agent | DONE | - | Architect Agent | nenhum |
| TASK-012 | 3 | Implementar helpers de idempotencia | Ledger Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-013 | 3 | Implementar reconciliacao cumulativa | Ledger Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-014 | 3 | Implementar guard de ACK_UNKNOWN | Execution / Risk Agent | DONE | - | Ledger Agent + QA / Chaos Testing Agent | nenhum |
| TASK-015 | 3 | Testes integrados Sprint 3 | QA / Chaos Testing Agent | DONE | - | Ledger Agent | nenhum |
| TASK-016 | 4 | Detectar ORDER_SENT nao resolvido apos restart | Ledger Agent | DONE | - | Execution / Risk Agent + QA / Chaos Testing Agent | fallback PM review |
| TASK-017 | 4 | Classificar recovery boot e resume gate | Ledger Agent | DONE | - | QA / Chaos Testing Agent | fallback PM review |
| TASK-018 | 4 | Decidir rota de partial fill | Execution / Risk Agent | DONE | - | Ledger Agent + QA / Chaos Testing Agent | fallback PM review |
| TASK-019 | 4 | Testes chaos/integracao Sprint 4 | QA / Chaos Testing Agent | DONE | - | Ledger Agent | fallback PM review |
| TASK-020 | 4 | Gate review Sprint 4 | PM Agent | DONE | - | Ledger Agent + QA / Chaos Testing Agent | fallback PM review |
| TASK-021 | 5 | Definir book health e sequenciamento L2 | Market Data Agent | DONE | - | Execution / Risk Agent | nenhum |
| TASK-022 | 5 | Invalidar book em gap/stale | Market Data Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-023 | 5 | Decidir snapshot resync | Market Data Agent | DONE | - | Execution / Risk Agent + QA / Chaos Testing Agent | nenhum |
| TASK-024 | 5 | Testes Sprint 5 book health | QA / Chaos Testing Agent | DONE | - | Market Data Agent | nenhum |
| TASK-025 | 5 | Gate review Sprint 5 | PM Agent | DONE | - | Market Data Agent + QA / Chaos Testing Agent | nenhum |
| TASK-026 | 6 | Criar BookExecutionFeatures | Market Data Agent | DONE | - | Execution / Risk Agent | nenhum |
| TASK-027 | 6 | Implementar spread/depth/imbalance/volatilidade | Market Data Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-028 | 6 | Implementar SlippageEstimator | Execution / Risk Agent | DONE | - | Market Data Agent + QA / Chaos Testing Agent | nenhum |
| TASK-029 | 6 | Implementar FeatureCache | Market Data Agent | DONE | - | Execution / Risk Agent | nenhum |
| TASK-030 | 6 | Testes e gate review Sprint 6 | QA / Chaos Testing Agent + PM Agent | DONE | - | Market Data Agent + Execution / Risk Agent | nenhum |
| TASK-031 | 5 | Corrigir gate: LocalOrderBook snapshot/diff | Market Data Agent | DONE | - | QA / Chaos Testing Agent + PM Agent | nenhum |
| TASK-032 | 6 | Corrigir gate: BookFeatures book_age_ms/in_sync | Execution / Risk Agent | DONE | - | Market Data Agent + QA / Chaos Testing Agent | nenhum |
| TASK-033 | 6 | Revalidar gate Sprint 5/6 antes do Sprint 7 | QA / Chaos Testing Agent + PM Agent | DONE | - | Market Data Agent + Execution / Risk Agent | nenhum |
| TASK-007-01 | 7 | Definir dataset historico minimo | Quant Research Agent | DONE | - | Market Data Agent | nenhum |
| TASK-007-02 | 7 | Implementar pair_selection.py | Quant Research Agent | DONE | - | Backtest Agent | nenhum |
| TASK-007-03 | 7 | Implementar stationarity.py | Quant Research Agent | DONE | - | QA Agent | nenhum |
| TASK-007-04 | 7 | Implementar Kalman Filter | Quant Research Agent | DONE | - | Backtest Agent + QA Agent | nenhum |
| TASK-007-05 | 7 | Implementar OU estimator | Quant Research Agent | DONE | - | Backtest Agent + QA Agent | nenhum |
| TASK-007-06 | 7 | Criar notebooks exploratorios | Quant Research Agent | DONE | - | Documentation Agent | nenhum |
| TASK-007-07 | 7 | Criar testes de research base | QA Agent | DONE | - | Quant Research Agent | nenhum |
| TASK-007-08 | 7 | Gerar relatorio research_sprint_07.md | Documentation Agent | DONE | - | PM Agent | nenhum |
| TASK-007-09 | 7 | Implementar loader/normalizer historico Binance | PM Agent | DONE | - | Market Data Agent + QA Agent | nenhum |
| TASK-007-10 | 7 | Produzir evidencia historica de custo de execucao | Market Data Agent | DONE | - | QA Agent + PM Agent | nenhum (ver BLOCKER-2026-06-30-S7-REAL-DATASET-GATE para o bloqueio de abertura do Sprint 8) |
| TASK-008-01 | 8 | Congelar universo e contrato de evidencia | PM Agent | DONE | - | Backtest Agent + Market Data Agent | nenhum |
| TASK-008-02 | 8 | Implementar walk-forward split causal | Backtest Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-008-03 | 8 | Gerar SignalIntent offline | Quant Research Agent | DONE | - | Backtest Agent + Architect Agent | nenhum |
| TASK-008-04 | 8 | Implementar backtest cost-aware | Backtest Agent | DONE | - | Quant Research Agent + QA / Chaos Testing Agent | nenhum |
| TASK-008-05 | 8 | Calcular metricas e ranking de sobrevivencia | Backtest Agent | DONE | - | PM Agent + Quant Research Agent | nenhum |
| TASK-008-06 | 8 | Criar testes de Sprint 8 | QA / Chaos Testing Agent | DONE | - | Backtest Agent + PM Agent | nenhum |
| TASK-008-07 | 8 | Gerar relatorio e gate Sprint 8 | Documentation Agent | DONE | - | PM Agent + Backtest Agent | nenhum |
| TASK-008-08 | 8 | Preparar limpeza segura dos arquivos raw de evidencia | Market Data Agent | BLOCKED | - | PM Agent + QA / Chaos Testing Agent | aguardando aceite explicito do usuario antes de apagar 17GB de raw |
| TASK-009-01 | 9 | Implementar fill_model.py | Backtest Agent | DONE | - | QA / Chaos Testing Agent + Execution / Risk Agent | nenhum |
| TASK-009-02 | 9 | Implementar execution_simulator.py | Backtest Agent | DONE | - | Quant Research Agent + QA / Chaos Testing Agent | nenhum |
| TASK-009-03 | 9 | Implementar replay_engine.py | Backtest Agent | DONE | - | QA / Chaos Testing Agent + Market Data Agent | nenhum |
| TASK-009-04 | 9 | Testes de Sprint 9 (chaos, causalidade) | QA / Chaos Testing Agent | DONE | - | Backtest Agent + PM Agent | nenhum |
| TASK-009-05 | 9 | Rodar replay real nos 13 pares aprovados | Backtest Agent | DONE | - | PM Agent + Quant Research Agent | nenhum |
| TASK-009-06 | 9 | Relatorio e gate Sprint 9 | Documentation Agent | DONE | - | PM Agent + Backtest Agent | nenhum |

## Progresso

| ID | Progresso | Notas |
|---|---:|---|
| TASK-001 | 100% | PM final review passed; architecture specification is documented and integrated. |
| TASK-002 | 100% | Architect review passed; state machine specification is documented and integrated. |
| TASK-003 | 100% | Architect review passed after metadata and TEST_MATRIX cleanup; event contracts are documented and integrated. |
| TASK-004 | 100% | QA review passed; risk limits specification is documented and integrated. |
| TASK-005 | 100% | QA review passed; recovery protocol specification is documented and integrated. |
| TASK-006 | 100% | Architect re-review passed; initial SQLite schema is documented, validated, and integrated. |
| TASK-007 | 100% | QA review passed; SQLite WAL bootstrap is implemented and integrated. |
| TASK-008 | 100% | Architect review passed; Ledger models are implemented and integrated. |
| TASK-009 | 100% | Architect and QA reviews passed; EventStore append/read APIs are implemented and integrated. |
| TASK-010 | 100% | Ledger/PM review passed; EventStore test coverage is integrated. |
| TASK-011 | 100% | Architect review passed; deterministic clientOrderId integrated. |
| TASK-012 | 100% | QA review passed; Ledger idempotency helpers integrated. |
| TASK-013 | 100% | QA review passed; cumulative fill reconciliation integrated. |
| TASK-014 | 100% | Ledger and QA reviews passed; ACK_UNKNOWN retry guard integrated. |
| TASK-015 | 100% | Ledger review passed; Sprint 3 integration tests integrated. |
| TASK-016 | 100% | PM fallback review passed; unresolved ORDER_SENT scanner integrated. |
| TASK-017 | 100% | PM fallback review passed; recovery boot gate integrated. |
| TASK-018 | 100% | PM fallback review passed; partial-fill route helper integrated. |
| TASK-019 | 100% | PM fallback review passed; Sprint 4 chaos/integration tests integrated. |
| TASK-020 | 100% | Sprint 4 gate passed; report created. |
| TASK-021 | 100% | Execution / Risk review passed; book sequencing helper integrated. |
| TASK-022 | 100% | QA / Chaos review passed; gap/stale invalidation integrated. |
| TASK-023 | 100% | Execution / Risk and QA / Chaos reviews passed; snapshot resync helper integrated. |
| TASK-024 | 100% | Sprint 5 focused and full test suites passed; TEST_MATRIX updated. |
| TASK-025 | 100% | Sprint 5 gate passed; report created. |
| TASK-026 | 100% | Execution / Risk review passed; BookExecutionFeatures fail-closed usability integrated. |
| TASK-027 | 100% | Market Data and QA reviews passed; spread/depth/imbalance/volatility helpers integrated. |
| TASK-028 | 100% | Market Data and QA reviews passed; SlippageEstimator integrated with explicit failure reasons. |
| TASK-029 | 100% | Execution / Risk review passed; FeatureCache stale fail-closed behavior integrated. |
| TASK-030 | 100% | Sprint 6 gate passed after P1 QA findings were corrected and re-reviewed. |
| TASK-031 | 100% | LocalOrderBook/BookBuilder snapshot/diff gate correction implemented and QA re-review passed. |
| TASK-032 | 100% | BookExecutionFeatures book_age_ms/in_sync gate correction implemented and QA re-review passed. |
| TASK-033 | 100% | Sprint 5/6 gate revalidated: focused 47 tests passed, full suite 140 tests passed, ruff passed. |
| TASK-007-01 | 100% | Dataset contract passed Market Data re-review after correcting bookTicker coverage, complete-month window, and funding carry formula. |
| TASK-007-02 | 100% | Pair selection passed Backtest re-review after fail-closed cost-quality/tail-spread fixes and regression tests. |
| TASK-007-03 | 100% | Stationarity wrappers passed QA/Backtest re-review after no-look-ahead rolling-correlation fix and regression tests. |
| TASK-007-04 | 100% | Kalman Filter synthetic implementation passed Backtest and QA review with no blocking findings. |
| TASK-007-05 | 100% | OU estimator passed QA re-review after non-unit-dt sigma fix and regression test; rolling z-score remains no-look-ahead. |
| TASK-007-06 | 100% | Exploratory notebooks created and Documentation Agent re-review passed; notebooks use synthetic smoke data only. |
| TASK-007-07 | 100% | Research tests passed Quant Research Agent review; focused suite passed 31 tests. |
| TASK-007-08 | 100% | Final Sprint 7 report written and PM/Documentation review passed. Later TASK-007-10 evidence work superseded the earlier Sprint 8 block and opened Sprint 8 for 31 June-2023 cost-gated pairs. |
| TASK-007-09 | 100% | Historical Binance loader/normalizer, local runner smoke, BTCUSDT 2023-06 real one-month smoke, full 2023-06 through 2026-05 dataset run, and statistical research gate passed. Market Data Agent review PASSA (2 P3 findings, non-blocking). QA Agent review PASSA (2 P2 + 1 P3 findings, non-blocking, no P1). Moved to DONE. |
| TASK-007-10 | 100% | Three-phase result. Phase 1: probed the real Binance bookTicker source (monthly+daily) for all 20 symbols across the full 36-month window; result `SOURCE_INCOMPLETE_FAIL_CLOSED` (only 11/36 months exist for any symbol), independently verified against the live S3 endpoint (not a pagination artifact), QA re-review PASSA. Phase 2 (ADR-0007): built a memory-safe daily-bookTicker downloader (`scripts/run_sprint7_execution_cost_download.py`, processes one symbol-day at a time after a monthly download attempt caused an OOM kill), and ran an initial real June-2023 pilot for 6 symbols / 6 pairs, producing 4326 checksum-verified hourly rows and 5/6 pair PASS. Phase 3 (2026-07-02): hardened the runner to stream-read ZIP members with numeric dtypes, then expanded the real June-2023 run to all 15 symbols appearing in the 41 Sprint 7 candidate pairs. Verified 450 Binance daily ZIPs + .CHECKSUM files (17.98GB compressed), produced 10827 raw hourly rows, isolated 27 duplicate symbol-hours, wrote 10800 deduplicated hourly rows, and ran the cost gate for all 41 candidate pairs. Result: `cost_gated_pass=true`; 31/41 pairs pass with genuine June-2023 cost evidence; 10/41 fail, all containing ADAUSDT, because ADAUSDT median spread is 3.52bps > 3.0bps. Sprint 8 may now open SCOPED to the 31 passed pairs under the June-2023 evidence window per ADR-0007; failed ADAUSDT pairs and broader/full-window claims remain statistical-only. |
| TASK-008-01 | 100% | `project_control/SPRINT8_UNIVERSE.json` created: 31 approved pairs, 10 ADAUSDT-blocked pairs, cost-gate artifacts referenced. `load_sprint8_universe_contract`/`validate_sprint8_universe_contract` fail closed on scope/count/ADA mismatches. Tested in `tests/test_sprint8_universe.py` (5 tests). |
| TASK-008-02 | 100% | `build_walk_forward_splits` implemented: `train_end < test_start` enforced, non-overlapping folds. Backtest Agent review PASSA (no issues in splits). Tested in `tests/test_sprint8_walk_forward.py` (3 tests). |
| TASK-008-03 | 100% | `generate_pair_signal_intents`/`generate_offline_signal_intent` implemented on causal rolling z-score + sequential Kalman spread. Quant Research Agent review found and PM fixed a P1 look-ahead (OU/half-life gate was fit once on the full sample instead of a causal trailing window); fix independently re-confirmed PASSA with a dedicated causal-safety regression test. |
| TASK-008-04 | 100% | `run_cost_aware_backtest` + `scripts/run_sprint8_backtest.py` implemented. Backtest Agent found and PM fixed a P1 beta-weighting mismatch; Market Data Agent found and PM fixed a P1 missing exit-cost understatement. Both independently re-confirmed PASSA. QA Agent found the runner had zero direct test coverage (P2); PM added `tests/test_sprint8_backtest_runner.py` (6 tests). |
| TASK-008-05 | 100% | `summarize_backtest_metrics` + per-pair CSV/JSON ranking (`sprint8_backtest_pair_results.csv`/`.json`) implemented: gross/cost/net PnL bps, hit rate, per-pair max drawdown, turnover, net PnL quote. Corrected run: 31 evaluated, 13 approved, 18 rejected. |
| TASK-008-06 | 100% | 20 new Sprint 8 tests across 4 files (universe, walk-forward, signal/backtest module, backtest runner), including a dedicated no-look-ahead regression test. Full suite: 211 passed. |
| TASK-008-07 | 100% | `reports/sprint_08_backtest.md` written with corrected methodology, full results, review history (including the 3 P1 findings and fixes), and explicit portfolio-vs-per-pair gate distinction. Sprint 9 gate: PASSA, scoped to 13 backtest-approved pairs. |
| TASK-008-08 | 0% | BLOCKED. 17GB of raw checksum-verified Binance archives remain preserved under `data/research/binance_public/cost_pilot/raw/`. Do not delete until the user explicitly accepts the evidence state and approves cleanup. |
| TASK-009-01 | 100% | `src/backtest/fill_model.py` implemented: MARKET/IOC and LIMIT+TTL fills against level-1 quotes only, reusing `estimate_slippage`; latency via earliest-reachable-quote selection; ACK_UNKNOWN via deterministic hash of order_id, integrated with `AckGuardOrderStatus`. Found and fixed two real bugs: (1) `_coerce_side` did not catch the raw `ValueError` from an invalid `SlippageSide` string; (2) `estimate_slippage` nulls `average_price` on any partial fill, which was silently zeroing a leg's real PnL downstream -- fixed in `_realized_price_and_slippage`. QA Agent re-review PASSA, independently confirmed the fix's math. |
| TASK-009-02 | 100% | `src/backtest/execution_simulator.py` implemented: beta-weighted round-trip entry/exit using fill_model, LEG_FILL_MISMATCH detection, genuine integration with `evaluate_ack_guard` to delay exit when entry is still ACK_UNKNOWN-unresolved. Found and fixed a real bug: the ack-guard delay check compared entry's static ack_status without accounting for whether reconciliation would already be complete by the planned exit time. Backtest Agent review PASSA (report-communication findings only, addressed in reports/backtest_executable_v1.md). |
| TASK-009-03 | 100% | `src/backtest/replay_engine.py` implemented: reuses `generate_pair_signal_intents` unchanged, bounded FIFO day-cache (never holds unbounded decompressed days). Market Data Agent review found a P1 (checksum computed but never verified before use, fail-open) -- fixed by calling `verify_checksum_file`, with new regression tests for missing-sidecar and mismatch cases. |
| TASK-009-04 | 100% | `tests/test_sprint9_chaos.py` added: large data-gap NO_QUOTE, zero-liquidity zero-fill (no crash), simultaneous both-leg exit failure (NO_EXIT_FILL), invalid-side fail-closed. Full suite: 242 passed, ruff clean. |
| TASK-009-05 | 100% | `scripts/run_sprint9_replay.py` run for real (3 full runs: initial, post-partial-fill-bug-fix, post-checksum-fix) against real checksum-verified June-2023 tick data, no new downloads. Final result: 247 signals, 239 executed trades, 0/13 pairs net-positive, portfolio -$2266.27. Corrected the runner's default pair scope after discovering it used all 31 cost-gated pairs instead of the 13 Sprint 8 backtest-approved pairs (which had also contributed to an earlier OOM crash via BTCUSDT). |
| TASK-009-06 | 100% | `reports/backtest_executable_v1.md` written with full methodology, real results, the partial-fill bug story, all 4 formal review findings (Backtest/QA/Market Data/Execution-Risk Agent), and an explicit gate decision: NAO PASSA for "PnL positivo em cenario conservador," with the caveat (Execution/Risk Agent) that this reflects the most expensive execution style tested, not proof the strategy has zero edge. |
