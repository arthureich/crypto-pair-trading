# TASK-007-08 - Gerar relatorio research_sprint_07.md

## Sprint

Sprint 7 - Research base: pair selection, Kalman e OU

## Dono

Documentation Agent

## Revisor obrigatorio

PM Agent

## Contexto obrigatorio

Antes de comecar, leia:

- project_control/PROJECT_STATE.md
- project_control/CURRENT_SPRINT.md
- project_control/TEST_MATRIX.md
- project_control/HANDOFFS.md
- notebooks/01_pair_selection.ipynb, se existir
- notebooks/02_kalman_ou.ipynb, se existir
- tasks/sprint_07/TASK-007-08-research-report.md

## Objetivo

Criar o relatorio final do Sprint 7 com dados utilizados, filtros, candidatos,
resultados Kalman/OU, pares aprovados/rejeitados, riscos e conclusao PASSA/NAO
PASSA para Sprint 8.

## Escopo

- objetivo do sprint
- dados utilizados
- filtros de universo
- tabela de pares candidatos
- resultado Kalman
- resultado OU
- pares aprovados
- pares rejeitados e motivos
- riscos
- conclusao

## Fora de escopo

- iniciar Sprint 8
- backtest estatistico completo
- paper trading
- live trading
- XGBoost
- P_fill/P_profit

## Arquivos permitidos

- reports/research_sprint_07.md
- project_control/HANDOFFS.md
- project_control/PROJECT_STATE.md
- project_control/TASK_BOARD.md

## Arquivos proibidos

- src/live/
- src/execution/
- src/ledger/
- src/models/

## Criterio de pronto

- relatorio inclui dados, periodo, simbolos, fonte, frequencia e limpeza
- filtros de volume, spread, liquidez, funding e historico minimo aparecem
- pares candidatos sao listados com metricas e status
- Kalman beta_t/alpha_t/spread_t e estabilidade sao descritos
- OU theta/mu/sigma/half-life/z-score sao descritos
- pares rejeitados tem motivo
- riscos de overfitting, amostra, regime, funding e liquidez aparecem
- conclusao PASSA/NAO PASSA e consistente com evidencias

## Testes obrigatorios

- Confirmar resultado real dos testes:
- `pytest tests/test_pair_selection.py`
- `pytest tests/test_stationarity.py`
- `pytest tests/test_kalman.py`
- `pytest tests/test_ou.py`

## Handoff esperado

Atualizar project_control/HANDOFFS.md com:

- status IN_REVIEW
- o que foi feito
- arquivos alterados
- testes rodados
- pares aprovados
- pares rejeitados
- pendencias
- riscos
- proximo passo recomendado
