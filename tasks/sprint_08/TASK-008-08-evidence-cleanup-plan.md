# TASK-008-08 - Preparar limpeza segura dos arquivos raw de evidencia

## Sprint

Sprint 8 - Backtest walk-forward cost-aware

## Agente

Market Data Agent

## Revisor obrigatorio

PM Agent + QA / Chaos Testing Agent

## Task

Preparar um plano de limpeza segura dos arquivos raw grandes de evidencia,
sem apagar nada ate haver aceite explicito.

## Contexto obrigatorio

- project_control/CURRENT_SPRINT.md
- project_control/HANDOFFS.md
- data/research/binance_public/cost_pilot/all_candidates_202306_archive_manifest.csv
- data/research/binance_public/cost_pilot/all_candidates_202306_manifest.json
- data/research/binance_public/cost_pilot/all_candidates_202306_source_review.json
- data/research/binance_public/cost_pilot/all_candidates_202306_execution_cost_gate.json

## Arquivos permitidos

- project_control/
- tasks/sprint_08/
- reports/
- data/research/binance_public/cost_pilot/*.json
- data/research/binance_public/cost_pilot/*.csv

## Arquivos proibidos

- src/ledger/
- src/execution/
- src/recovery/
- src/live/
- src/models/
- apagar `data/research/binance_public/cost_pilot/raw/` sem aprovacao explicita

## Criterio de pronto

- listar exatamente quais arquivos raw podem ser apagados depois do aceite;
- listar exatamente quais artefatos pequenos devem permanecer;
- validar que manifest, source_review, gate JSON/CSV e hourly-cost deduped
  preservam auditoria suficiente;
- nao executar `rm`;
- registrar comando de limpeza proposto, mas nao rodar.

## Testes obrigatorios

- conferir existencia dos artefatos pequenos;
- conferir contagens do manifest;
- `git diff --check`.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` com plano de limpeza e aguardar
aprovacao explicita do usuario antes de apagar qualquer raw.

## Status

BLOCKED

## Bloqueio

Depende de aceite do estado de evidencia e aprovacao explicita para limpeza.

## Progresso

0%

## Prompt de delegacao

Agente: Market Data Agent

Sprint atual: Sprint 8 - Backtest walk-forward cost-aware

Task: TASK-008-08 - Preparar limpeza segura dos arquivos raw de evidencia

Contexto obrigatorio:

```text
O usuario quer remover arquivos depois, mas raw ainda e evidencia auditavel.
Prepare plano, nao apague.
```

Arquivos permitidos:

```text
project_control/
tasks/sprint_08/
reports/
data/research/binance_public/cost_pilot/*.json
data/research/binance_public/cost_pilot/*.csv
```

Arquivos proibidos:

```text
src/ledger/
src/execution/
src/recovery/
src/live/
src/models/
data/research/binance_public/cost_pilot/raw/ para delecao
```

Criterio de pronto:

```text
Plano seguro de limpeza, sem executar delecao.
```

Testes obrigatorios:

```text
conferir manifest/source_review/gate/hourly-cost
git diff --check
```

Handoff esperado:

```text
Registrar plano e aguardar aprovacao explicita.
```
