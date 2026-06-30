# TASK-007-06 - Criar notebooks exploratorios

## Sprint

Sprint 7 - Research base: pair selection, Kalman e OU

## Dono

Quant Research Agent

## Revisor obrigatorio

Documentation Agent

## Contexto obrigatorio

Antes de comecar, leia:

- project_control/PROJECT_STATE.md
- project_control/CURRENT_SPRINT.md
- tasks/sprint_07/TASK-007-01-historical-dataset.md
- tasks/sprint_07/TASK-007-02-pair-selection.md
- tasks/sprint_07/TASK-007-05-ou-estimator.md
- tasks/sprint_07/TASK-007-06-exploratory-notebooks.md

## Objetivo

Criar notebooks exploratorios para pair selection e Kalman/OU, documentando
dados, filtros, resultados e riscos sem transformar notebook em fonte unica de
verdade.

## Escopo

- notebook de pair selection
- notebook de Kalman/OU
- tabelas de pares aprovados/rejeitados
- graficos exploratorios, se uteis
- notas sobre full-sample versus rolling/no-look-ahead

## Fora de escopo

- notebook como motor de producao
- paper trading
- live trading
- backtest executavel completo
- XGBoost

## Arquivos permitidos

- notebooks/01_pair_selection.ipynb
- notebooks/02_kalman_ou.ipynb
- reports/research_sprint_07.md
- project_control/HANDOFFS.md

## Arquivos proibidos

- src/live/
- src/execution/
- src/ledger/
- src/models/

## Criterio de pronto

- notebooks abrem com fluxo claro
- dados utilizados estao documentados
- filtros e resultados sao reproduziveis a partir dos modulos de `src/research`
- riscos de look-ahead e overfitting aparecem explicitamente
- notebooks nao substituem testes automatizados

## Testes obrigatorios

- Rodar os testes dos modulos usados pelo notebook:
- `pytest tests/test_pair_selection.py`
- `pytest tests/test_stationarity.py`
- `pytest tests/test_kalman.py`
- `pytest tests/test_ou.py`

## Handoff esperado

Atualizar project_control/HANDOFFS.md com:

- notebooks criados
- dados e periodo usados
- testes rodados
- pendencias
- riscos

