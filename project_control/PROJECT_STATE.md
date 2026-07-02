# PROJECT_STATE

Last updated: 2026-07-02

## Sprint atual

Sprint 9 - Backtest executavel com simulacao de ordens (ver `project_control/ROADMAP.md`)

## Status geral

ABERTA / EM EXECUCAO. Usuario forneceu o roadmap mestre de 28 sprints
(`project_control/ROADMAP.md`, ADR-0008). Sprint 8 canonico do roadmap
("Triple Barrier + backtest estatistico") diverge do "Sprint 8" ja
executado neste projeto ("Backtest walk-forward cost-aware", gate PASSA
escopado a 13 pares); a divergencia foi aceita e registrada como debito
tecnico explicito (nao revertida). Por instrucao explicita do usuario, o
projeto avanca direto para a Sprint 9 do roadmap, reusando os 13 pares e os
17GB de dados brutos ja verificados. TASK-008-08 (limpeza de raw) permanece
BLOCKED aguardando aceite explicito.

## Ultimos sprints concluidos

- Sprint 1 - Especificacao operacional
- Sprint 2 - Ledger base com SQLite WAL
- Sprint 3 - Idempotencia, clientOrderId e reconciliacao cumulativa
- Sprint 4 - Recovery boot e modo safe
- Sprint 5 - Market Data Plane: book local
- Sprint 6 - Features de execucao e slippage
- Sprint 7 - Research base: pair selection, Kalman e OU
- Sprint 8 (nao-canonico) - Backtest walk-forward cost-aware (gate PASSA,
  escopado a 13 pares; diverge do Sprint 8 do ROADMAP.md, ver ADR-0008)

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
- Expanded real execution-cost pilot for all 41 Sprint 7 candidate pairs
  inside June 2023: 450 daily bookTicker archives checksum-verified, 31 pairs
  cost-gated PASS, 10 ADAUSDT pairs correctly rejected

## Componentes concluidos (Sprint 8)

- Contrato de universo Sprint 8 (`project_control/SPRINT8_UNIVERSE.json`),
  carregavel e fail-closed (31 aprovados, 10 bloqueados por ADAUSDT).
- Splits walk-forward causais (`build_walk_forward_splits`).
- Geracao de SignalIntent offline causal (Kalman sequencial + z-score
  rolling + gate OU/half-life recalculado em janela causal movel, apos
  correcao de um look-ahead P1 encontrado em revisao).
- Backtest cost-aware com peso beta e custo round-trip (entrada + saida),
  apos correcao de dois P1 encontrados em revisao (peso beta ausente, custo
  de saida nao modelado).
- `reports/sprint_08_backtest.md`: 31 pares avaliados, 13 aprovados
  (net PnL positivo real), 18 rejeitados, portfolio agregado negativo
  (rotulado explicitamente para nao ser confundido com aprovacao).
- 20 novos testes automatizados (universo, walk-forward, sinal/backtest,
  runner, incluindo teste dedicado de causalidade).

## Componentes em andamento

- Sprint 9 (`project_control/ROADMAP.md`): fill_model.py,
  execution_simulator.py, replay_engine.py em implementacao. TASK-009-01
  esta READY.
- TASK-008-08 (limpeza segura dos 17GB de arquivos raw preservados)
  permanece BLOCKED aguardando aceite explicito do usuario antes de
  qualquer exclusao. Esses mesmos arquivos sao o insumo real da Sprint 9.

## Objetivo atual

Sprint 9: substituir o fill idealizado do Sprint 8 (mark-to-market 1 barra
depois do sinal) por simulacao realista de execucao contra cotacoes reais
tick-a-tick de junho/2023: partial fill, IOC, maker com TTL, latencia e
ACK_UNKNOWN, medindo se o PnL liquido dos 13 pares aprovados sobrevive a
essas condicoes.

## Proximo gate

Sprint 8 (nao-canonico) PASSA (escopado) -- ja fechado, ver historico acima.
Debito tecnico do Sprint 8 canonico do roadmap (triple barrier, Sharpe/
Sortino/profit factor) registrado em RISKS.md, nao bloqueia Sprint 9.

Sprint 9 so passa se (ver `ROADMAP.md`):

- ordem nao tem fill garantido (demonstrado, nao assumido);
- partial fill gera exposicao residual (LEG_FILL_MISMATCH detectado);
- ACK_UNKNOWN forca reconciliacao simulada;
- PnL liquido reportado honestamente (positivo ou negativo);
- causalidade confirmada (nenhuma cotacao futura usada);
- Backtest/QA/Execution-Risk Agent confirmam PASSA.

## Bloqueadores atuais

- Sprint 7 statistical real-dataset gate has been executed for the documented
  2023-06 through 2026-05 Binance USD-M window. It produced 20 accepted
  symbols, 526080 normalized 1h bars, 41 statistical candidate pairs, 149
  rejected pairs, and 41 statistical-only pair accepts after stationarity,
  Kalman, OU, and z-score checks.
- TASK-007-09 passed Market Data Agent + QA Agent review and is DONE.
- TASK-007-10 confirmed Binance Public Data bookTicker (top-of-book/L2) has no
  coverage at all for 25 of the 36 required months (2024-05 through 2026-05),
  for any symbol. This is a permanent data-availability limit of the source,
  independently verified against the live endpoint and re-verified by QA
  Agent.
- Per ADR-0007, real memory-safe daily bookTicker pilots were run inside June
  2023. The expanded 2026-07-02 run covered all 15 symbols appearing in the
  41 Sprint 7 candidate pairs, preserving 450 checksum-verified daily archives
  (17.98GB compressed) and producing a deduplicated 10800-row hourly cost
  file.
- Sprint 8 may now open, SCOPED to the 31 candidate pairs that passed the
  June-2023 cost gate. The 10 failed pairs all contain ADAUSDT and remain
  blocked by ADAUSDT `WIDE_MEDIAN_SPREAD` (3.52bps > 3.0bps). Any month
  outside June 2023 remains statistical-only until the same
  real-download-and-verify process is repeated, an alternative verified source
  is found for 2024-05 through 2026-05, or the live Market Data Plane
  (Sprint 5/6 BookFeatures) supplies forward evidence once paper/live trading
  exists.

## Gates pendentes

- Daily realized loss and drawdown threshold gaps remain fail-closed
  live-readiness blockers.
- TASK-008-08 (limpeza segura dos arquivos raw) permanece BLOCKED aguardando
  aceite explicito do usuario.
- Escopo e tarefas do Sprint 9 ainda nao foram definidos; requer decisao do
  usuario antes de abrir formalmente.

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
- Backtest pode parecer melhor do que execucao real se custo de junho/2023 for
  extrapolado indevidamente para outros regimes.
- Backtest usa horizonte fixo de 1h sem stop-loss/take-profit/saida por
  reversao de z-score; execucao real provavelmente sairia em momento
  diferente.
- Custo usa apenas mediana horaria do spread top-of-book, nao p95/p99 nem
  profundidade/impacto — pode subestimar custo real em cenarios de spread
  largo ou notional maior.
- max_drawdown_bps e por-par, nao existe metrica de drawdown de portfolio
  combinado e alinhado no tempo.

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
