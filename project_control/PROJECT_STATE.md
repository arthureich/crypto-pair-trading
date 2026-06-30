# PROJECT_STATE

Last updated: 2026-06-30

## Sprint atual

Sprint 7 - Research base: pair selection, Kalman e OU

## Status geral

BLOQUEADO PARA SPRINT 8

## Ultimos sprints concluidos

- Sprint 1 - Especificacao operacional
- Sprint 2 - Ledger base com SQLite WAL
- Sprint 3 - Idempotencia, clientOrderId e reconciliacao cumulativa
- Sprint 4 - Recovery boot e modo safe
- Sprint 5 - Market Data Plane: book local
- Sprint 6 - Features de execucao e slippage

## Componentes concluidos

- EventStore base
- SQLite WAL
- clientOrderId deterministico
- cumulative fill reconciliation
- ACK_UNKNOWN sem retry cego
- recovery_boot
- SAFE_MODE
- LocalOrderBook
- BookBuilder
- snapshot/diff L2 local
- gap detection
- stale book detection
- best bid / best ask confiaveis
- book_age_ms
- book.in_sync
- feature cache
- spread_bps
- depth_5bps
- depth_10bps
- imbalance
- slippage estimator
- pair selection research helpers
- stationarity research helpers
- Kalman beta_t / alpha_t / spread_t
- Ornstein-Uhlenbeck estimator
- no-look-ahead research z-score helpers
- exploratory research notebooks
- Sprint 7 technical research report

## Componentes em andamento

- Historical dataset execution for Sprint 7 gate

## Objetivo atual

Validar o sinal estatistico bruto por meio de selecao de pares, Kalman Filter,
Ornstein-Uhlenbeck, estacionariedade, half-life e z-score.

## Proximo gate

Sprint 7 so passa se:

- pares candidatos sao ranqueados;
- spread e calculado com beta dinamico;
- OU gera half-life e z-score;
- pares instaveis sao descartados;
- nao ha look-ahead na preparacao dos dados;
- os resultados sao documentados.

## Bloqueadores atuais

- Sprint 7 research gate is not satisfied for Sprint 8 because the documented
  36 complete-month Binance USD-M dataset has not been downloaded, checksumed,
  normalized, or run through the research pipeline.

## Gates pendentes

- Daily realized loss and drawdown threshold gaps remain fail-closed
  live-readiness blockers.
- Sprint 7 real-dataset research gate.

## Riscos atuais

- Research full-sample exploratorio pode ser confundido com sinal disponivel em
  tempo real se o relatorio nao separar claramente analise exploratoria de
  features rolling/no-look-ahead.
- Pares candidatos podem parecer estacionarios em amostra curta e quebrar em
  mudanca de regime.
- Funding, liquidez e spread medio podem eliminar pares estatisticamente bons.
- Kalman beta_t pode ficar instavel se parametros de ruido forem mal definidos.
- OU half-life muito curto pode ser ruido; half-life muito longo pode ser
  inviavel operacionalmente.

## Fora de escopo agora

- XGBoost
- P_fill/P_profit
- paper trading
- live trading
- alavancagem
- multi-exchange
- Execution Risk Gate completo
- Real live trading
- Live order router implementation
- Exchange trading endpoint integration
- Kelly sizing
