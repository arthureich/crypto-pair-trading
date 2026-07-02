# CURRENT_SPRINT

Last updated: 2026-07-02

## Sprint

Sprint 9 - Backtest executavel com simulacao de ordens (`project_control/ROADMAP.md`)

## Status

ABERTA / EM EXECUCAO

## Nota de reconciliacao

O roadmap mestre (`project_control/ROADMAP.md`) foi fornecido pelo usuario em
2026-07-02. Comparado a ele, o "Sprint 8" ja fechado neste projeto
("Backtest walk-forward cost-aware") diverge do Sprint 8 canonico do roadmap
("Triple Barrier direcional e backtest estatistico"). Essa divergencia foi
aceita e registrada como debito tecnico explicito, nao revertida --
ver `DECISIONS.md` ADR-0008 e `RISKS.md`. A partir da Sprint 9, a numeracao
segue exatamente `ROADMAP.md`.

## Objetivo

Transformar o backtest em uma simulacao realista de execucao: nenhuma ordem
tem fill garantido, partial fill gera exposicao residual, ACK_UNKNOWN forca
reconciliacao simulada, latencia e simulada, e o PnL liquido e medido contra
essas condicoes realistas em vez do preenchimento idealizado assumido no
Sprint 8.

## Escopo permitido

- implementar `src/backtest/fill_model.py`: simulacao de fill contra
  top-of-book real (bid/ask + qty de nivel 1), MARKET/IOC, LIMIT com TTL,
  latencia, ACK_UNKNOWN;
- implementar `src/backtest/execution_simulator.py`: round-trip de trade
  perna-a-perna usando fill_model, com peso beta e deteccao de
  LEG_FILL_MISMATCH;
- implementar `src/backtest/replay_engine.py`: replay causal sobre os
  sinais ja gerados no Sprint 8, usando os dados brutos ja baixados e
  verificados (17GB preservados em
  `data/research/binance_public/cost_pilot/raw/`);
- rodar o replay real sobre os 13 pares backtest-approved do Sprint 8;
- gerar `reports/backtest_executable_v1.md`;
- testes de causalidade, fail-closed e chaos.

## Fora de escopo

- baixar novos dados (usar apenas o que ja foi verificado e preservado);
- Triple Barrier direcional / Sharpe / Sortino / profit factor (debito
  tecnico do Sprint 8 canonico, nao deste sprint -- ver ADR-0008);
- Execution Risk Gate completo (Sprint 10);
- paper trading, live trading;
- alteracoes em `src/ledger/`, `src/execution/client_order_id.py`,
  `src/live/`, `src/recovery/`, `src/risk/execution_risk_gate.py`;
- XGBoost, P_fill, P_profit_given_fill;
- alavancagem, multi-exchange.

## Invariantes obrigatorios

- Sinal continua sendo gerado pelo mesmo caminho causal ja revisado no
  Sprint 8 (`generate_pair_signal_intents`) -- Sprint 9 nao muda geracao de
  sinal, so realismo de execucao.
- Replay nunca consome uma cotacao com `event_time` anterior ao momento da
  decisao.
- Nenhum modulo deste sprint importa `src.ledger`, `src.live`,
  `src.recovery`, ou `src.risk.execution_risk_gate`.
- Reusar `estimate_slippage` de `src/execution/slippage_estimator.py` para
  consumo de book -- nao duplicar essa logica.
- Memoria: nunca carregar mais de um pequeno numero fixo de arquivos diarios
  descomprimidos simultaneamente (o Sprint 8 teve um OOM kill por violar
  isso).
- Resultados devem separar claramente: preenchimento completo, parcial,
  expirado e sem cotacao -- nunca assumir fill perfeito.

## Universo de entrada

Os 13 pares backtest-approved do Sprint 8 (`project_control/SPRINT8_UNIVERSE.json`
+ `reports/sprint_08_backtest.md`):

