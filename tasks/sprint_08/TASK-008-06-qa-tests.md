# TASK-008-06 - Criar testes de Sprint 8

## Sprint

Sprint 8 - Backtest walk-forward cost-aware

## Agente

QA / Chaos Testing Agent

## Revisor obrigatorio

Backtest Agent + PM Agent

## Task

Criar e revisar a cobertura de testes da Sprint 8: universo, no-look-ahead,
SignalIntent offline, custo causal, PnL liquido e fail-closed.

## Contexto obrigatorio

- project_control/CURRENT_SPRINT.md
- project_control/TEST_MATRIX.md
- outputs das TASK-008-01 a TASK-008-04
- tests/

## Arquivos permitidos

- tests/
- src/research/
- scripts/
- project_control/
- tasks/sprint_08/

## Arquivos proibidos

- src/ledger/
- src/execution/
- src/recovery/
- src/live/
- src/models/
- data/research/binance_public/cost_pilot/raw/

## Criterio de pronto

- testes cobrem universo dos 31 pares;
- testes bloqueiam ADAUSDT;
- testes detectam look-ahead;
- testes provam custo aplicado causalmente;
- testes provam que SignalIntent offline nao toca execution/ledger;
- suite completa passa;
- TEST_MATRIX atualizado.

## Testes obrigatorios

- `pytest tests`
- `ruff check src tests scripts`
- `git diff --check`

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` e `project_control/TEST_MATRIX.md`
com testes adicionados, falhas encontradas e status de gate.

## Status

BLOCKED

## Bloqueio

Depende das surfaces implementadas em TASK-008-01 a TASK-008-04.

## Progresso

0%

## Prompt de delegacao

Agente: QA / Chaos Testing Agent

Sprint atual: Sprint 8 - Backtest walk-forward cost-aware

Task: TASK-008-06 - Criar testes de Sprint 8

Contexto obrigatorio:

```text
Sprint 8 deve falhar fechado contra par fora do universo, ADAUSDT, custo
ausente e look-ahead. SignalIntent e offline e nao pode tocar execution/ledger.
```

Arquivos permitidos:

```text
tests/
src/research/
scripts/
project_control/
tasks/sprint_08/
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
Cobertura de gate Sprint 8 com pytest/ruff/diff-check limpos.
```

Testes obrigatorios:

```text
pytest tests
ruff check src tests scripts
git diff --check
```

Handoff esperado:

```text
Registrar cobertura, falhas e recomendacao PASSA/NAO PASSA.
```
