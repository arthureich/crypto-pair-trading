# TASK-022 - Gap and Stale Book Invalidation

## Sprint

Sprint 5 - Market Data Book Health and Gap Detection

## Dono

Market Data Agent

## Revisor obrigatorio

QA / Chaos Testing Agent

## Status

READY

## Progresso

25%

## Objetivo

Invalidate book health when L2 sequence gaps or stale timestamps are detected.

## Arquivos permitidos

- `src/market_data/book_health.py`
- `tests/test_book_health.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Criterio de pronto

- Gap invalidates the book.
- Stale book invalidates the book.
- Invalid book status clearly blocks entry eligibility.
- Tests pass.
