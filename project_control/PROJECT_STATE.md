# PROJECT_STATE

Last updated: 2026-07-03

## Atualizacao 2026-07-03: TASK-SIG-004 fechada (checagem intrahora 5m)

A checagem exploratoria unica autorizada pelo ADR-0010 foi executada e
fechada. TASK-SIG-004 reprocessou dados reais 5m checksum-verificados para 8
simbolos / 9 pares / 2025-12 a 2026-05 (419.328 barras normalizadas), sem
novo ciclo de otimizacao e sem redownload do universo completo. Revisao
formal encontrou bug de unidade em barreira vertical sub-hora; corrigido com
`TripleBarrierConfig.bar_duration_hours`, propagacao em
`statistical_backtest.py`, e `max_vertical_bars=2880` no runner 5m para
preservar o cap real de 240h.

Resultado pos-correcao: baseline 5m e tight 5m (`max_half_life_hours=0,375`)
ficaram identicos, com 23.051 trades, gross PF 1,1343 e net PF 0,4223. O
achado motivador de 1h (gross PF 1,1559, net PF 0,8327, n=74) nao se converte
em edge liquido em amostra adequada. Decisao: **nao abrir TASK-SIG-005**;
Signal Iteration 1 permanece ENCERRADA; Sprint 10 permanece NAO ABERTA
automaticamente. Ver `reports/signal_intrahour_sanity_check.md` e
`HANDOFFS.md`.

## Atualizacao 2026-07-03: ADR-0010 -- Signal Iteration 1 OFICIALMENTE ENCERRADA (hipotese rejeitada)

Decisao do usuario, registrada em ADR-0010 (`DECISIONS.md`): encerrar
oficialmente a Signal Iteration 1 como **hipotese rejeitada** (nao "pendente"
ou "em pausa") e seguir para a proxima linha de pesquisa do roadmap. O sinal
de reversao a media Kalman/OU, neste universo (41 pares) e dataset (barras
de 1h, 2023-06 a 2026-05), nao tem edge liquido exploravel via timing de
saida (SIG-002) nem filtro de entrada por half-life (SIG-003). Resultado
negativo convergente, tres vezes testado de forma independente e
pre-registrada -- documentado como achado permanente, nao como trabalho
incompleto.

A checagem exploratoria autorizada (TASK-SIG-004) foi executada e tambem nao
mostrou edge liquido exploravel; portanto esta familia de sinal nao recebe
mais investimento sem uma nova decisao explicita do usuario.

## Atualizacao 2026-07-03: Signal Iteration 1 ENCERRADA (TASK-SIG-003, ultima tentativa)

TASK-SIG-003 testou a ultima pista pendente: filtro ex-ante de ENTRADA via
`max_half_life_hours`. Run 1 (grade [240..12]h) foi achado NAO-VINCULANTE em
revisao formal (Quant Research Agent, P1) -- so 0,064% dos trades excluidos,
distribuicao de half-life ja quase toda <12h. Corrigido com Run 2, novo
pre-registro independente e vinculante (grade [240..0,375]h, 99,88%
excluidos no threshold mais apertado). Decisao final: `STOP_SIGNAL_ITERATION`
-- nenhum threshold cumpre net PF>=1,10 E trade_count>=200 simultaneamente
(0,375h chega perto no gross, PF 1,156, mas falha no net, PF 0,833, com
amostra pequena demais, 74 trades). Observacao descritiva nao-decisoria:
existe concentracao real de edge bruto em reversao muito rapida, mas nao
sobrevive ao custo fixo na amostra disponivel. Revisao formal: Quant
(MUDANCAS SOLICITADAS -> corrigido -> PASSA), QA (PASSA), PM (PASSA). 304
testes, ruff limpo, diff limpo. Ver `reports/signal_entry_filter_experiment.md`.

**Isto encerra a Signal Iteration 1 (SIG-001/002/003).** Evidencia acumulada
das 3 tasks nao sustenta continuar iterando este sinal com os dados/universo
atuais. Sprint 10 permanece NAO ABERTA. Decisao macro pendente do usuario:
pivotar formulacao do sinal, investir num pre-registro dedicado a reversao
muito rapida com amostra maior, ou pausar esta linha de pesquisa. NADA foi
commitado ainda.

## Atualizacao 2026-07-03: Signal Iteration 1 -- TASK-SIG-002 fechado (hipotese rejeitada)

