# TASK-008-04 - Implementar backtest cost-aware

## Sprint

Sprint 8 - Backtest walk-forward cost-aware

## Agente

Backtest Agent

## Revisor obrigatorio

Quant Research Agent + QA / Chaos Testing Agent

## Task

Implementar backtest offline que consome splits walk-forward, SignalIntent
offline e custo de execucao real de junho/2023, reportando PnL bruto, custos e
PnL liquido por par.

## Contexto obrigatorio

- project_control/CURRENT_SPRINT.md
- contrato de universo produzido pela TASK-008-01
- splits produzidos pela TASK-008-02
- SignalIntent offline produzido pela TASK-008-03
- data/research/binance_public/cost_pilot/all_candidates_202306_hourly_cost.csv
- data/research/binance_public/cost_pilot/all_candidates_202306_execution_cost_gate.json
- src/execution/slippage_estimator.py apenas como referencia conceitual, sem dependencia obrigatoria

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
- src/execution/ exceto leitura conceitual sem edicao
- src/recovery/
- src/live/
- src/models/
- qualquer endpoint de exchange/trading

## Criterio de pronto

- backtest e offline e deterministico;
- custo e aplicado no timestamp correto, sem olhar futuro;
- PnL bruto, custo, PnL liquido e turnover sao calculados;
- regras de entrada/saida sao documentadas;
- custos ausentes falham fechado;
- pares fora do universo falham fechado;
- nenhum envio/cancelamento de ordem existe no codigo.

## Testes obrigatorios

- teste de PnL liquido com custo conhecido;
- teste fail-closed para custo ausente;
- teste fail-closed para par fora do universo;
- teste que verifica ausencia de imports execution/ledger/recovery;
- `ruff check src tests scripts`.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` com metodologia, outputs, testes e
limitacoes.

## Status

BLOCKED

## Bloqueio

Depende de TASK-008-02 e TASK-008-03.

## Progresso

0%

## Prompt de delegacao

Agente: Backtest Agent

Sprint atual: Sprint 8 - Backtest walk-forward cost-aware

Task: TASK-008-04 - Implementar backtest cost-aware

Contexto obrigatorio:

```text
Backtest offline somente. Use custo real de junho/2023 com escopo claro.
Custo ausente ou par fora do contrato falha fechado.
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
src/recovery/
src/live/
src/models/
src/execution/ para edicao
```

Criterio de pronto:

```text
Backtest deterministico com PnL bruto/liquido, custo, turnover e fail-closed.
```

Testes obrigatorios:

```text
pytest <novos testes de backtest cost-aware>
ruff check src tests scripts
```

Handoff esperado:

```text
Registrar outputs, metodologia, testes e riscos.
```
