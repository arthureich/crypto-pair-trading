# TASK-023 - Snapshot Resync Decision Helper

## Sprint

Sprint 5 - Market Data Book Health and Gap Detection

## Dono

Market Data Agent

## Revisor obrigatorio

Execution / Risk Agent + QA / Chaos Testing Agent

## Status

READY

## Progresso

25%

## Objetivo

Decide when a book requires snapshot resync after gap, stale data, or mismatch evidence.

## Arquivos permitidos

- `src/market_data/book_health.py`
- `tests/test_book_health.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Criterio de pronto

- Snapshot mismatch requires resync.
- Incomplete snapshot requires resync.
- Healthy in-sequence book does not require resync.
- Tests pass.
