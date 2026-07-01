# PROJECT_STATE

Last updated: 2026-07-01

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

## Componentes concluidos (Sprint 7, adicional)

- Historical Binance loader/normalizer (TASK-007-09), reviewed and passed by
  Market Data Agent and QA Agent
- Historical top-of-book/L2 execution-cost source review (TASK-007-10):
  definitive finding that Binance Public Data bookTicker coverage is
  incomplete for the required window

## Componentes em andamento

- Nenhum item tecnico de Sprint 7 em andamento. Sprint 8 start depende de
  decisao de politica sobre a fonte de custo de execucao (ver Bloqueadores
  atuais).

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

- Sprint 7 statistical real-dataset gate has been executed for the documented
  2023-06 through 2026-05 Binance USD-M window. It produced 20 accepted
  symbols, 526080 normalized 1h bars, 41 statistical candidate pairs, 149
  rejected pairs, and 41 statistical-only pair accepts after stationarity,
  Kalman, OU, and z-score checks.
- TASK-007-09 passed Market Data Agent + QA Agent review and is DONE.
- TASK-007-10 is DONE with a definitive negative finding: Binance Public Data
  bookTicker (top-of-book/L2) coverage exists for only 11 of the required 36
  months, for every one of the 20 accepted symbols. This was independently
  verified against the live source and re-verified by QA Agent; it is a real
  data-availability limit, not a bug.
- Sprint 8 remains blocked. The blocker is no longer "evidence not yet
  produced" — it is "verified evidence does not exist for this window on this
  source." Starting Sprint 8 now requires an explicit PM/stakeholder decision
  among: find an alternative verified cost source, shrink the research window
  to the covered sub-period, redefine cost-gated PASS policy via ADR, or keep
  Sprint 8 blocked indefinitely.

## Gates pendentes

- Daily realized loss and drawdown threshold gaps remain fail-closed
  live-readiness blockers.
- Sprint 7 cost-gated real-dataset research gate.

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
