# TASK-008-01 - Congelar universo e contrato de evidencia

## Sprint

Sprint 8 - Backtest walk-forward cost-aware

## Agente

PM Agent

## Revisor obrigatorio

Backtest Agent + Market Data Agent

## Task

Criar o contrato formal e carregavel do universo Sprint 8: somente os 31 pares
com `cost_gated_pass=true` em junho/2023, com os 10 pares ADAUSDT bloqueados
fail-closed e com referencia aos artefatos de evidencia que sustentam o escopo.

## Contexto obrigatorio

Leia antes de executar:

- project_control/PROJECT_STATE.md
- project_control/CURRENT_SPRINT.md
- project_control/BLOCKERS.md
- project_control/DECISIONS.md
- project_control/TEST_MATRIX.md
- reports/research_sprint_07.md
- data/research/binance_public/cost_pilot/all_candidates_202306_execution_cost_gate.json
- data/research/binance_public/cost_pilot/all_candidates_202306_manifest.json
- data/research/binance_public/cost_pilot/all_candidates_202306_source_review.json

## Arquivos permitidos

- project_control/
- tasks/sprint_08/
- reports/
- docs/
- data/research/binance_public/cost_pilot/*summary*.json
- data/research/binance_public/cost_pilot/*manifest*.json
- data/research/binance_public/cost_pilot/*gate*.json
- data/research/binance_public/cost_pilot/*gate*.csv
- src/research/
- tests/

## Arquivos proibidos

- src/ledger/
- src/execution/
- src/recovery/
- src/live/
- src/models/
- qualquer endpoint de exchange/trading
- arquivos raw ZIP/.CHECKSUM de `data/research/binance_public/cost_pilot/raw/`

## Criterio de pronto

- contrato do universo Sprint 8 documenta os 31 pares aprovados;
- contrato documenta os 10 pares ADAUSDT rejeitados e o motivo;
- contrato referencia exatamente a janela `2023-06` e os artefatos de custo;
- nenhum par statistical-only aparece como cost-gated;
- TASK-008-02 e TASK-008-03 podem consumir o contrato sem reprocessar raw;
- `project_control/TASK_BOARD.md`, `CURRENT_SPRINT.md` e `HANDOFFS.md` ficam consistentes.

## Testes obrigatorios

- teste que carrega o contrato e encontra exatamente 31 pares aprovados;
- teste que garante que nenhum par aprovado contem `ADAUSDT`;
- teste que garante que os 10 pares ADAUSDT ficam fail-closed;
- `ruff check src tests scripts`

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` com:

- caminho do contrato criado;
- contagem de pares aprovados/rejeitados;
- artefatos de evidencia usados;
- testes rodados;
- tarefas desbloqueadas.

## Status

READY

## Progresso

0%

## Prompt de delegacao

Agente: PM Agent

Sprint atual: Sprint 8 - Backtest walk-forward cost-aware

Task: TASK-008-01 - Congelar universo e contrato de evidencia

Contexto obrigatorio:

```text
Sprint 8 so pode operar nos 31 pares com cost_gated_pass=true para junho/2023.
Os 10 pares com ADAUSDT falharam por WIDE_MEDIAN_SPREAD e devem falhar
fechado. A evidencia e real, mas escopada a junho/2023.
```

Arquivos permitidos:

```text
project_control/
tasks/sprint_08/
reports/
docs/
data/research/binance_public/cost_pilot/*summary*.json
data/research/binance_public/cost_pilot/*manifest*.json
data/research/binance_public/cost_pilot/*gate*.json
data/research/binance_public/cost_pilot/*gate*.csv
src/research/
tests/
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
Contrato carregavel com 31 pares aprovados, 10 rejeitados, janela exata,
referencia aos artefatos e testes fail-closed.
```

Testes obrigatorios:

```text
pytest <novo teste de contrato de universo>
ruff check src tests scripts
```

Handoff esperado:

```text
Registrar contrato criado, testes rodados e liberar TASK-008-02/TASK-008-03
se passar.
```
