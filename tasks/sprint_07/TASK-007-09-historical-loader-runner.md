# TASK-007-09 - Implementar loader/normalizer historico Binance

## Sprint

Sprint 7 - Research base: pair selection, Kalman e OU

## Dono

PM Agent fallback for Quant Research Agent

## Revisor obrigatorio

Market Data Agent + QA Agent

## Contexto obrigatorio

Antes de comecar, leia:

- project_control/PROJECT_STATE.md
- project_control/CURRENT_SPRINT.md
- project_control/BLOCKERS.md
- docs/historical_dataset.md
- src/research/pair_selection.py
- tasks/sprint_07/TASK-007-09-historical-loader-runner.md

## Objetivo

Implementar o caminho executavel para baixar, verificar checksum, normalizar e
rodar a selecao inicial de pares sobre arquivos historicos publicos da Binance
USD-M Futures.

## Escopo

- montar URLs mensais do Binance Public Data
- baixar arquivos ZIP e `.CHECKSUM`, quando solicitado
- verificar SHA256
- ler OHLCV, mark price, index price, premium index e funding
- normalizar para o formato esperado por `select_pairs`
- preservar regras de limpeza e no-forward-fill
- fornecer runner de pesquisa para execucao local do dataset
- adicionar testes de normalizacao, checksum e gaps

## Fora de escopo

- top-of-book/L2 historico completo
- bookTicker como fonte obrigatoria
- backtest completo
- paper trading
- live trading
- order router
- XGBoost
- P_fill/P_profit

## Arquivos permitidos

- src/research/
- tests/
- scripts/
- reports/
- project_control/
- tasks/sprint_07/

## Arquivos proibidos

- src/live/
- src/execution/
- src/ledger/
- src/models/

## Criterio de pronto

- URLs e caminhos mensais sao deterministas
- checksums sao verificados antes da normalizacao
- klines e sidecars sao normalizados com schema estavel
- funding e unido por as-of sem futuro
- gaps nao recebem forward-fill de retorno/preco
- saida alimenta `select_pairs`
- testes passam

## Testes obrigatorios

- `pytest tests/test_historical_dataset.py`
- `pytest tests/test_pair_selection.py`

## Handoff esperado

Atualizar project_control/HANDOFFS.md com:

- o que foi feito
- arquivos alterados
- testes rodados
- execucao real/smoke, se houver
- pendencias
- riscos

## Status

IN_REVIEW

## Progresso

95%

## Nota de status

Loader, normalizer, checksum verification, local runner smoke, and tests are
implemented. The real 2023-06 through 2026-05 Binance USD-M dataset was
downloaded, checksumed, normalized, and run through the Sprint 7 statistical
research gate.

Current real run artifacts:

```text
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_summary.json
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.json
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.csv
```

Market Data Agent and QA Agent review are still required before DONE.
Cost-gated Sprint 7 PASS remains false because verified historical
top-of-book/L2 execution-cost evidence is unavailable.
