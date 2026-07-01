# TASK-007-10 - Produzir evidencia historica de custo de execucao

## Sprint

Sprint 7 - Research base: pair selection, Kalman e OU

## Agente

Market Data Agent

## Revisor obrigatorio

QA Agent + PM Agent

## Task

Produzir evidencia historica verificavel de top-of-book/L2, spread e custo de
execucao para os 41 pares estatisticos gerados pelo Sprint 7 real-dataset gate.

## Contexto obrigatorio

Antes de comecar, leia:

- project_control/PROJECT_STATE.md
- project_control/CURRENT_SPRINT.md
- project_control/BLOCKERS.md
- project_control/TEST_MATRIX.md
- docs/historical_dataset.md
- reports/research_sprint_07.md
- data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_summary.json
- data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.json
- src/research/pair_selection.py

## Objetivo

Substituir o estado `cost_gated_pass=false` por uma decisao auditavel:

- `PASS` somente se houver evidencia historica verificavel de custo de execucao;
- `FAIL` se a evidencia for ausente, incompleta, stale, inconsistente ou pior
  que os limites do Sprint 7;
- `BLOCKED` se a fonte historica necessaria nao existir publicamente.

## Escopo permitido

- investigar disponibilidade de dados historicos top-of-book/L2 ou book ticker
  para Binance USD-M;
- criar adaptador/loader de dados historicos de custo somente em `src/research/`;
- gerar dataset normalizado de spread/custo em `data/research/`;
- juntar custo historico aos pares candidatos sem look-ahead;
- calcular median/p95/p99 spread bps por simbolo e por par;
- calcular cobertura temporal e stale/gap stats da evidencia de custo;
- atualizar o gate estatistico para consumir custo somente quando a qualidade
  for verificavel;
- atualizar relatorio, handoff e matriz de testes.

## Fora de escopo

- live trading;
- order router;
- ledger;
- execution engine;
- emergency exit;
- XGBoost;
- P_fill/P_profit;
- backtest financeiro completo;
- simulacao de fill agressiva;
- alavancagem;
- multi-exchange.

## Arquivos permitidos

- src/research/
- tests/
- scripts/
- reports/
- docs/historical_dataset.md
- project_control/
- tasks/sprint_07/
- data/research/

## Arquivos proibidos

- src/live/
- src/execution/
- src/ledger/
- src/models/
- notebooks/

## Criterio de pronto

- fonte historica de custo documentada com periodo, simbolos, granularidade,
  campos, checksums/proveniencia e limites;
- se a fonte existir, dados sao normalizados com schema estavel;
- evidencia incompleta falha fechada e nao vira aproximacao silenciosa;
- custos sao unidos aos pares sem usar dados futuros;
- `median`, `p95` e `p99` de spread/custo sao calculados por simbolo e por par;
- cobertura temporal e gaps de custo sao reportados;
- `cost_gated_pass` fica verdadeiro somente para pares com evidencia completa e
  dentro dos limites definidos em `docs/historical_dataset.md`;
- `reports/research_sprint_07.md` diferencia claramente candidato estatistico de
  candidato aprovado por custo;
- Sprint 8 continua bloqueado se a evidencia nao existir ou nao passar.

## Testes obrigatorios

- `pytest tests/test_pair_selection.py`
- `pytest tests/test_historical_dataset.py`
- novo teste unitario/integracao para normalizacao de custo historico;
- novo teste fail-closed quando custo historico esta ausente ou incompleto;
- novo teste de no-look-ahead no join de custo com barras/pairs;
- `ruff check src/research tests scripts`

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` com:

- fonte avaliada;
- se a fonte existe ou nao;
- artefatos gerados;
- pares que passaram/reprovaram por custo;
- testes rodados;
- risco residual;
- decisao de gate para Sprint 8.

## Status

IN_PROGRESS

## Progresso

25%

## Prompt de delegacao

Agente: Market Data Agent

Sprint atual: Sprint 7 - Research base: pair selection, Kalman e OU

Task: TASK-007-10 - Produzir evidencia historica de custo de execucao

Contexto obrigatorio:

```text
O Sprint 7 real-dataset gate ja rodou para 2023-06 through 2026-05.
Resultado: 20 simbolos aceitos, 526080 barras 1h normalizadas, 41 pares
estatisticos aceitos e 149 pares rejeitados por pair selection.

O bloqueio restante e cost-gated PASS=false. Nao transforme candidato
estatistico em candidato operacional sem evidencia verificavel de
top-of-book/L2/spread/custo.
```

Arquivos permitidos:

```text
src/research/
tests/
scripts/
reports/
docs/historical_dataset.md
project_control/
tasks/sprint_07/
data/research/
```

Arquivos proibidos:

```text
src/live/
src/execution/
src/ledger/
src/models/
notebooks/
```

Criterio de pronto:

```text
1. Fonte historica de custo documentada e validada, ou impossibilidade
   documentada.
2. Dados de custo, se existirem, normalizados com cobertura/gaps/spread bps.
3. Join com barras/pairs sem look-ahead.
4. Gate recalculado com median/p95/p99 de custo.
5. Evidencia incompleta falha fechada.
6. Relatorio e arquivos de controle atualizados.
```

Testes obrigatorios:

```text
pytest tests/test_pair_selection.py
pytest tests/test_historical_dataset.py
pytest <novo teste de custo historico>
ruff check src/research tests scripts
```

Handoff esperado:

```text
Atualize project_control/HANDOFFS.md e informe se Sprint 8 continua bloqueado
ou se existe um conjunto de pares cost-gated aprovado.
```
