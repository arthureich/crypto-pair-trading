# TASK-027 - Spread, Depth, Imbalance, and Volatility Helpers

## Sprint

Sprint 6 - Execution Features and Slippage

## Dono

Market Data Agent

## Revisor obrigatorio

QA / Chaos Testing Agent

## Status

DONE

## Progresso

100%

## Objetivo

Compute spread, depth within 5/10 bps, order book imbalance, and short-window volatility from supplied book evidence without DataFrame hot-path dependencies.

## Arquivos permitidos

- `src/features/execution_features.py`
- `src/features/__init__.py`
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

- `spread_bps` is computed correctly.
- `depth_5bps` and `depth_10bps` are computed on bid and ask sides.
- `order_book_imbalance` is computed deterministically.
- 1s and 5s volatility helpers do not use future data.
- No Pandas/DataFrame dependency is used in the hot path.
- Tests pass.

## Testes obrigatorios

- `pytest tests/test_execution_features.py`

