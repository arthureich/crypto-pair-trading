# TASK-007-03 - Implementar stationarity.py

## Sprint

Sprint 7 - Research base: pair selection, Kalman e OU

## Dono

Quant Research Agent

## Revisor obrigatorio

QA Agent

## Contexto obrigatorio

Antes de comecar, leia:

- project_control/PROJECT_STATE.md
- project_control/CURRENT_SPRINT.md
- project_control/TEST_MATRIX.md
- tasks/sprint_07/TASK-007-01-historical-dataset.md
- tasks/sprint_07/TASK-007-03-stationarity.md

## Objetivo

Implementar wrappers e metricas de estacionariedade para pesquisa de pares,
incluindo ADF, KPSS, half-life preliminar, correlacao rolling e estabilidade de
spread.

## Escopo

- ADF wrapper com retorno padronizado
- KPSS wrapper com retorno padronizado
- half-life preliminar
- correlacao rolling
- estabilidade de spread
- flags para pares claramente nao estacionarios
- separacao explicita entre full-sample exploratorio e rolling/no-look-ahead

## Fora de escopo

- Kalman Filter
- OU estimator completo
- backtest completo
- XGBoost
- live trading

## Arquivos permitidos

- src/research/stationarity.py
- src/research/__init__.py
- tests/test_stationarity.py
- project_control/HANDOFFS.md

## Arquivos proibidos

- src/live/
- src/execution/
- src/ledger/
- src/models/

## Criterio de pronto

- ADF/KPSS retornam estrutura padronizada
- half-life preliminar e calculada
- correlacao rolling usa apenas dados disponiveis ate cada ponto
- pares nao estacionarios podem ser rejeitados/alertados
- erros de amostra insuficiente sao explicitos
- testes passam

## Testes obrigatorios

- `pytest tests/test_stationarity.py`

## Handoff esperado

Atualizar project_control/HANDOFFS.md com:

- o que foi feito
- arquivos alterados
- testes rodados
- limitacoes estatisticas
- pendencias
- riscos
