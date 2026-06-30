# TASK-032 - Corrigir gate: BookFeatures book_age_ms/in_sync

## Sprint

Sprint 6 - Execution Features and Slippage

## Dono

Execution / Risk Agent

## Revisor obrigatorio

Market Data Agent + QA / Chaos Testing Agent

## Contexto obrigatorio

Antes de comecar, leia:

- project_control/PROJECT_STATE.md
- project_control/CURRENT_SPRINT.md
- project_control/INTERFACES.md
- docs/risk_limits.md
- src/features/execution_features.py
- tests/test_execution_features.py
- tasks/sprint_06/TASK-032-bookfeatures-health-fields.md

## Objetivo

Expor explicitamente `book_age_ms` e `in_sync` no snapshot
`BookExecutionFeatures`, preservando comportamento fail-closed e alinhando o
codigo ao contrato `BookFeatures`.

## Escopo

- campos `book_age_ms` e `in_sync` em `BookExecutionFeatures`
- derivacao de `book_age_ms` a partir de `BookHealthDecision.age_ms`
- derivacao de `in_sync` a partir de health/resync/usabilidade
- testes de book saudavel, stale, invalid, resync e book vazio

## Fora de escopo

- LocalOrderBook/BookBuilder
- Execution Risk Gate completo
- slippage estimator novo
- order router
- live trading
- research/Kalman/OU

## Arquivos permitidos

- src/features/execution_features.py
- src/features/__init__.py
- tests/test_execution_features.py

## Arquivos proibidos

- src/live/
- src/execution/
- src/ledger/
- src/research/

## Criterio de pronto

- `BookExecutionFeatures` possui `book_age_ms: int | None`
- `BookExecutionFeatures` possui `in_sync: bool`
- book saudavel e sem resync marca `in_sync=True`
- stale, invalid, resync, malformed e empty/crossed book marcam `in_sync=False`
- `usable_for_trading` continua fail-closed
- testes passam

## Testes obrigatorios

- `UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_execution_features.py --basetemp=pytest_temp_run_task032 -o cache_dir=pytest_temp_run_task032/.pytest_cache`

## Handoff esperado

Atualizar project_control/HANDOFFS.md com:

- o que foi feito
- arquivos alterados
- testes rodados
- pendencias
- riscos
