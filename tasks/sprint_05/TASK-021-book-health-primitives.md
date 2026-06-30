# TASK-021 - Book Health and L2 Sequencing Primitives

## Sprint

Sprint 5 - Market Data Book Health and Gap Detection

## Dono

Market Data Agent

## Revisor obrigatorio

Execution / Risk Agent

## Status

IN_PROGRESS

## Progresso

25%

## Objetivo

Create pure market-data primitives for L2 update sequence tracking and book-health status.

## Arquivos permitidos

- `src/market_data/book_health.py`
- `src/market_data/__init__.py`
- `tests/test_book_health.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/execution/`
- `src/ledger/`
- `src/recovery/`
- `src/live/`
- `docs/`
- `migrations/`

## Criterio de pronto

- L2 update input model exists.
- Book health status/reason enums exist.
- In-sequence updates can be classified healthy.
- Sequence gap can be represented without exchange clients.
- Tests pass.

## Testes obrigatorios

- `pytest tests/test_book_health.py`