O usuario escolheu explicitamente **iterar o sinal primeiro**, em vez de
avancar para Sprint 10 (Execution Risk Gate) ou testar execucao
passiva/maker. TASK-SIG-001 diagnosticou os 62.878 trades ja calculados no
Sprint 8 canonico: gross PnL agregado negativo antes de custo (-0,7673
bps/trade), `|z| >= 3.0` pior que `2.0-2.5`, e reversoes resolvidas em 2-4h
positivas. TASK-SIG-002 testou causalmente essa ultima pista com
`max_vertical_bars=4`. Resultado: **hipotese rejeitada** -- decisao
`STOP_FAST_REVERSION_PATH`. O baseline reproduz o canonico exatamente
(deltas 0.0) e a variante piora (gross -15.427 bps, net -2.044 bps). Um bug
de "barra confirmadora" foi encontrado durante a implementacao: a janela do
resolvedor precisava de `+2` barras (nao `+1`) para confirmar VERTICAL em vez
de descartar como NO_DATA; antes da correcao a variante parecia melhor
(survivorship de VERTICALs virando NO_DATA), depois corretamente piora.
Revisao formal: Backtest/Quant/QA/PM todos PASSA; P3 compartilhado (regressao
acoplada a mock) resolvido com teste de integracao de resolvedor real.
Verificacao: 292 testes, ruff limpo, diff limpo.

Conclusao acumulada: o sinal, neste universo e features, nao tem edge bruto
exploravel por timing de SAIDA. Decisao pendente do usuario: abrir TASK-SIG-003
como teste ex-ante final do lado da ENTRADA, ou encerrar a iteracao de sinal.
Sprint 10 permanece NAO ABERTA. NADA foi commitado ainda.

## Atualizacao 2026-07-03: Sprint 8 Canonico fechado (retroativo, ADR-0009)

O debito tecnico do ADR-0008 (Sprint 8 canonico do roadmap nunca
implementado) foi fechado: `src/research/triple_barrier.py` +
`src/backtest/statistical_backtest.py` implementados, 4 bugs P1 reais
encontrados e corrigidos em revisao formal (2 rodadas, 6 agentes no total),
e execucao real contra os 41 pares estatisticos do Sprint 7. **Gate NAO
PASSA para 0/41 pares** (melhor caso: ETCUSDT/LTCUSDT, profit factor 0,960
vs. limiar 1,10; portfolio profit factor 0,782). Ver
`reports/backtest_statistical.md` para metodologia completa e a ressalva de
que este resultado (custo fixo estimado) nao e diretamente comparavel ao da
Sprint 9 (custo real tick-a-tick) -- ambos, porem, apontam na mesma direcao.
Este trabalho nao reabriu nem alterou o Sprint 8/9 ja fechados deste
projeto. `RISKS.md` atualizado. Suite completa: 270 testes, ruff limpo.

## Sprint atual

Nenhuma sprint numerada nova aberta. Ultima sprint numerada fechada:
Sprint 9 - Backtest executavel com simulacao de ordens (ver
`project_control/ROADMAP.md`). Workstream pos-Sprint 9 / pre-Sprint 10
(Signal Iteration 1 + TASK-SIG-004) tambem esta fechado.

## Status geral

SPRINT 9 FECHADA. Gate NAO PASSA para "PnL liquido positivo em cenario
conservador": 0 dos 13 pares aprovados no Sprint 8 sao liquido-positivos
com execucao realista (IOC agressivo contra dados tick reais de
junho/2023). Um bug real de PnL (preenchimento parcial zerando PnL de
perna) foi encontrado e corrigido durante o desenvolvimento, confirmado
matematicamente correto por revisao independente do QA Agent. Resultado:
247 sinais, 239 trades, portfolio -$2266.27. Ver
`reports/backtest_executable_v1.md`. Usuario forneceu o roadmap mestre de
28 sprints (`project_control/ROADMAP.md`, ADR-0008); Sprint 8 canonico do
roadmap diverge do "Sprint 8" ja executado neste projeto, registrado como
debito tecnico explicito. TASK-008-08 (limpeza de raw) permanece BLOCKED
aguardando aceite explicito -- porem os dados derivados essenciais ja
foram versionados no git (commit 174d327) para permitir alternar entre
maquinas sem depender dos 17GB de dados brutos.

Escopo do Sprint 10 ainda nao definido -- decisao pendente do usuario,
mas Execution/Risk Agent recomenda testar uma variante de execucao
LIMIT/maker antes de concluir que a estrategia nao tem edge.

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
- Sprint 9 - Backtest executavel com simulacao de ordens (gate NAO PASSA
  para "PnL positivo em cenario conservador": 0/13 pares; ver
  `reports/backtest_executable_v1.md`)

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

