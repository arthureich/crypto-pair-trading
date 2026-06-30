# TASK-007-02 - Implementar pair_selection.py

## Sprint

Sprint 7 - Research base: pair selection, Kalman e OU

## Dono

Quant Research Agent

## Revisor obrigatorio

Backtest Agent

## Contexto obrigatorio

Antes de comecar, leia:

- project_control/PROJECT_STATE.md
- project_control/CURRENT_SPRINT.md
- project_control/INTERFACES.md
- tasks/sprint_07/TASK-007-01-historical-dataset.md
- tasks/sprint_07/TASK-007-02-pair-selection.md

## Objetivo

Implementar selecao inicial de pares candidatos com filtros explicitos,
ranking, metricas e motivos de aprovacao/rejeicao.

## Escopo

- carregar universo ja normalizado
- filtrar ativos por historico minimo
- filtrar por volume/liquidez/spread medio/funding
- gerar combinacoes de pares
- calcular correlacao rolling sem look-ahead quando em modo rolling
- ranquear pares candidatos
- produzir estruturas de relatorio com metricas e motivos

## Fora de escopo

- Kalman Filter
- OU estimator
- backtest completo
- XGBoost
- P_fill/P_profit
- live trading
- order router

## Arquivos permitidos

- src/research/pair_selection.py
- src/research/__init__.py
- tests/test_pair_selection.py
- project_control/HANDOFFS.md

## Arquivos proibidos

- src/live/
- src/execution/
- src/ledger/
- src/models/

## Criterio de pronto

- ativo sem dados suficientes e rejeitado
- par com baixa correlacao e rejeitado
- pares candidatos sao ranqueados por score deterministico
- motivos de rejeicao sao preservados
- filtros de liquidez/spread/funding sao testaveis
- nao ha DataFrame global mutavel
- testes passam

## Testes obrigatorios

- `pytest tests/test_pair_selection.py`

## Handoff esperado

Atualizar project_control/HANDOFFS.md com:

- o que foi feito
- arquivos alterados
- testes rodados
- pares/metricas de exemplo, se houver
- pendencias
- riscos

