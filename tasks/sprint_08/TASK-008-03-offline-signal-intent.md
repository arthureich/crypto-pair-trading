# TASK-008-03 - Gerar SignalIntent offline

## Sprint

Sprint 8 - Backtest walk-forward cost-aware

## Agente

Quant Research Agent

## Revisor obrigatorio

Backtest Agent + Architect Agent

## Task

Criar um gerador offline de `SignalIntent` para backtest, usando Kalman/OU,
spread e z-score em modo causal. O output e apenas simulacao; nao pode chamar
Execution Plane nem Ledger Plane.

## Contexto obrigatorio

- project_control/INTERFACES.md
- project_control/CURRENT_SPRINT.md
- contrato de universo produzido pela TASK-008-01
- src/research/kalman.py
- src/research/ou.py
- src/research/stationarity.py
- reports/research_sprint_07.md

## Arquivos permitidos

- src/research/
- tests/
- scripts/
- reports/
- project_control/
- tasks/sprint_08/

## Arquivos proibidos

- src/ledger/
- src/execution/
- src/recovery/
- src/live/
- src/models/
- qualquer API de exchange

## Criterio de pronto

- SignalIntent offline segue o contrato em `project_control/INTERFACES.md`;
- sinais sao gerados somente com dados disponiveis ate o timestamp de decisao;
- entradas/saidas do gerador sao deterministicas;
- output carrega `pair_id`, legs, z-score, beta, half-life e timestamps;
- nenhum import de `src/execution`, `src/ledger`, `src/recovery` ou live.

## Testes obrigatorios

- teste de schema minimo de SignalIntent offline;
- teste de causalidade temporal;
- teste que falha se houver dependencia de execution/ledger/recovery;
- `pytest tests/test_kalman.py tests/test_ou.py tests/test_stationarity.py`;
- `ruff check src tests scripts`.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` com schema, limites, testes e como o
Backtest Agent deve consumir os sinais.

## Status

BLOCKED

## Bloqueio

Depende de TASK-008-01.

## Progresso

0%

## Prompt de delegacao

Agente: Quant Research Agent

Sprint atual: Sprint 8 - Backtest walk-forward cost-aware

Task: TASK-008-03 - Gerar SignalIntent offline

Contexto obrigatorio:

```text
SignalIntent e advisory/offline. Nao enviar ordem, nao tocar execution, nao
tocar ledger. Sinal precisa ser causal e reprodutivel.
```

Arquivos permitidos:

```text
src/research/
tests/
scripts/
reports/
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
```

Criterio de pronto:

```text
Gerador offline de SignalIntent causal, deterministico e testado.
```

Testes obrigatorios:

```text
pytest <novos testes de SignalIntent offline>
pytest tests/test_kalman.py tests/test_ou.py tests/test_stationarity.py
ruff check src tests scripts
```

Handoff esperado:

```text
Registrar schema, exemplos, testes e instrucoes para TASK-008-04.
```