```text
ARBUSDT/OPUSDT
ARBUSDT/ETHUSDT
ETCUSDT/ETHUSDT
ARBUSDT/DOTUSDT
ARBUSDT/LINKUSDT
ARBUSDT/AVAXUSDT
AVAXUSDT/SOLUSDT
DOGEUSDT/ETCUSDT
AVAXUSDT/ETHUSDT
DOGEUSDT/ETHUSDT
ETHUSDT/OPUSDT
ETCUSDT/LTCUSDT
ETHUSDT/UNIUSDT
```

## Artefatos de entrada

```text
data/research/binance_public/cost_pilot/raw/data/futures/um/daily/bookTicker/ (17GB, checksum-verificado)
data/research/binance_public/cost_pilot/sprint8_backtest_pair_results.csv
data/research/binance_public/cost_pilot/sprint8_backtest_results.json
project_control/SPRINT8_UNIVERSE.json
src/research/sprint8.py
src/execution/slippage_estimator.py
reports/sprint_08_backtest.md
```

## Entregaveis obrigatorios

```text
src/backtest/fill_model.py
src/backtest/execution_simulator.py
src/backtest/replay_engine.py
scripts/run_sprint9_replay.py
reports/backtest_executable_v1.md
```

## Criterio de pronto (do ROADMAP.md)

```text
ordem nao tem fill garantido
partial fill gera exposicao residual
ACK_UNKNOWN forca reconciliacao simulada
PnL liquido ainda e positivo em cenario conservador
stress de fee e slippage nao destroi completamente o edge
```

## Testes obrigatorios

```text
pytest tests/test_fill_model.py
pytest tests/test_execution_simulator.py
pytest tests/test_replay_engine.py
pytest tests/test_sprint9_chaos.py
pytest tests -q (suite completa, sem regressao)
ruff check src tests scripts
```

## Agentes envolvidos

- PM Agent
- Backtest Agent
- Quant Research Agent
- Market Data Agent
- Execution / Risk Agent (consultivo, realismo de ordem)
- QA / Chaos Testing Agent
- Documentation Agent

## Revisores obrigatorios

- Backtest Agent para metodologia de fill e replay.
- QA / Chaos Testing Agent para causalidade e fail-closed.
- Market Data Agent para uso correto dos dados de book reais.
- Execution / Risk Agent para realismo de IOC/latencia/ACK_UNKNOWN
  (perspectiva de quem vai construir o Execution Risk Gate no Sprint 10).
- PM Agent para gate e escopo.

## Sprint tasks

| ID | Tarefa | Dono | Revisor | Status | Progresso |
|---|---|---|---|---|---:|
| TASK-009-01 | Implementar fill_model.py | Backtest Agent | QA Agent + Execution/Risk Agent | READY | 0% |
| TASK-009-02 | Implementar execution_simulator.py | Backtest Agent | Quant Research Agent + QA Agent | BLOCKED | 0% |
| TASK-009-03 | Implementar replay_engine.py | Backtest Agent | QA Agent + Market Data Agent | BLOCKED | 0% |
| TASK-009-04 | Testes de Sprint 9 (chaos, causalidade) | QA Agent | Backtest Agent + PM Agent | BLOCKED | 0% |
| TASK-009-05 | Rodar replay real nos 13 pares | Backtest Agent | PM Agent + Quant Research Agent | BLOCKED | 0% |
| TASK-009-06 | Relatorio e gate Sprint 9 | Documentation Agent | PM Agent + Backtest Agent | BLOCKED | 0% |

## Gate para avancar ao Sprint 10 (Execution Risk Gate)

Sprint 10 so pode abrir se:

```text
fill_model, execution_simulator e replay_engine implementados e testados;
replay real rodado nos 13 pares com dados verificados (nao mock);
PnL liquido realista reportado (positivo ou negativo, sem mascarar);
causalidade confirmada (nenhuma cotacao futura usada);
Backtest/QA/Execution-Risk Agent registram PASSA;
reports/backtest_executable_v1.md escrito.
```
