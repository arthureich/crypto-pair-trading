# TASK-008-07 - Gerar relatorio e gate Sprint 8

## Sprint

Sprint 8 - Backtest walk-forward cost-aware

## Agente

Documentation Agent

## Revisor obrigatorio

PM Agent + Backtest Agent

## Task

Gerar `reports/sprint_08_backtest.md` e fechar o gate Sprint 8 com base nas
metricas, testes e handoffs.

## Contexto obrigatorio

- project_control/CURRENT_SPRINT.md
- project_control/PROJECT_STATE.md
- project_control/TASK_BOARD.md
- project_control/HANDOFFS.md
- project_control/TEST_MATRIX.md
- outputs das TASK-008-01 a TASK-008-06
- reports/research_sprint_07.md

## Arquivos permitidos

- reports/
- project_control/
- tasks/sprint_08/
- docs/

## Arquivos proibidos

- src/ledger/
- src/execution/
- src/recovery/
- src/live/
- src/models/
- data/research/binance_public/cost_pilot/raw/

## Criterio de pronto

- relatorio documenta metodologia, universo, splits, custos, resultados e
  limitacoes;
- relatorio separa estatistico, cost-gated e backtest-approved;
- Sprint 9 recebe decisao PASSA/NAO PASSA;
- PROJECT_STATE, TASK_BOARD, HANDOFFS e TEST_MATRIX atualizados;
- nenhum claim extrapola junho/2023 como custo real universal.

## Testes obrigatorios

- confirmar que todos os testes de Sprint 8 foram rodados;
- `git diff --check`;
- revisao PM + Backtest.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` com conclusao do Sprint 8, pares que
sobraram, riscos e decisao de gate para Sprint 9.

## Status

BLOCKED

## Bloqueio

Depende de TASK-008-05 e TASK-008-06.

## Progresso

0%

## Prompt de delegacao

Agente: Documentation Agent

Sprint atual: Sprint 8 - Backtest walk-forward cost-aware

Task: TASK-008-07 - Gerar relatorio e gate Sprint 8

Contexto obrigatorio:

```text
O relatorio nao pode vender Sprint 8 como live-ready. Ele decide apenas quais
pares sobrevivem ao backtest offline cost-aware.
```

Arquivos permitidos:

```text
reports/
project_control/
tasks/sprint_08/
docs/
```

Arquivos proibidos:

```text
src/ledger/
src/execution/
src/recovery/
src/live/
src/models/
data/research/binance_public/cost_pilot/raw/
```

Criterio de pronto:

```text
Relatorio Sprint 8 completo, gate Sprint 9 claro, arquivos de controle
atualizados.
```

Testes obrigatorios:

```text
git diff --check
confirmar pytest/ruff da Sprint 8 nos handoffs
```

Handoff esperado:

```text
Registrar decisao PASSA/NAO PASSA para Sprint 9.
```
