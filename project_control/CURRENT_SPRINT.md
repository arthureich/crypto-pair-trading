# CURRENT_SPRINT

## Sprint

Sprint 7 - Research base: pair selection, Kalman e OU

## Objetivo

Construir a base de pesquisa estatistica da estrategia: selecionar pares
candidatos, calcular spread com hedge ratio dinamico via Kalman Filter, estimar
processo Ornstein-Uhlenbeck, calcular half-life, z-score e descartar pares
instaveis.

## Escopo permitido

- coleta/normalizacao de OHLCV historico
- coleta/normalizacao de mark price
- coleta/normalizacao de funding
- pair selection inicial
- filtros de liquidez
- filtros de spread medio
- correlacao rolling
- ADF
- KPSS
- half-life
- beta stability
- Kalman beta_t
- Kalman alpha_t
- spread_t
- OU theta
- OU mu
- OU sigma
- z-score
- relatorios de pesquisa

## Fora de escopo

- XGBoost
- calibracao de modelo
- P_fill
- P_profit_given_fill
- live trading
- order router
- Risk Gate completo
- paper trading
- alavancagem
- multi-exchange

## Entregaveis obrigatorios

- `src/research/pair_selection.py`
- `src/research/kalman.py`
- `src/research/ou.py`
- `src/research/stationarity.py`
- `notebooks/01_pair_selection.ipynb`
- `notebooks/02_kalman_ou.ipynb`
- `reports/research_sprint_07.md`
- `tests/test_pair_selection.py`
- `tests/test_kalman.py`
- `tests/test_ou.py`
- `tests/test_stationarity.py`

## Criterio de pronto

- pares candidatos sao ranqueados
- spread e calculado com beta dinamico
- OU gera half-life e z-score
- pares instaveis sao descartados
- testes passam
- relatorio explica quais pares continuam e quais foram rejeitados

## Testes obrigatorios

- `pytest tests/test_pair_selection.py`
- `pytest tests/test_stationarity.py`
- `pytest tests/test_kalman.py`
- `pytest tests/test_ou.py`

## Gate para avancar ao Sprint 8

So avancar se houver pelo menos um conjunto de pares candidatos com:

- liquidez minima aceitavel
- spread medio aceitavel
- estacionariedade razoavel
- half-life operacionalmente viavel
- beta_t nao explosivo
- documentacao clara dos resultados

## Gate final do Sprint 7

- dataset historico minimo definido
- pares candidatos ranqueados
- filtros de liquidez aplicados
- correlacao rolling calculada
- ADF/KPSS aplicados
- Kalman beta_t implementado
- spread_t calculado
- OU implementado
- half-life calculado
- z-score calculado
- pares instaveis descartados
- testes passam
- `reports/research_sprint_07.md` escrito
- `project_control/HANDOFFS.md` atualizado
- `project_control/PROJECT_STATE.md` atualizado
- `project_control/TASK_BOARD.md` atualizado

## Gate real-dataset

Real 2023-06 through 2026-05 Binance USD-M run:

- 20 seed symbols accepted
- 526080 normalized 1h bars
- 41 statistical candidate pairs
- 149 rejected pairs
- 41 pairs evaluated by stationarity, Kalman, OU, and z-score gate
- 41 statistical-only accepts
- cost-gated PASS: false (definitive, not pending)

TASK-007-09 received Market Data Agent + QA Agent review: PASSA (no P1
findings). TASK-007-09 is DONE.

TASK-007-10 executed a real source review against the Binance Public Data
bookTicker archive (monthly and daily, both S3 prefixes, all 20 accepted
symbols) for the full 36-month window. Result: `SOURCE_INCOMPLETE_FAIL_CLOSED`.
Verified top-of-book/L2 coverage exists for only 11 of the 36 required months
(2023-06 through approximately 2024-04); no symbol reaches complete coverage,
and Binance Public Data does not publish bookTicker archives past that point
for any of the 20 symbols. This was independently confirmed against the live
S3 endpoint (not a pagination artifact) and re-verified by QA Agent. Because
the source is incomplete, `cost_gated_pass=false` for all 41 candidate pairs,
unconditionally. TASK-007-10 is DONE with this definitive negative finding.

Sprint 8 remains blocked. This is no longer a pending-execution blocker: it is
a data-availability limitation of the current source. Advancing to Sprint 8
now requires a PM/stakeholder decision: (a) find and verify an alternative
top-of-book/L2 source, (b) shrink the research window to the ~11 months with
verified coverage and re-run the statistical gate on that sub-window, (c)
redefine the cost-gated PASS policy via ADR (e.g. accept forward-collected
execution-cost evidence going forward instead of retroactive), or (d) keep
Sprint 8 blocked indefinitely until one of the above is resolved. See
`BLOCKER-2026-06-30-S7-REAL-DATASET-GATE`.

## Agentes envolvidos

- Quant Research Agent
- Backtest Agent
- Market Data Agent
- QA Agent
- Documentation Agent
- PM Agent

## Revisores obrigatorios

- Market Data Agent for dataset/source/liquidity assumptions.
- Backtest Agent for no-look-ahead and research/backtest boundaries.
- QA Agent for synthetic tests, no mutable global DataFrame state, and
  fail-closed rejection cases.
- Documentation Agent for notebooks and report clarity.
- PM Agent for gate and sprint state.

## Sprint tasks

| ID | Tarefa | Dono | Revisor | Status | Progresso |
|---|---|---|---|---|---:|
| TASK-007-01 | Definir dataset historico minimo | Quant Research Agent | Market Data Agent | DONE | 100% |
| TASK-007-02 | Implementar pair_selection.py | Quant Research Agent | Backtest Agent | DONE | 100% |
| TASK-007-03 | Implementar stationarity.py | Quant Research Agent | QA Agent | DONE | 100% |
| TASK-007-04 | Implementar Kalman Filter | Quant Research Agent | Backtest Agent + QA Agent | DONE | 100% |
| TASK-007-05 | Implementar OU estimator | Quant Research Agent | Backtest Agent + QA Agent | DONE | 100% |
| TASK-007-06 | Criar notebooks exploratorios | Quant Research Agent | Documentation Agent | DONE | 100% |
| TASK-007-07 | Criar testes de research base | QA Agent | Quant Research Agent | DONE | 100% |
| TASK-007-08 | Gerar relatorio research_sprint_07.md | Documentation Agent | PM Agent | DONE | 100% |
| TASK-007-09 | Implementar loader/normalizer historico Binance | PM Agent | Market Data Agent + QA Agent | DONE | 100% |
| TASK-007-10 | Produzir evidencia historica de custo de execucao | Market Data Agent | QA Agent + PM Agent | DONE | 100% |
