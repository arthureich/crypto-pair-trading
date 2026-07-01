# TASK-028 - Slippage Estimator

## Sprint

Sprint 6 - Execution Features and Slippage

## Dono

Execution / Risk Agent

## Revisor obrigatorio

Market Data Agent + QA / Chaos Testing Agent

## Status

DONE

## Progresso

100%

## Objetivo

Estimate buy and sell slippage from supplied book levels before any order router exists.

## Arquivos permitidos

- `src/execution/slippage_estimator.py`
- `src/execution/__init__.py`
- `tests/test_slippage_estimator.py`
- `project_control/HANDOFFS.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/ledger/`
- `src/recovery/`
- `src/live/`
- `docs/`
- `migrations/`

## Criterio de pronto

- Buy slippage consumes asks.
- Sell slippage consumes bids.
- VWAP is computed from supplied levels.
- Insufficient liquidity returns an explicit failure decision/reason.
- Invalid quantity/notional inputs fail closed.
- Tests pass.

## Testes obrigatorios

- `pytest tests/test_slippage_estimator.py`
