# TASK-007-05 - Implementar OU estimator

## Sprint

Sprint 7 - Research base: pair selection, Kalman e OU

## Dono

Quant Research Agent

## Revisor obrigatorio

Backtest Agent + QA Agent

## Contexto obrigatorio

Antes de comecar, leia:

- project_control/PROJECT_STATE.md
- project_control/CURRENT_SPRINT.md
- src/research/kalman.py, se existir
- src/research/stationarity.py, se existir
- tasks/sprint_07/TASK-007-05-ou-estimator.md

## Objetivo

Implementar estimador Ornstein-Uhlenbeck para spread_t, calculando theta, mu,
sigma, half-life e z-score.

## Escopo

- estimar OU em serie de spread
- calcular theta
- calcular mu
- calcular sigma
- calcular half-life
- calcular z-score
- rejeitar/alertar theta <= 0
- controlar janelas rolling sem look-ahead

## Fora de escopo

- Kalman Filter novo
- backtest completo
- signal live
- order router
- XGBoost
- P_fill/P_profit

## Arquivos permitidos

- src/research/ou.py
- src/research/__init__.py
- tests/test_ou.py
- project_control/HANDOFFS.md

## Arquivos proibidos

- src/live/
- src/execution/
- src/ledger/
- src/models/

## Criterio de pronto

- theta, mu e sigma sao estimados
- half-life e calculado
- z-score e calculado
- theta <= 0 gera rejeicao ou alerta explicito
- serie sintetica mean-reverting gera theta positivo
- rolling z-score nao usa dado futuro
- testes passam

## Testes obrigatorios

- `pytest tests/test_ou.py`

## Handoff esperado

Atualizar project_control/HANDOFFS.md com:

- o que foi feito
- arquivos alterados
- testes rodados
- comportamento para theta <= 0
- pendencias
- riscos
