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
| TASK-007-09 | Implementar loader/normalizer historico Binance | PM Agent | Market Data Agent + QA Agent | IN_PROGRESS | 25% |
