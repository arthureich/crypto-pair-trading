# TASK-033 - Revalidar gate Sprint 5/6 antes do Sprint 7

## Sprint

Sprint 6 - Execution Features and Slippage

## Dono

QA / Chaos Testing Agent + PM Agent

## Revisor obrigatorio

Market Data Agent + Execution / Risk Agent

## Contexto obrigatorio

Antes de comecar, leia:

- project_control/PROJECT_STATE.md
- project_control/CURRENT_SPRINT.md
- project_control/TEST_MATRIX.md
- project_control/BLOCKERS.md
- project_control/HANDOFFS.md
- tasks/sprint_05/TASK-031-local-order-book-gate-correction.md
- tasks/sprint_06/TASK-032-bookfeatures-health-fields.md
- tasks/sprint_06/TASK-033-revalidate-s5-s6-gate.md

## Objetivo

Revalidar o gate dos Sprints 5 e 6 contra o checklist literal necessario para
abrir o Sprint 7.

## Escopo

- validar LocalOrderBook/BookBuilder
- validar book_age_ms e in_sync em BookFeatures
- rodar testes obrigatorios de Sprint 5/6
- atualizar blockers, handoffs, test matrix e task board

## Fora de escopo

- iniciar Sprint 7 antes do gate passar
- implementar research/Kalman/OU
- Execution Risk Gate completo
- paper trading
- live trading

## Arquivos permitidos

- project_control/BLOCKERS.md
- project_control/HANDOFFS.md
- project_control/TASK_BOARD.md
- project_control/TEST_MATRIX.md
- project_control/PROJECT_STATE.md
- reports/

## Arquivos proibidos

- src/live/
- src/ledger/
- src/research/

## Criterio de pronto

- testes de book builder passam
- testes de execution features passam
- testes de slippage passam
- suite completa passa ou qualquer falha e registrada como blocker
- blocker do gate e resolvido ou mantido ativo com motivo

## Testes obrigatorios

- `UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_book_builder.py tests/test_book_health.py tests/test_execution_features.py tests/test_slippage_estimator.py --basetemp=pytest_temp_run_task033_gate -o cache_dir=pytest_temp_run_task033_gate/.pytest_cache`
- `UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests --basetemp=pytest_temp_run_task033_all -o cache_dir=pytest_temp_run_task033_all/.pytest_cache`

## Handoff esperado

Atualizar project_control/HANDOFFS.md com:

- resultado real do gate
- testes rodados
- blockers restantes
- decisao PM sobre abertura do Sprint 7