## Componentes concluidos (Sprint 9)

- `src/backtest/fill_model.py`: simulacao de fill MARKET/IOC e LIMIT+TTL
  contra top-of-book real (nivel 1), latencia, ACK_UNKNOWN integrado com
  `evaluate_ack_guard` (Sprint 3).
- `src/backtest/execution_simulator.py`: round-trip por par com peso beta,
  deteccao de LEG_FILL_MISMATCH, atraso de saida por ACK_UNKNOWN genuino.
- `src/backtest/replay_engine.py`: replay causal dos mesmos sinais do
  Sprint 8 contra dados tick reais, cache de dias limitado (memory-safe).
- Bug real encontrado e corrigido: preenchimento parcial zerava
  silenciosamente o PnL da perna (herdado de `estimate_slippage` do
  Sprint 6); corrigido e confirmado matematicamente correto por revisao
  independente do QA Agent.
- Segundo problema real corrigido: checksum computado mas nunca verificado
  antes de usar os dados (achado do Market Data Agent).
- `reports/backtest_executable_v1.md`: resultado real -- 0 dos 13 pares
  liquido-positivos com execucao realista, portfolio -$2266.27.
- 34 novos testes automatizados (fill_model, execution_simulator,
  replay_engine, chaos).
- `.gitignore` corrigido para versionar dados derivados essenciais (antes
  `data/` inteiro era ignorado, inclusive os resumos pequenos).

## Componentes em andamento

- Nenhum item tecnico do Sprint 9 em andamento -- sprint fechada.
- Nenhuma tarefa da Signal Iteration 1 em andamento: TASK-SIG-001/002/003 e
  a checagem exploratoria TASK-SIG-004 estao DONE.
- TASK-008-08 (limpeza segura dos 17GB de arquivos raw preservados)
  permanece BLOCKED aguardando aceite explicito do usuario antes de
  qualquer exclusao.
- Sprint 10 permanece nao aberta.

## Objetivo atual

Decisao macro do usuario: escolher entre pivotar para nova formulacao de
sinal, abrir outra hipotese de pesquisa do roadmap, ou abrir Sprint 10
conscientemente apesar do gate economico negativo ja documentado. Nenhuma
task SIG deve ser aberta automaticamente.

## Proximo gate

Sprint 8 (nao-canonico) PASSA (escopado) -- ja fechado, ver historico acima.
Debito tecnico do Sprint 8 canonico do roadmap (triple barrier, Sharpe/
Sortino/profit factor) registrado em RISKS.md, nao bloqueia sprints futuros.

Sprint 9 FECHADA. Criterios do ROADMAP.md:

- ordem nao tem fill garantido: demonstrado (fills parciais reais, 75
  entradas parciais, 76 saidas parciais);
- partial fill gera exposicao residual: demonstrado (11.470,92 unidades
  nao fechadas, 70/239 trades com LEG_FILL_MISMATCH);
- ACK_UNKNOWN forca reconciliacao simulada: demonstrado (integrado com
  `evaluate_ack_guard` real);
- PnL liquido reportado honestamente: demonstrado -- e negativo (0/13
  pares positivos, portfolio -$2266.27);
- causalidade confirmada: demonstrado e testado;
- Backtest/QA/Market Data Agent confirmam PASSA (apos correcoes);
  Execution/Risk Agent (consultivo) recomenda testar variante LIMIT/maker
  antes de qualquer decisao definitiva sobre a estrategia.

Gate para Sprint 10 (Execution Risk Gate, se for a proxima escolha): NAO
PASSA para "PnL liquido positivo em cenario conservador" -- decisao de
como prosseguir e do usuario.

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
- Nenhum gate SIG ativo. Signal Iteration 1 e TASK-SIG-004 estao fechadas;
  Sprint 10 so abre por decisao explicita de escopo.

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
- Sprint 9 usa execucao MARKET_IOC agressiva sempre (nunca LIMIT/maker) --
  e o cenario de custo mais caro possivel; 0/13 pares positivos pode
  refletir execucao cara demais, nao necessariamente ausencia de edge.
- Exposicao residual nao fechada (naked leg) nao e marcada a mercado no
  PnL reportado do Sprint 9 -- subestima risco real e exige Hedge
  Engine/Barrier Manager/Emergency Exit (Sprints 21-22 do ROADMAP.md)
  antes de qualquer promocao a capital real.
- Latencia (250ms) e taxa de ACK_UNKNOWN (2%) no Sprint 9 sao suposicoes
  nao calibradas por dados reais de producao.

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
