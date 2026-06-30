# CURRENT_SPRINT

## Sprint

Sprint 6 - Execution Features and Slippage

## Objetivo

Create pure execution-quality features derived from trusted local book health evidence before any full Execution Risk Gate or order router exists.

## Escopo permitido

- Compute spread_bps and mid price from supplied best bid/ask.
- Compute depth within 5 bps and 10 bps from supplied book levels.
- Compute order book imbalance.
- Estimate buy/sell slippage from supplied book depth and notional/quantity inputs.
- Mark execution features unusable when book health is stale, invalid, out of sync, or requires resync.
- Maintain a lightweight in-memory feature cache.
- Add focused unit tests for execution features, slippage, cache freshness, and fail-closed usability.

## Fora de escopo

- Full Execution Risk Gate.
- Order router.
- Live WebSocket clients.
- Exchange REST clients.
- Real market-data ingestion.
- Signal generation.
- Kalman/OU research.
- ML features or XGBoost.
- Backtest engine.
- Paper trading.
- Real trading endpoint calls.

## Entregaveis obrigatorios

- `src/features/execution_features.py`
- `src/features/__init__.py`
- `src/execution/slippage_estimator.py`
- `src/market_data/feature_cache.py`
- `tests/test_execution_features.py`
- `tests/test_slippage_estimator.py`

## Criterio de pronto

- Spread bps is computed correctly.
- Depth within 5 bps and 10 bps is computed on both sides.
- Order book imbalance is computed deterministically.
- Given a notional or quantity, buy slippage consumes asks and sell slippage consumes bids.
- Insufficient liquidity returns an explicit failure reason.
- Stale, invalid, or resync-required book evidence makes features unusable for trading.
- Feature cache returns the latest feature snapshot and marks stale data fail-closed.
- Hot path does not use DataFrame/Pandas.
- Tests pass.
- Handoffs exist for every task.

## Testes obrigatorios

- `pytest tests/test_execution_features.py`
- `pytest tests/test_slippage_estimator.py`
- `pytest tests`

## Gate para avancar

Do not advance to Sprint 7 until execution features, slippage estimation, feature cache freshness, and fail-closed book usability are implemented, tested, and reviewed.

## Agentes envolvidos

- PM Agent
- Market Data Agent
- Execution / Risk Agent
- QA / Chaos Testing Agent

## Revisores obrigatorios

- Execution / Risk Agent for feature usability semantics.
- Market Data Agent for book-derived feature ownership.
- QA / Chaos Testing Agent for slippage/depth/stale-book tests.
- PM Agent for gate and sprint state.

## Sprint tasks

| ID | Tarefa | Dono | Revisor | Status | Progresso |
|---|---|---|---|---|---:|
| TASK-026 | BookExecutionFeatures primitives | Market Data Agent | Execution / Risk Agent | DONE | 100% |
| TASK-027 | Spread, depth, imbalance, and volatility helpers | Market Data Agent | QA / Chaos Testing Agent | DONE | 100% |
| TASK-028 | Slippage estimator | Execution / Risk Agent | Market Data Agent + QA / Chaos Testing Agent | DONE | 100% |
| TASK-029 | Feature cache | Market Data Agent | Execution / Risk Agent | DONE | 100% |
| TASK-030 | Sprint 6 tests and gate review | QA / Chaos Testing Agent + PM Agent | Market Data Agent + Execution / Risk Agent | DONE | 100% |
