# TASK-029 - Feature Cache

## Sprint

Sprint 6 - Execution Features and Slippage

## Dono

Market Data Agent

## Revisor obrigatorio

Execution / Risk Agent

## Status

DONE

## Progresso

100%

## Objetivo

Create a lightweight in-memory feature cache for latest execution features by symbol.

## Arquivos permitidos

- `src/market_data/feature_cache.py`
- `src/market_data/__init__.py`
- `tests/test_execution_features.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/ledger/`
- `src/recovery/`
- `src/live/`
- `docs/`
- `migrations/`

## Criterio de pronto

- Latest features can be stored and retrieved by symbol.
- Cache lookup returns a snapshot, not mutable internal state.
- Stale cache entries are marked unusable/fail-closed.
- No DataFrame/Pandas dependency is used.
- Tests pass.

## Testes obrigatorios

- `pytest tests/test_execution_features.py`
