# TASK-008-02 - Implementar walk-forward split causal

## Sprint

Sprint 8 - Backtest walk-forward cost-aware

## Agente

Backtest Agent

## Revisor obrigatorio

QA / Chaos Testing Agent

## Task

Implementar geracao de splits walk-forward offline para os 31 pares aprovados,
sem usar futuro para formar janelas de treino, calibracao ou decisao.

## Contexto obrigatorio

- project_control/CURRENT_SPRINT.md
- tasks/sprint_08/TASK-008-01-freeze-universe-evidence.md
- contrato de universo produzido pela TASK-008-01
- data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv
- src/research/pair_selection.py
- src/research/kalman.py
- src/research/ou.py
- src/research/stationarity.py

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
- notebooks/

## Criterio de pronto

- split walk-forward tem treino, validacao e teste definidos por tempo;
- nenhuma estatistica usa dados posteriores ao timestamp de decisao;
- pares sem cobertura suficiente falham fechado;
- splits sao serializaveis/reprodutiveis;
- logs/relatorio indicam janela usada em cada fold.

## Testes obrigatorios

- teste de fronteira temporal sem look-ahead;
- teste de rejeicao por cobertura insuficiente;
- teste de reproducibilidade dos folds;
- `pytest tests/test_pair_selection.py tests/test_kalman.py tests/test_ou.py`;
- `ruff check src tests scripts`.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` com folds definidos, testes, riscos e
se TASK-008-04 pode ser desbloqueada parcialmente.

## Status

BLOCKED

## Bloqueio

Depende de TASK-008-01.

## Progresso

0%

## Prompt de delegacao

Agente: Backtest Agent

Sprint atual: Sprint 8 - Backtest walk-forward cost-aware

Task: TASK-008-02 - Implementar walk-forward split causal

Contexto obrigatorio:

```text
Use apenas o contrato de universo Sprint 8 congelado. Nenhum split pode usar
dados futuros para calcular features, parametros ou decisoes.
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
notebooks/
```

Criterio de pronto:

```text
Folds walk-forward reproduziveis e testados contra look-ahead.
```

Testes obrigatorios:

```text
pytest <novos testes de split walk-forward>
pytest tests/test_pair_selection.py tests/test_kalman.py tests/test_ou.py
ruff check src tests scripts
```

Handoff esperado:

```text
Registrar folds, arquivos criados, testes e desbloqueios.
```
