# TASK-007-04 - Implementar Kalman Filter

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
- project_control/INTERFACES.md
- src/research/stationarity.py, se existir
- tasks/sprint_07/TASK-007-04-kalman-filter.md

## Objetivo

Implementar o Kalman Filter para estimar hedge ratio dinamico beta_t,
alpha_t e spread_t entre dois ativos.

## Escopo

- funcao de fit/update
- calculo de beta_t
- calculo de alpha_t
- calculo de spread_t
- innovation
- state covariance
- controle basico de ruido de observacao e estado
- flag/alerta para beta_t explosivo
- teste com dados sinteticos

## Fora de escopo

- XGBoost
- backtest completo
- live trading
- order router
- Risk Gate

## Arquivos permitidos

- src/research/kalman.py
- src/research/__init__.py
- tests/test_kalman.py
- project_control/HANDOFFS.md

## Arquivos proibidos

- src/live/
- src/execution/
- src/ledger/
- src/models/

## Criterio de pronto

- beta_t e estimado
- alpha_t e estimado
- spread_t e calculado
- dados sinteticos com beta conhecido sao recuperados de forma razoavel
- beta explosivo gera alerta ou flag
- resultado e reprodutivel
- testes passam

## Testes obrigatorios

- `pytest tests/test_kalman.py`

## Handoff esperado

Atualizar project_control/HANDOFFS.md com:

- o que foi feito
- arquivos alterados
- testes rodados
- parametros default
- pendencias
- riscos
