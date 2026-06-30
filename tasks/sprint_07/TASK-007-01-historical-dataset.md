# TASK-007-01 - Definir dataset historico minimo

## Sprint

Sprint 7 - Research base: pair selection, Kalman e OU

## Dono

Quant Research Agent

## Revisor obrigatorio

Market Data Agent

## Contexto obrigatorio

Antes de comecar, leia:

- project_control/PROJECT_STATE.md
- project_control/CURRENT_SPRINT.md
- project_control/INTERFACES.md
- project_control/TEST_MATRIX.md
- tasks/sprint_07/TASK-007-01-historical-dataset.md

## Objetivo

Definir o dataset historico minimo para pesquisa de pares cripto futures,
incluindo simbolos, periodo, frequencia, fonte, regras de limpeza e campos
necessarios.

## Escopo

- universo inicial de simbolos
- OHLCV historico
- mark price, se disponivel
- funding, se disponivel
- filtros minimos de historico
- documentacao de fonte, periodo e frequencia
- criterios minimos de liquidez/spread/funding

## Fora de escopo

- baixar dados live
- exchange REST/WebSocket client real
- backtest executavel
- paper trading
- live trading
- XGBoost
- P_fill/P_profit

## Arquivos permitidos

- docs/
- reports/research_sprint_07.md
- notebooks/01_pair_selection.ipynb
- project_control/HANDOFFS.md

## Arquivos proibidos

- src/live/
- src/execution/
- src/ledger/
- src/research/kalman.py
- src/research/ou.py

## Criterio de pronto

- dataset minimo esta definido
- simbolos, periodo, frequencia e fonte estao documentados
- regras de limpeza estao documentadas
- campos obrigatorios estao listados
- limites minimos de liquidez/spread/funding estao definidos
- risco de look-ahead esta explicitamente documentado

## Testes obrigatorios

- Nao ha teste automatizado obrigatorio nesta tarefa documental.
- Qualquer helper criado deve ter teste focado.

## Handoff esperado

Atualizar project_control/HANDOFFS.md com:

- o que foi definido
- fonte/periodo/frequencia
- arquivos alterados
- pendencias
- riscos

