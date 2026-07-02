# TASK-008-05 - Calcular metricas e ranking de sobrevivencia

## Sprint

Sprint 8 - Backtest walk-forward cost-aware

## Agente

Backtest Agent

## Revisor obrigatorio

PM Agent + Quant Research Agent

## Task

Calcular metricas por par e por portfolio offline para decidir quais pares
continuam depois do backtest cost-aware.

## Contexto obrigatorio

- outputs da TASK-008-04
- project_control/CURRENT_SPRINT.md
- reports/research_sprint_07.md
- data/research/binance_public/cost_pilot/all_candidates_202306_execution_cost_gate.csv

## Arquivos permitidos

- src/research/
- tests/
- scripts/
- reports/
- project_control/
- tasks/sprint_08/
- data/research/

## Arquivos proibidos

- src/ledger/
- src/execution/
- src/recovery/
- src/live/
- src/models/

## Criterio de pronto

- metricas por par: trades, hit rate, PnL bruto, custo, PnL liquido, drawdown,
  turnover, Sharpe/Sortino quando aplicavel;
- ranking separa aprovados, rejeitados e inconclusivos;
- criterios de rejeicao sao explicitos;
- resultados preservam o rotulo de escopo: custo real de junho/2023.

## Testes obrigatorios

- teste de agregacao de metricas;
- teste de ranking deterministico;
- teste de rejeicao por PnL liquido/drawdown/turnover;
- `ruff check src tests scripts`.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` com tabela de sobrevivencia,
criterios e riscos.

## Status

BLOCKED

## Bloqueio

Depende de TASK-008-04.

## Progresso

0%

## Prompt de delegacao

Agente: Backtest Agent

Sprint atual: Sprint 8 - Backtest walk-forward cost-aware

Task: TASK-008-05 - Calcular metricas e ranking de sobrevivencia

Contexto obrigatorio:

```text
Nao basta PnL bruto. Ranking precisa considerar custo, drawdown, turnover e
estabilidade. Resultado nao e autorizacao de live.
```

Arquivos permitidos:

```text
src/research/
tests/
scripts/
reports/
project_control/
tasks/sprint_08/
data/research/
```

Arquivos proibidos:

```text
src/ledger/
src/execution/
src/recovery/
src/live/
src/models/
```

Criterio de pronto:

```text
Metricas e ranking deterministico por par e portfolio offline.
```

Testes obrigatorios:

```text
pytest <novos testes de metricas/ranking>
ruff check src tests scripts
```

Handoff esperado:

```text
Registrar ranking, criterios e riscos.
```
