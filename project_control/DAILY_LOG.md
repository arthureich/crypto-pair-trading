# Daily Log

## 2026-07-18 (DEPLOY-001 Fase 7 + FECHAMENTO -- monitor forward; PROGRAMA COMPLETO 7/7; STOP POLICY)

```text
- FASE 7 (monitoramento forward). src/research/forward_monitor.py: horizontes de
  leitura (1mo diagnostico / 3mo preliminar / 6mo inicial / 12mo primeiro
  relevante / 18-24mo mais confiavel -- guardas contra concluir cedo), metricas
  por stream (Sharpe/Sortino/maxDD composto/DD duration/underwater/PF/hit-rate),
  criterios de ALERTA (shortfall>budget, custo>breakeven, DD alem do historico,
  queda de hit-rate, concentracao de PnL, falhas de dados, config-hash !=
  congelado, exposicao != config). Alertas SO alertam, nunca modificam. + 8 testes.
- scripts/run_forward_monitor.py le o ledger imutavel: 5 eventos OOS =
  operational_diagnostic (NAO veredito), nenhum alerta, config-hash bate.
  reports/forward_monitor.md.
- PROGRAMA DEPLOY-001 COMPLETO (7/7). reports/deploy_program_status.md responde
  as 10 perguntas de conclusao. Bottom line honesto: TSM e um edge REAL mas
  MODESTO -- Sharpe teorico ~0.97 sobrevive execucao (tamanho pequeno) e selecao
  por multiplas tentativas (DSR 0.80), MAS peso estatistico efetivo fino (~1
  universo independente, CI de stream unico toca zero, PnL episodico) e drawdowns
  profundos/longos (31-58% compostos, ate ~14mo). Capacidade prudente ~$10M nos
  majors. O veredito real agora depende so do forward.
- STOP POLICY em vigor: familia TSM CONGELADA; so o forward continua; sem novas
  variantes na mesma janela; nova ideia exige nova hipotese + pre-registro +
  dados independentes.
- Verificacao: 639 testes (8 novos), ruff limpo. Nenhum parametro economico tocado.
```

## 2026-07-18 (DEPLOY-001 Fase 6 -- haircut por multiplas tentativas: edge sobrevive a selecao MAS evidencia efetiva e MAIS FINA)

```text
- FASE 6 (ajuste estatistico por multiplas tentativas). src/research/
  multiple_testing.py (PSR, expected-max-Sharpe, DSR, effective-trials; stdlib
  NormalDist) + 9 testes. scripts/run_multiple_testing_haircut.py + inventario
  artifacts/tsm/attempt_ledger.json (24 hipoteses de estrategia).
- Resultado MISTO e honesto:
  - REASSURING: PSR vs 0 = 0.957; DSR (deflacionado por 24 hipoteses) = 0.80 ->
    o lead NAO e plausivelmente a sorte entre muitas tentativas (e as tentativas
    sao quase todas a mesma familia TSM -> contagem naive superestima o risco).
  - SOBRIO 1: CI de Sharpe por BLOCK-BOOTSTRAP (respeita autocorrelacao) =
    [-0.05, 1.94] -> INCLUI zero. No stream unico de 3 anos o Sharpe NAO e
    conclusivamente > 0; o PSR iid era otimista.
  - SOBRIO 2: os 7 universos cripto sao 0.83-correlacionados -> ~1.17 EFETIVOS
    independentes. O "positivo em 7/7" (TSM-010/013) vale ~1 aposta independente,
    NAO 7 -- o claim de breadth estava materialmente superestimado. CORRECAO.
  - SOBRIO 3: PnL CONCENTRADO -- melhor mes 38%, top-3 meses 71% do total. Edge
    episodico, nao estavel.
  - PBO/CSCV: NAO estimavel na nossa estrutura (poucas variantes pre-registradas,
    nao um grid combinatorio) -> reportado como tal, nao fabricado.
- VEREDITO honesto: edge REAL mas MODESTO e descontado-por-dependencia; muito
  mais fino que o headline "7/7, CI exclui zero". O forward (Fase 7) e o juiz.
- Verificacao: 631 testes (9 novos), ruff limpo. Nenhum parametro economico tocado.
```

## 2026-07-18 (DEPLOY-001 Fase 5 -- controles de producao: limites, failure modes, kill switches, idempotencia)

```text
- FASE 5 (controles de producao): src/research/production_controls.py.
  Adicionados por justificativa OPERACIONAL, nunca por melhorar backtest.
  - Limites pre-trade (rejeitam a ordem, sistema segue): max gross 1.0 / net 0.30
    / leverage 2.0 / por-simbolo 0.20 / participacao 10% ADV / liquidez-min $1M /
    turnover diario 2.0.
  - Failure modes (flags): stale_data, non_positive_price, incomplete_bar,
    missing_funding, price_deviation (>20% vs ref), abnormal_spread (>1%). Tambem
    tratados operacionalmente: API down, conexao, ativo suspenso/delistado,
    mudanca de spec, symbol-mapping, fill parcial, clock skew, restart no meio.
  - Kill switches (HALT sistema): config_hash != congelado, margem<buffer 30%,
    divergencia de estado local, dado invalido critico. Acao segura =
    HALT_NO_NEW_EXPOSURE -- NAO auto-liquida (auto-liquidacao exige politica
    explicita + humano).
  - Idempotencia: ordens chaveadas pelo decision_id deterministico (Fase 2) ->
    reprocessar apos restart nao duplica ordem/PnL.
- reports/production_risk_policy.md documenta a politica (3 camadas + safe action).
- NAO e loop de trading ao vivo (fora de escopo, nao autorizado; sem dinheiro real).
- Verificacao: 622 testes (10 novos de failure-mode/controles), ruff limpo.
  Nenhum parametro economico tocado.
```

## 2026-07-18 (DEPLOY-001 Fase 4 -- capacidade: ~$10M prudente nos majors, limitado por TRX; Sharpe-based e otimista)

```text
- FASE 4 (capacidade/liquidez/impacto).
- Infra (ZERO mudanca economica): TsmTrendResult agora expoe per-symbol L/S
  weights (symbols + ls_weight_rows), read-only, para analise downstream. Os 27
  testes do tsm_trend seguem passando (base intacta; pesos somam unit-gross).
- src/research/capacity.py: turnover_matrix / participation_matrix /
  slippage_bps_matrix / capacity_net_returns (puros) + 6 testes.
- scripts/run_tsm_capacity.py: varre grid de capital ($1k..$100M) usando
  participacao REAL por simbolo (dollar-volume trailing-24h) + cenarios de
  impacto (none/low/moderate/severe).
- Resultado (majors original-20): participacao escala linear; simbolo GARGALO =
  TRXUSDT (menos liquido dos 20). Capacidade PRUDENTE (<=10% ADV) ~$10M. O Sharpe
  quase nao degrada ate $100M (0.966 -> 0.959) MAS isso e o modelo linear de
  slippage sendo gentil (cap em 100% ADV subestima o impacto real em alta
  participacao) -> as figuras Sharpe sao OTIMISTAS; a headline honesta e a
  participacao. Achei o defeito do criterio (Sharpe-based enganava) e corrigi:
  headline = capacidade por participacao.
- Universo majors = LIMITE SUPERIOR de capacidade; universos menos liquidos
  (TSM-015) tem capacidade bem menor.
- Verificacao: 612 testes (6 novos de capacity), ruff limpo. Nenhum parametro
  economico tocado. reports/capacity_analysis.md.
```

## 2026-07-18 (DEPLOY-001 Fase 3 -- execucao realista: gap teorico-vs-executavel MINIMO em tamanho pequeno)

```text
- FASE 3 (modelo de execucao realista): src/research/execution_model.py.
  - UMA politica conservadora PRE-DECLARADA (nao escolhida por Sharpe): taker fee
    4.5bps + half-spread 2.0bps + slippage linear na participacao; executa no
    primeiro preco APOS o sinal, cruza o spread, sem fill maker, sem melhor preco
    posterior. Memoryless por rebalance (cost[t] usa so t -> sem lookahead).
  - Limitacao honesta: temos klines (sem bid/ask/tick) -> friccoes sao overlay de
    custo sobre os retornos causais, nao simulacao de fill tick-a-tick.
- scripts/run_forward_execution_report.py: mede teorico(A) vs executavel(B) vs
  conservador(C, 50% do risco) e POPULA o ledger imutavel com os rebalances OOS.
  - Resultado (dev original-20): Sharpe A/B/C = 0.970 / 0.966 / 0.966; custo
    executavel base 6.5bps/leg vs 6.0 declarado -> gap MINIMO (haircut ~0.4%),
    coerente com cost-insensitivity (FC-II-007 breakeven ~142bps). Slippage de
    TAMANHO cresce com participacao -> quantificado na Fase 4.
  - Ledger: 5 eventos OOS (junho/2026) escritos em artifacts/tsm/forward/
    canonical_ledger.jsonl (append-only, idempotente na re-execucao). Movido para
    artifacts/ (data/research/* e gitignored) para o historico viver no git.
- Verificacao: 606 testes (8 novos de execucao), ruff limpo. Nenhum parametro
  economico tocado.
```

## 2026-07-18 (DEPLOY-001 Fase 2 -- ledger forward IMUTAVEL append-only, 3 streams)

```text
- FASE 2 (paper-forward imutavel): src/research/forward_ledger.py.
  - decision_id DETERMINISTICO = sha256(config_hash|exchange|symbol|signal_ts) ->
    replay do mesmo dia e idempotente.
  - Append-only JSONL: replay identico = no-op; MESMO id com conteudo DIFERENTE
    -> LedgerImmutabilityError (o passado nunca e sobrescrito).
  - Correcoes = eventos NOVOS (event_type=correction) que referenciam o original
    + motivo; a linha original nunca e editada (fluxo de bug da spec).
  - Schema de evento COMPLETO (decision_id, config_hash, commit, timestamps com
    UTC, side/pesos/notional, bid/ask/mid/fill, fee/slippage/funding, gross +
    3 streams de PnL, flags de data/execucao).
  - 3 streams via three_stream_pnl: A teorico (gross - custo declarado), B
    executavel (gross - friccoes reais), C conservador (fracao de risco * B - drag).
- Populacao REAL do ledger com os 3 streams depende do modelo de execucao (Fase
  3) -- separacao correta de responsabilidades, nao atalho. Fase 2 entrega o
  backbone testado (10 testes: id deterministico, idempotencia, imutabilidade,
  fluxo de correcao, round-trip, ordenacao dos streams).
- Verificacao: 598 testes (10 novos), ruff limpo. Nenhum parametro economico
  tocado.
```

## 2026-07-18 (DEPLOY-001 Fases 0+1 -- config canonica congelada; AUDITORIA de drawdown corrige narrativa "shallow")

```text
- NOVA fase do projeto (ADR-0033, TASK-DEPLOY-001): congelar a TSM validada e
  transforma-la em sistema forward executavel/auditavel. NAO e pesquisa de alpha.
  Principio: separar pesquisa/validacao/execucao/risco/producao/forward; infra
  nunca altera parametros economicos. Sem dinheiro real.
- FASE 0 (congelar config canonica): scripts/freeze_canonical_config.py ->
  artifacts/tsm/canonical-config.json + frozen-configs.json. Ambiguidade de nome
  resolvida PELOS ARTEFATOS (nao relatorios): o nucleo robusto validado (TSM-009
  ..015 primario) e o BASE PURO -- sign x inverse-vol, unit-gross, 5d, funding
  on, SEM overlay managed-vol (Moreira-Muir window12/cap3) e SEM ERC. Esses dois
  formam o combined-caveated (secundario). config_hash reproduzivel ba5037fc...,
  source_commit e0779b0 (FC-II-008).
- FASE 1 (auditoria de metricas/unidades): src/research/drawdown.py (framings
  COMPOSTA e ADITIVA, com timestamps de pico/vale/recuperacao) + 13 testes de
  borda (incl. o check canonico equity 1.00->0.20 = 80%). scripts/
  run_tsm_drawdown_audit.py reconstroi os 7 universos offline.
- VEREDITO = B (unidade/enquadramento, NAO bug de calculo): o maxDD ~0.31-0.80
  reportado era ADITIVO (np.cumsum, P&L cumulativo por unidade de gross), NAO %
  de equity composta. O aditivo REPRODUZ o _max_drawdown legado exatamente. Os
  drawdowns COMPOSTOS reais sao 31.0%-57.8% -> ou seja "0.80" = 57.8% (NAO 80%),
  MAS NAO sao "shallow": 58% e um drawdown severo. Corrige a narrativa anterior.
- Achado adicional honesto: mid_alt_l1 e defi ficam UNRECOVERED no fim da janela
  (drawdown composto ~55-57% ainda aberto) -- casa com o achado temporal (TSM-014).
- DECISAO: daqui pra frente a metrica-cabeca de risco e o maxDD COMPOSTO %.
  Nenhum parametro/estrategia alterado (drawdown e reporting, nao logica economica).
- Verificacao: 588 testes (13 novos de drawdown), ruff limpo. Fases 2-7 a seguir.
```

## 2026-07-17 (TSM stress de liquidez -- LIQUIDITY-ROBUST dentro dos sobreviventes; LOW tier sobrevive ate 30bps)

```text
- Prioridade #3 do usuario (universos adicionais), focada no eixo DISCRIMINANTE
  que faltava: LIQUIDEZ. Todos os resultados ate agora viviam em majors/alts
  liquidos onde 6bps e valido; liquidez baixa e onde trend tipicamente quebra.
- TASK-TSM-015: docs/pre_registers/TASK-TSM-015.md travado A PRIORI (tercis por
  mediana de quote_volume diario; varredura de custo 6/12/20/30bps).
  scripts/run_tsm_liquidity_stress.py OFFLINE (uniao dos 45 symbols cacheados,
  ZERO download); TSM base FIXO por tier.
- Resultado: LIQUIDITY-ROBUST (dentro dos sobreviventes). Sharpe @6bps HIGH
  0,769 / MID 0,934 / LOW 0,842 (gap HIGH-LOW -0,073, SEM degradacao monotona).
  LOW tier na varredura: 6bps 0,842 -> 12 0,810 -> 20 0,767 -> 30 0,714; buy-hold
  do LOW -0,510. LOW bate buy-hold em TODO custo, incl. a regua de 20bps.
- Notavel: HIGH e o tier MAIS BAIXO, MID o mais alto -> edge de trend mais forte
  nos alts menos eficientes, nao nos majors (coerente com toda a tese).
- CUSTO HONESTO: LOW tem drawdowns MAIS PROFUNDOS (maxDD 0,686 vs ~0,47 HIGH/MID)
  -- Sharpe comparavel, risco maior em baixa liquidez.
- RESSALVA DE SURVIVORSHIP (central): iliquidos/microcap reais nao tem 3a de
  historico e estao AUSENTES -> testa so o extremo menos liquido dos
  sobreviventes = limite inferior otimista, nao a cauda real. quote_volume e
  proxy grosseiro (sem spread/book).
- Verificacao: 575 testes (7 novos: proxy de liquidez, tercis, metrics), ruff
  limpo. Descritivo; sem promocao; sem mudanca de parametro.
```

## 2026-07-17 (TSM robustez temporal -- TEMPORALMENTE ROBUSTO com custo honesto: drawdowns longos ~14m mas rasos)

```text
- Prioridade #4 do usuario: robustez temporal (janelas independentes, NUNCA
  escolhidas apos ver resultados). Tambem preenche a lacuna de TSM-013 (sub-
  periodo salvo so 1/7).
- TASK-TSM-014: docs/pre_registers/TASK-TSM-014.md travado com janelas FIXAS A
  PRIORI (3 sub-periodos padrao; rolantes W6=37/W12=73 derivadas da cadencia 5d).
  scripts/run_tsm_temporal_robustness.py reconstroi OFFLINE (barras cacheadas,
  ZERO download) o stream de PnL/rebalance do TSM base (FC-II-008, include_funding,
  zero re-tune) de 7 universos cripto; reusa UNIVERSES do multiverse.
- (A) Sub-periodos x universo (backfill 1/7 -> 7/7): cada universo positivo em
  >=2/3. Medias cross-universo: 2023-06/2024-05 1,39 (100% pos); 2024-06/2025-05
  0,50 (100% pos, mais fraco); 2025-06/2026-05 0,56 (86% pos). So 1 celula
  negativa quase-zero (defi 2025-06 -0,02).
- (B) Rolling pooled: W6(~6m) 77% positivas; W12(~12m) 91%.
- (C) Duracao de drawdown: pior ~415d (~14 meses), time-underwater 79-89%.
- Veredito: TEMPORALMENTE ROBUSTO -- edge holds no tempo, nao numa janela quente.
  CUSTO HONESTO (nao acucarado): drawdowns LONGOS (~14m nos universos mid/alt --
  mid_alt_l1/defi/mid_tier_ref, os mesmos mais fracos no ano FINAL, provavelmente
  ainda underwater no fim), MAS em profundidade MODESTA (maxDD ~0,31-0,80) =
  grinds rasos-porem-longos, tipicos de trend. Robustez repousa em (A)+(B); (C)
  e o risco honesto.
- Achado colateral: corrigido bug real do _sharpe (slice constante gerava Sharpe
  ~5e16 por std de rounding ~3e-17 != 0) -> guard com epsilon 1e-12 -> None. Um
  teste pegou isso; outro pegou off-by-one na duracao de drawdown (peak-to-
  recovery deve incluir a barra de recuperacao). Ambos corrigidos.
- Verificacao: 568 testes (10 novos: helpers puros + os 2 bugs acima), ruff
  limpo. Descritivo; sem promocao; sem mudanca de parametro. TradFi nao re-rodado.
```

## 2026-07-17 (TSM caracterizacao estatistica -- ROBUSTEZ IN-DOMAIN comprovada: Sharpe medio 0,783, IC95 [0,628,0,928] exclui zero)

```text
- Prioridade #5 do usuario: caracterizacao estatistica. Sintese DESCRITIVA dos
  artefatos ja committados (TSM-008/009/010/011/012) numa unica frase de robustez.
- TASK-TSM-013: docs/pre_registers/TASK-TSM-013.md travado ANTES de computar
  (define as estatisticas). scripts/run_tsm_stat_characterization.py le so JSON
  do cost_pilot; NENHUM backtest novo, NENHUMA mudanca de param. Cripto in-domain
  (n=7 universos) vs TradFi out-of-domain (n=4) NUNCA pooled. Bootstrap semente
  FIXA 0 (10k) -> reproduzivel; t-IC como cross-check (n pequeno).
- Resultado CRIPTO (base TSM fixo): Sharpe media 0,783 (mediana 0,832, sd 0,220,
  CV 0,28); IC95 bootstrap [0,628, 0,928] EXCLUI zero (t-IC [0,579, 0,987]);
  positivo 7/7; bate buy-hold 7/7. -> ROBUSTEZ ESTATISTICA IN-DOMAIN: o edge e
  propriedade cross-universo estavel, nao sorte.
- Degradacao SUAVE: melhor gaming 1,004, pior old_guard 0,462 (spread 0,543),
  pior ainda positivo -> sem penhasco. Sub-periodo mais fraco: 2024-06/2025-05.
- Overlay (combined-base): delta Sharpe medio -0,027; combined>base so 3/7 ->
  confirma overlays parcialmente universe-specific; base vol-targeted = CORE.
- TradFi (out-of-domain, SEPARADO): Sharpe medio -0,037, 0/4 bate buy-hold ->
  limite documentado (TSM-012), reportado a parte, nunca pooled.
- Ressalvas honestas: n=7 pequeno (IC largo-ish); cobertura de sub-periodo so
  1/7 cripto (original_20, unico com sub-periodos salvos). Descritivo; sem
  promocao; sem mudanca de parametro.
- Verificacao: 558 testes (6 novos: helpers puros + reprodutibilidade do
  bootstrap), ruff limpo. Nenhum arquivo de Execution/Ledger/live tocado.
```

## 2026-07-17 (TSM cross-asset-class -- 0/4 TradFi; LIMITE documentado, edge cripto-especifico nesta janela)

```text
- Prioridade #2 do usuario: generalizacao cross-asset-class. Pergunta central:
  o edge e trend-following multi-ativos (Hurst-Ooi-Pedersen) ou cripto-especifico?
- TASK-TSM-012: scripts/run_tsm_asset_classes.py -- Yahoo chart API keyless,
  MESMOS horizontes economicos (28/7/5 dias) em barras diarias, include_funding
  =False, sqrt(252/5), ZERO re-tune. 4 universos: indices/commodities/forex/ETFs.
  25.735 barras baixadas.
- Resultado: TSM positivo E > buy-hold em 0/4 classes. Absoluto: commodities
  +0,18 e ETFs +0,13 (fraco+), indices -0,29 e forex -0,16.
- Regra #6 (literatura ANTES de interpretar): o comportamento CONCORDA com a
  evidencia recente -- 2023-2024 foi periodo DOCUMENTADAMENTE fraco pra trend/
  CTAs de TradFi (bull de acoes, baixa 'trendiness'; SG Trend flat-to-down --
  Capstone/Auspice/HedgeNordic/Quantica). Papel do trend = crisis-alpha/
  diversificacao, NAO bater um bull -> 'bate buy-hold' e regua adversa-por-
  construcao e a janela e um regime fraco conhecido.
- Leitura honesta (limite, nao refutacao): o edge FORTE do TSM e, nesta janela,
  CRIPTO-ESPECIFICO (cripto 2023-26 = dispersao/vol/negative-alt-drift altos,
  ideal pra long/short trend; TradFi = bull liso, adverso). NAO refuta o edge
  cripto (7 universos + 2 exchanges). LIMITA a claim: robustez cripto multi-
  universo + cross-exchange comprovada, cross-asset-class NAO.
- Por regra #6, NENHUMA mudanca de estrategia (efeito de regime/benchmark).
  Teste futuro justo = janela mais longa + universo pooled ~50+ + regua de
  diversificacao/absoluto (pre-registro proprio).
- Ressalva: futuros continuos do Yahoo tem vies de roll. Nao e promocao live.
- Verificacao: 552 testes passando, ruff limpo. Sem testes novos (script).
- Nenhum arquivo de Execution/Ledger/Recovery/ML/live/order-routing tocado.
```

## 2026-07-17 (TSM cross-exchange na Bybit -- Sharpe 0,971 vs Binance 0,970, venue-independent)

```text
- Prioridade #1 do usuario: generalizacao cross-exchange. Reconnaissance:
  Bybit v5 (klines+funding 8h, historico 2023-06, 633 perps) e OKX viaveis;
  Hyperliquid FORA (candleSnapshot raso).
- TASK-TSM-011: scripts/run_tsm_bybit_crossexchange.py -- cliente Bybit v5
  publico resiliente (klines+funding paginados, backward as-of merge -> mesma
  schema), TSM BASE FIXO (zero re-tune), MESMOS 20 symbols, mesmo codigo,
  Bybit vs Binance. 20/20 baixados (26.304 barras cada).
- Resultado: Bybit Sharpe 0,971 vs Binance 0,970; maxDD 0,341 vs 0,347;
  turnover/net/subperiodos quase identicos. GENERALIZA (venue-independent) ->
  o edge nao e artefato de dados/microestrutura da Binance. Ressalva: precos
  do mesmo simbolo sao arbitrados entre venues -> similaridade esperada; este
  teste descarta artefatos de dado de venue, e os cross-UNIVERSE (TSM-009/010)
  sao a diversidade mais forte. O match quase-identico valida o pipeline Bybit.
- Scorecard: TSM base testado em 7 universos de ativos + 2 exchanges, params
  fixos, zero retuning, positivo em todos. Proximo: OKX, classes de ativo,
  OOS continuo. 552 testes, ruff limpo.
```

## 2026-07-16 (TSM base generaliza em 6/6 universos tematicos -- evidencia mais forte contra overfitting)

```text
- Usuario: breadth de validacao > +0,2 Sharpe; o resultado que importa e o TSM
  base funcionar em outro universo com params fixos. Prioridade #1: expandir
  out-of-universe para varios universos tematicos.
- TASK-TSM-010: base TSM FIXO (FC-II-008, zero re-tune) em 6 universos
  (large_cap, mid_alt_l1, defi, gaming, old_guard, mid_tier_ref). Harness com
  download resiliente POR SIMBOLO (flaky/ausente pulado). 44 symbols.
- Resultado: base Sharpe > 0 E > buy-hold em 6/6 -- large_cap 0,99 (bh 0,14),
  gaming 1,00 (bh -0,80), defi 0,83 (bh -0,45), mid_alt_l1 0,65 (bh -0,56),
  mid_tier_ref 0,58 (bh -0,43), old_guard 0,46 (bh 0,06). Em 4/6 o buy-hold e
  NEGATIVO e o TSM positivo. **Evidencia mais forte do projeto contra
  overfitting** (out-of-sample na dimensao de ATIVOS, params fixos). Reforca
  TSM-009: combinado bate base em so 2/6 -> base = core robusto, overlays
  universe-specific.
- Limitacao honesta: AI/memecoins sem historico 3a -> nao testaveis nesta
  janela. Nao e promocao live. Proximo (plano do usuario): outras exchanges
  (Bybit/OKX), outras classes de ativo, OOS continuo. 552 testes, ruff limpo.
```

## 2026-07-13d (teste out-of-universe do TSM combinado -- CORE generaliza, OVERLAYS nao)

```text
- Usuario escolheu o teste out-of-universe (novo mercado, gratis). TASK-TSM-009:
  config FIXA do combinado (TASK-TSM-008) rodada numa universe DIFERENTE de
  alts. Download da data.binance.vision instavel (WinError 10054 repetido);
  adicionei resume-retry e restringi a familias klines+fundingRate (unicas que
  o TSM usa). 10 de 15 candidatos baixaram completos (NEAR/FIL/AAVE/ALGO/ICP/
  SAND/MANA/AXS/GRT/CRV); 5 descartados por DISPONIBILIDADE (nao performance).
- Resultado: base 0,577 / combinado 0,335 / buy-hold -0,429. ACHADO importante
  (dev-window nao pegava): (1) o CORE do TSM GENERALIZA -- base e combinado
  batem buy-hold em todos os subperiodos numa universe fresca -> trend e edge
  GERAL, nao artefato dos 20 (sobe confianca na base); (2) MAS os overlays NAO
  generalizam -- combinado 0,335 < base 0,577 (oposto da universe original) ->
  ERC+vol-target parcialmente especificos da universe/overfit (tempera o
  combinado). Base vol-targeted = core robusto; combinado = melhor so na
  universe de deploy.
- Corrigi o veredito auto-gerado (que superestimava "GENERALIZES") para a
  leitura honesta de dois lados. 552 testes, ruff limpo.
```

## 2026-07-13c (TSM convergiu -- candidato lider combinado no paper-forward; foco agora e OOS + novas familias)

```text
- Usuario: a familia TSM praticamente convergiu; cada nova tentativa na mesma
  janela aumenta a chance de falso-positivo. Maior ganho agora: (1) por o
  ERC+Vol-Target no paper-forward JA, (2) acumular OOS, (3) em paralelo abrir
  NOVAS familias (novos dados/hipoteses/mercados), nao refinar o TSM ao infinito.
- Feito (1): scripts/run_tsm_paper_forward.py agora tem como PRIMARIO o
  combinado ERC + vol-target (TASK-TSM-008). Overlay vol-target aplicado ao
  stream ERC COMPLETO e so entao fatiado pos-cutoff (causal). Jun/2026: 5
  rebalances OOS (Sharpe 4,04 = ruido; 95 p/ o gatilho). Relogio OOS do lider
  iniciado; re-rodar mensalmente.
- Estado: TSM ENCERRADO como linha de refinamento (candidato lider = combinado,
  Sharpe dev 1,18). Proximo = OOS accrual + decidir nova familia (exige novo
  dado/mercado; fronteira gratis publica+DVOL esgotada -> provavel decisao de
  gasto/mercado do usuario). 552 testes, ruff limpo.
```

## 2026-07-13b (TSM combinado ERC + vol-targeting -- MELHOR config; candidato OOS lider)

```text
- Usuario escolheu testar a sintese das duas melhorias limpas (ERC + vol-tgt).
  TASK-TSM-008: principled (cada uma validada sozinha antes; mecanismos
  ortogonais -- cross-sectional vs serie temporal), 1 variante combinada.
- scripts/run_tsm_combined_dev.py compoe modulos ja testados (portfolio_erc +
  apply_vol_target), sem codigo de alfa novo; compara 4 variantes.
- Resultado (DEV): Sharpe base 0,970 -> ERC 1,039 -> vol 1,107 -> COMBINADO
  1,183 (+0,076 sobre o melhor isolado), maxDD 0,309 (o menor), net o maior.
  COMPLEMENTARES: combinado melhor em TODOS os subperiodos, ambos regimes BTC
  e todo custo. PASSA -> CANDIDATO LIDER a OOS. Melhor config do TSM (1,18 /
  0,31), supersede os isolados. Puro-TSM. Sem promocao; OOS-gated. 552 testes.
```

## 2026-07-13 (Options-skew PAID-GATED; volatility-targeting do TSM PASSA limpo -- 3o candidato OOS)

```text
- Usuario deu ordem de prioridade (Options skew #1, refinar TSM, ensembles,
  risk overlay, sizing; TSM continua a prioridade ate esgotar).
- Reconnaissance Options: API publica Deribit so da snapshot ATUAL da cadeia
  (mark_iv por strike) + trades esparsos + DVOL 30d ATM (ja usado). Historico
  de skew/25dRR/butterfly/term-structure NAO e reconstruivel de graca ->
  PAID-GATED (Tardis/Amberdata, item #6, decisao do usuario).
- Seguindo a enfase em TSM, TASK-TSM-007: volatility targeting (Moreira-Muir;
  Man Group/Research Affiliates). src/research/vol_target.py (overlay causal
  knob-free sobre o stream de retorno; alvo=media expanding -> alavancagem
  media ~1; CAP 3.0; 6 testes).
- Resultado (DEV): Sharpe 0,970 -> 1,107 (+0,137), maxDD 0,347 -> 0,329
  (melhor). PASSA LIMPO: melhor nos 3 subperiodos, ambos regimes BTC, e todo
  nivel de custo. Ao contrario do prior ("mudo p/ trend"), ajudou -- a vol dos
  retornos do TSM e explotavelmente variavel. 3o candidato OOS do TSM (com ERC
  + ensemble), puro-TSM. Mais limpo que o ERC. Sem promocao; OOS-gated.
  552 testes, ruff limpo.
```

## 2026-07-12j (VRP como overlay no TSM -- NAO_PASSA; exploracao GRATIS do VRP encerrada)

```text
- Usuario escolheu testar VRP como feature/overlay. TASK-ALT-013: blend
  equal-risk do stream TSM + VRP-timing(primario), reusa
  tsm_ensemble.blend_diagnostic (mesmo da Linha 5). Sem modulo/teste novo.
- Resultado (DEV): TSM 0,991 / VRP 0,493 / blend 0,966 (PIOR), corr +0,180.
  NAO_PASSA -- perna VRP fraca e positivamente correlacionada puxa o Sharpe
  para baixo (VRP -0,48 em 2024-25). VRP nao ajuda o book como overlay.
- ENCERRA a exploracao GRATIS do VRP: sinal real (info+economia) mas sem
  monetizacao gratis (nem standalone/ALT-012 nem overlay/ALT-013). Restam
  skew/superficie (dado de opcoes mais pesado) e VRP-harvesting (Angle A,
  livro de opcoes) -- decisoes de gasto/instrumento do usuario. 546 testes.
```

## 2026-07-12i (VRP-timing como estrategia -- NAO_PASSA standalone; sinal real mas melhor como feature)

```text
- Usuario escolheu pre-registrar um backtest de timing VRP. TASK-ALT-012:
  src/research/vrp_timing.py (compute_vrp_z identico a ALT-011 + backtest
  long/short sign(vrp_z) semanal BTC/ETH; 8 testes) + dev script c/ bateria.
- Resultado (DEV): primaria long/short Sharpe 0,493 vs buy-hold 0,349
  (melhor), net melhor, MAS maxDD 0,787 vs 0,774 (pior) e INCONSISTENTE
  (subperiodo 2024-25 negativo; so ganha em 2025-26). NAO_PASSA o criterio.
- Corrige o vies do teste de decil: o spread de 197 bps era inflado por
  amostragem sobreposta; a estrategia semanal real e modesta/drawdown-heavy.
- Secundaria long-only melhor (Sharpe 0,601, maxDD 0,500) MAS descritiva-only
  (nao promove ex-post; precisaria de pre-registro proprio).
- Conclusao honesta: VRP e sinal REAL (info+economia), mas melhor como
  FEATURE/overlay, nao trade standalone. Sem promocao; OOS-gated. 546 testes.
```

## 2026-07-12h (Familia F Options aberta -- 1o HIT em dado externo: VRP preve retorno 7d de BTC/ETH)

```text
- TSM completo -> proxima familia por prioridade: Options (#1). Revisao de
  literatura profunda (mandato): evidencia a mais forte de todas -- arXiv
  2410.15195 (VRP positivo/persistente, option-implied preve retorno BTC);
  Atanasova et al. Dado FREE: API publica Deribit DVOL.
- Usuario escolheu Angle B (preditor p/ perp, sem pivo de opcoes). ADR-0032
  abriu Familia F. TASK-ALT-011: download_alt_dvol.py (DVOL diario BTC+ETH,
  keyless, 2192 linhas) + diagnostic_alt_options_vrp.py (reusa info_content):
  4 features (dvol_z, vrp_z=IV^2-RV^2, dvol_change_z, iv_rv_ratio_z) vs
  retorno 7d/30d.
- Resultado: **vrp_z@7d TEM_INFORMACAO** -- rho +0,0866, POSITIVO e
  sign-consistent nos 3 subperiodos (+0,088/+0,046/+0,110), coerente com a
  teoria e a literatura. 1o HIT em dado externo do projeto. vrp@30d rho maior
  (+0,11) mas inverte no 1o subperiodo -> corretamente SEM.
- Ressalvas: BTC/ETH-only (2-asset, sinal de timing, nao cross-sectional).
- Teste economico descritivo (passo pre-registrado, info != edge): spread
  bruto top-vs-bottom-decil 196,8 bps/7d vs ~12 bps custo (net +184,8,
  monotonic. +0,67). 1o sinal a passar AMBAS as barras (info E economia). MAS
  tail-driven (nao monotono limpo), holds sobrepostos amostrados diariamente
  (superestima), in-sample, BTC/ETH-only -> LEAD, nao edge validado. Proximo:
  backtest proprio de timing VRP semanal + OOS (task separada), ou vrp_z como
  feature no perp. Angle A (livro de opcoes) = decisao do usuario. Custo ZERO.
  2 testes novos, 538 na suite, ruff limpo.
```

## 2026-07-12g (TSM Linhas 5-6 -- ensemble trend+carry CARREGADO (carry-fragil); execucao encerrada; PROGRAMA COMPLETO)

```text
- TASK-TSM-005 (Linha 5, ensemble). Literatura: Koijen et al. "Carry" + CTA
  (trend+carry diversificam). Blend equal-risk 50/50 dos streams TSM + funding
  carry K=5 (semanal, padronizado a unit-vol). src/research/tsm_ensemble.py
  (puro, 6 testes) + dev script.
- Resultado (DEV): TSM 0,987 / carry 1,109 / BLEND 1,510 (+0,523), corr
  -0,037, blend maxDD 4,90 < 5,88. Bate o TSM nos 3 subperiodos (carry cobre
  2024-25 fraco do TSM; TSM cobre 2025-26 fraco do carry). PASSA o criterio
  limpo -> CARREGADO candidato OOS. RESSALVA: carry ja deu 1o mes OOS
  NEGATIVO -> blend herda fragilidade OOS; mais fraco que ERC (puro-TSM).
  Melhor numero dev do projeto, mas OOS-gated.
- TASK-TSM-006 (Linha 6, execucao): ENCERRAMENTO FUNDAMENTADO sem build --
  TSM cost-insensitive (FC-II-007 breakeven 142 bps) + Sprint 10 maker null
  -> otimizar execucao nao se justifica (ADR-0031 regra 6).
- PROGRAMA TSM (6 linhas) COMPLETO: regime/sizing/meta-labeling REJEITADOS,
  execucao encerrada; ERC (limpo) e ensemble (carry-fragil) carregados OOS.
  Proximo: familia Options/VRP (revisao de literatura profunda; free primeiro).
  536 testes, ruff limpo.
```

## 2026-07-12f (TSM Linha 4 meta-labeling / ML como filtro -- REJEITADO; replay da mirage ML-001)

```text
- Decisao ERC (Linha 3) resolvida: usuario delegou ("continue") -> ERC
  CARREGADO como candidato lider a OOS (o -0,003 e ruido; criterio nao
  relaxado; promocao segue OOS-gated).
- TASK-TSM-004 (Linha 4). Literatura: Lopez de Prado / Hudson & Thames
  (secundario filtra falsos positivos do primario). Precedente ML-001
  (mirage) -> minimal-DoF: 1 modelo FROZEN (GradientBoosting default), 1
  threshold FROZEN (0,5), 6 features causais, purged+embargoed walk-forward
  CV. keep_mask novo param em run_tsm_trend_backtest (base intacta).
- Resultado (DEV, OUT-OF-FOLD): edge por perna raso (label rate ~0,507);
  Sharpe OOF 0,784 -> 0,412 (PIOR), maxDD 0,347 -> 0,503 (PIOR); filtro
  ganhou so em 3/5 folds. REJEITADO/CAUTELAR -- replay exato da ML-001: ML
  concentra/curve-fita edge fino, ganhos por-fold nao sobrevivem OOF purgado.
- Linha 4 encerrada; seguir para Linha 5 (ensemble). 7 testes novos, 530 na
  suite, ruff limpo.
```

## 2026-07-12e (TSM Linha 3 portfolio construction -- ERC = 1a melhoria ampla; BORDERLINE, decisao de integridade)

```text
- TASK-TSM-003 (ADR-0031, Linha 3). Literatura: Baltas (risk-parity/ERC
  ciente de correlacao melhora trend-following; cripto tem alts colados em
  BTC -> inverse-vol naive da base ignora correlacao).
- Implementado erc_weights (coordinate descent) + _erc_reweight (covariancia
  causal 90d por rebalance, preserva direcao e split L/S da base) + flag
  portfolio_erc default OFF + 6 testes.
- Resultado (DEV, sem veredito): Sharpe 0,970 -> 1,039 (+0,069), maxDD 0,347
  -> 0,326 (melhor), turnover 0,457 -> 0,396 (MENOR), net maior. PRIMEIRA
  melhoria ampla: melhor nos 3 subperiodos, em todo custo, com/sem funding,
  DD melhor em todo corte; turnover cai (mecanismo do ERC -> economicamente
  explicado). Erra a LETRA estrita em UM corte (BTC-down Sharpe -0,003,
  ruido; DD ainda melhora la).
- Criterio NAO relaxado. BORDERLINE: candidato lider a OOS, mas a decisao de
  carregar (dada a complexidade covariancia+solver e o -0,003) e de
  integridade -> sinalizada ao usuario. Promocao segue OOS-gated. 523 testes.
```

## 2026-07-12d (TSM Linha 2 position sizing -- sizing por conviccao REJEITADO)

```text
- TASK-TSM-002 (ADR-0031, Linha 2). Literatura: regra TREND (Baz et al.;
  Hamill-Rattray-Van Hemert; Rohrbach) -- dimensionar pela forca do trend
  em vez do sign binario reduz turnover ~24% sem perder desempenho e domina
  o sign() fora de amostra.
- Hipotese: ponderar pernas por conviccao (trailing/vol) aposta mais nas
  fortes. Celula primaria sem knob: peso = trailing/vol, unit-gross (mesma
  exposicao; so muda reparticao). Flag conviction_sizing default OFF + 4
  testes.
- Resultado (DEV, sem veredito): Sharpe 0,970 -> 0,888 (PIOR), maxDD 0,347
  -> 0,390 (PIOR), turnover 0,457 -> 0,566 (MAIOR). REJEITADO decisivamente
  -- pior em todas as headline, no subperiodo recente, em BTC-up e em todo
  custo. A reducao de turnover da literatura vem da funcao SATURANTE
  (constantes tunaveis, excluidas); a linear knob-free churna mais.
- Linha 2 encerrada; seguir para Linha 3 (portfolio construction: risk
  parity/ERC/HRP). 517 testes, ruff limpo.
```

## 2026-07-12c (Programa de Melhoria do TSM aberto; Linha 1 filtro de regime -- 1a hipotese REJEITADA)

```text
- ADR-0031 abriu o Programa de Melhoria do TSM: fluxo completo por hipotese
  (literatura -> hipotese -> pre-registro -> implementar -> validar ->
  relatorio -> docs), params fixos a priori, dev != promocao (OOS-gated),
  base intacta, bateria de robustez obrigatoria, busca limitada por linha.
  Ordem: regime -> sizing -> portfolio -> meta-labeling -> ensemble -> exec.
- TASK-TSM-001 (Linha 1, regime). Literatura: Moreira-Muir (vol-managed) +
  cripto (trend recompensa serie-temporal; regra TREND por forca). Hipotese:
  TSM concentra edge quando ha trend forte; choppy = whipsaw. Filtro binario
  sem knob: FLAT quando forca agregada (media |trailing|/vol) < mediana
  causal 90d. Flag regime_filter default OFF (base intacta), 4 testes.
- Resultado (DEV, sem veredito): Sharpe 0,970 -> 0,949 (PIOR), maxDD 0,347
  -> 0,321 (melhor), livro ativo 42%. REJEITADO: agregado neutro esconde
  efeitos OPOSTOS por subperiodo (ajuda so 2024-06/2025-05) e por regime BTC
  (ajuda down, piora up) = assinatura de falso-positivo; unico efeito real e
  menos turnover (so ganha a custo irreal 30-60 bps). Hipotese encerrada;
  seguir para Linha 2 (position sizing). 513 testes, ruff limpo.
```

## 2026-07-12b (fluxo cross-venue via Coinalyze free tier -- 2a metade da trilha gratuita; nula; avenida gratis esgotada)

```text
- Usuario forneceu chave Coinalyze (em .env gitignored, .env.example so
  placeholder). TASK-ALT-010 (ADR-0030): fluxo cross-venue.
- download_alt_xvenue_funding.py: funding diario dos 20 assets em 4-5 venues
  majors {Binance,Bybit,OKX,Huobi,BitMEX}, perpetuos USDT. Parse puro
  testado com fixture; 429 tratado com backoff+Retry-After. 95 mercados ->
  103.325 linhas (asset,dia,venue).
- diagnostic_alt_xvenue_funding.py (reusa info_content): 3 features
  (disp/range/mean cross-venue, >=3 venues/dia) vs retorno 1d/3d. Prior
  divulgado: single-venue funding/OI/fluxo agregado ja nulos -> aposta so
  na DISCORDANCIA.
- Resultado: 6 celulas SEM_INFORMACAO. Near-miss mais estruturado da busca
  externa (NAO hit): disp/range@3d cruzam magnitude (+0,040) mas sao mirage
  de UM regime (2024-06/2025-05 rho ~+0,10; recente levemente negativo ->
  sign-consistency falha); @1d sign-consistent mas sub-limiar. Media ~0.
  Padrao de eficiencia crescente (decaimento), como OI/order-flow.
- Esgota a avenida de dado externo GRATIS (on-chain + cross-venue nulos).
  Resta so dado PAGO (on-chain premium, superficie de opcoes) e o pivo de
  instrumento (livro de opcoes) -- decisoes de gasto/instrumento do usuario.
  4 testes novos, 509 na suite, ruff limpo.
```

## 2026-07-12 (1a familia de DADO EXTERNO testada -- Familia G on-chain na camada gratuita; custo ZERO; nula)

```text
- Usuario escolheu (no brief de viabilidade) a trilha "on-chain + fluxo
  cross-venue na camada gratuita": provar sinal de graca ANTES de gastar.
- TASK-ALT-009 (ADR-0029): Familia G (On-Chain) via Coin Metrics community
  (keyless, custo ZERO). Reconnaissance de catalogo: fluxos de exchange so
  BTC/ETH (2/20); MVRV/active-addr/tx-count ~12-13/20; tudo 1d.
- download_alt_onchain.py (parse puro testado com fixture, so fetch toca
  rede) + diagnostic_alt_onchain.py (reusa info_content). 4 features
  causais diarias vs retorno 1d/7d. Nota: metrica on-chain finaliza apos o
  dia fechar -> shift(1) diario EXPLICITO extra (mais estrito que horario).
- Bug real corrigido no run: open_time saiu em SEGUNDOS (timestamp
  microssegundo + astype) -> 0 obs/subperiodo; corrigido com conversao ms
  unit-independent.
- Resultado: 8 celulas SEM_INFORMACAO pelo criterio travado. Near-miss (NAO
  hit): exchange_netflow_z@7d rho -0,0346 (coerente: inflow=venda), 2/3
  subperiodos negativos mas o do meio inverte -> sign-consistency falha; e
  so BTC/ETH. Proxies gratis nulos -> on-chain premium exige prior mais
  forte; decisao de gasto do usuario. Cross-venue continua key-gated
  (ALT-010). 505 testes, ruff limpo.
```

## 2026-07-11 (Funding Iteration 2: varredura de familias -- dado publico esgotado; fronteira e dado externo)

```text
- Adotado esquema de "familias de informacao" (marcar CONCLUIDA quando
  esgotada). Rodada autonoma, so pesquisa/paper, nada real.
- TASK-FC-II-001 position sizing (inverse-vol + vol-target, overlay no K=5):
  dev run nao bate o proprio gate (Sharpe +0,049 vs +0,15; drawdown pior).
- TASK-FC-II-002 basis: SEM_INFORMACAO (padrao E incremental sobre funding).
  Adicionado partial_spearman_rho ao info_content (+testes). Premium index
  ja nos bars -> sem download.
- TASK-FC-II-003 microestrutura curto (1h/4h): imbalance_price_divergence
  cruza o limiar (rho ~0,035, 1o hit direcional do projeto) MAS spread bruto
  ~1-2 bps vs custo 6-12 -> economicamente morto -> ABORT.
- TASK-FC-II-004 Familia E (fluxo): taker agressor + razoes long/short (ja
  em disco, do download de OI) -> 10 celulas SEM_INFORMACAO. Corrigiu
  afirmacao previa de "esgotado" testando o dado de fluxo que faltava.
- Trilha A: paper-forward do K=5; 1o mes OOS (jun/2026) NEGATIVO (PF 0,78).
- TASK-TSM-paper-forward (ADR-0027): recorder do TSM vol-targeted fixo (com
  funding); jun/2026 = 5 rebalances OOS (Sharpe 4,19 = RUIDO puro; 95 para o
  gatilho de 100). Inicia o relogio OOS; re-rodar mensalmente. Monitoramento,
  nao veredito.
- TASK-ALT-008 (ADR-0028): fecha a varredura em dado publico com os ultimos
  diagnosticos DIRECIONAIS nao rodados -- Familia B (range-vol: Parkinson/
  Rogers-Satchell/close-location) + Familia C (Amihud/turnover/trade-size),
  so barra, causais, 24h e 4h. 12 celulas SEM_INFORMACAO (max abs rho 0,027 <
  0,03 = clustering de vol, nao direcional; Amihud ~0,00). B e C passam de
  ~Concluida para CONCLUIDA (dado publico).
- Status: familias A(lead, OOS-gated)/B/C/D/E/I-barras/J CONCLUIDAS (dado
  publico). VARREDURA EM DADO PUBLICO COMPLETA. So restam F/opcoes-VRP,
  G/on-chain, H/sentimento, I/ticks -- exigem dado EXTERNO (decisao de
  aquisicao do usuario -- proximo passo = brief de viabilidade, sem baixar).
  501 testes, ruff limpo.
```

## 2026-07-09 (TASK-ML-001 - programa Funding Carry Inteligente: infra de meta-labeling construida; CV de dev cautelar)

```text
- Aberto ADR-0026 + pre-registro TASK-ML-001 (travados antes de codigo):
  filtro de meta-labeling sobre o funding carry incremental K=5 (near-miss
  PF 1,0904, INALTERADO). Gate BLOQUEADO ate OOS novo (>=500 rebalances
  apos 2026-05-31), consistente com ADR-0023/0024.
- Construido e testado (468 testes, ruff limpo): purged_cv.py (harness de
  CV walk-forward com purga+embargo, 15 testes incl. trava de vazamento),
  meta_labeling.py (painel causal + runner filtrado com renormalizacao +
  prova de equivalencia ao canonico), refactor leg_pnl_fracs em
  funding_carry.py (behavior-preserving, 18 testes), meta_model_selection.py
  + run_ml_meta_labeling_cv.py (selecao XGBoost via CV).
- Achado: unidade Opcao 1 (gatear so entradas) => ~38 exemplos (a
  incremental quase nao troca de perna). Trocada para Opcao 2 (perna-
  intervalo, ~30.140 linhas); pre-registro/ADR re-travados.
- CV de DESENVOLVIMENTO (sem veredito): "melhor" PF filtrado medio 4,99 =
  MIRAGEM (folds 3/5 PF 11-12 com PnL +169/+7 bps; folds 1/2/4 o filtro
  PIORA, net -160/-920/-7). Filtro NAO mostra melhora estavel; parece
  ajuste a ruido. Sinal cautelar/negativo. Gate segue bloqueado.
- Commit da infra Opcao 1 feito a pedido (95643ae); Opcao 2 + CV ainda
  nao commitados nesta anotacao.
```

## 2026-07-07 (TASK-ALT-004 - regime-conditioning TSREV fechado NAO_PASSA)

Depois da Family J mostrar informacao robusta de volatilidade/regime, abri
uma task separada de feasibility (ADR-0022/TASK-ALT-004) para testar o uso
operacional minimo e mais conservador: bloquear entradas da TSREV 24h quando
`realized_vol_168h` estivesse acima do percentil causal 67% da historia 90d
do proprio symbol. Pre-registrei explicitamente que isto nao seria validacao
final, pois o OOS 2025-06/2026-05 ja foi analisado varias vezes.

Implementei `scripts/run_regime_conditioned_tsrev.py` e
`tests/test_regime_conditioned_tsrev.py`: filtro causal, missing regime
fail-closed, no-lookahead por mutacao de futuro, filtro de trades por
allow_entry explicito e renormalizacao inverse-vol apos o filtro.

Resultado real: NAO_PASSA. O filtro bloqueou 1.187 trades OOS, manteve
2.758 trades resolvidas, mas piorou PF/net PnL (PF 0,9822; net
-6.110,64bps) e max drawdown seguiu enorme (61.748,50bps vs baseline
buy-and-hold 11.003,94bps). Decisao: esta variante de regime-conditioning
encerra; nao abrir novo-OOS deste filtro exato.

Verificacao: 18 testes focados, 424 testes na suite completa, ruff limpo
nos arquivos novos.

## 2026-07-07 (TASK-ALT-003 - Family J Regime Detection fechada)

Continuei a Research Phase II apos G/F fecharem sem informacao. Abri
ADR-0021 e `docs/pre_registers/TASK-ALT-003.md` antes de executar a
Family J, mantendo a excecao de ADR-0019: OHLCV permitido apenas como
camada de regime/contexto, nao como alpha direcional.

Implementei `scripts/diagnostic_alt_regime_detection.py` com target
`future_abs_return_24h = abs(log_price[t+24h] - log_price[t])` e 6 features
causais (`realized_vol_24h`, `realized_vol_168h`,
`trend_intensity_168h`, `volume_shock_24h`, `market_dispersion_24h`,
`market_abs_return_24h`). Adicionei `tests/test_alt_regime_detection.py`
cobrindo target absoluto, no-lookahead por mutacao de futuro, repeticao de
features de mercado por symbol e fail-closed para colunas faltantes/linhas
duplicadas.

Resultado real no dataset Sprint 7 normalizado, sem novo download: as 6
features passam `TEM_INFORMACAO` contra retorno absoluto futuro de 24h.
Mais fortes: `realized_vol_168h` rho=0,3009 e `realized_vol_24h`
rho=0,2927; todas com sinal positivo nos 3 subperiodos. Interpretacao
registrada: informacao de volatilidade/regime, nao alpha direcional.

Atualizei PROJECT_STATE, CURRENT_SPRINT, TASK_BOARD, HANDOFFS, TEST_MATRIX
e RISKS. Verificacao: 5 testes focados novos, 418 testes na suite completa,
ruff limpo nos arquivos novos.

## 2026-07-03 (TASK-SIG-004 - checagem intrahora 5m fechada)

Continuei a partir da revisao formal da TASK-SIG-004. O trabalho tecnico
central estava feito, mas a revisao pediu mudancas: governanca nao fechada e
bug de unidade em barreira vertical sub-hora.

Corrigi a unidade no core compartilhado: `TripleBarrierConfig` agora recebe
`bar_duration_hours` (default 1.0, preservando o comportamento de 1h),
`vertical_barrier_bars` calcula contagem real de barras via
`ceil((half_life_hours * multiplier) / bar_duration_hours)`, e o resolvedor
continua usando `open_time` real para proteger contra gaps. `statistical_backtest.py`
passa `bar_duration_hours` ao triple barrier e o runner 5m escala
`max_vertical_bars=2880` para preservar o cap real de 240h.

Rerodei a checagem real com `--no-download`, reaproveitando os dados 5m ja
baixados/normalizados (419.328 barras, 8 simbolos, 9 pares, 2025-12 a
2026-05). Resultado pos-correcao: baseline=tight, 23.051 trades, gross PF
1,1343, net PF 0,4223. O achado motivador 1h (gross PF 1,1559, net PF
0,8327, n=74) nao vira edge liquido em amostra adequada.

Atualizei `reports/signal_intrahour_sanity_check.md`, JSON/CSV de saida,
task file, TASK_BOARD, HANDOFFS, CURRENT_SPRINT, PROJECT_STATE e TEST_MATRIX.
Decisao: nao abrir TASK-SIG-005; Signal Iteration 1 permanece encerrada;
Sprint 10 nao abre automaticamente. Verificacao: foco 41 testes, suite
completa 315 testes, ruff limpo, git diff --check limpo.

## 2026-07-03 (Signal Iteration 1 - TASK-SIG-003, ultima tentativa e encerramento)

Usuario escolheu explicitamente "TASK-SIG-003: teste ex-ante de ENTRADA"
como proximo passo apos o STOP de TASK-SIG-002, e "ainda nao commitar".
Criei a task com regra de decisao PRE-REGISTRADA (net PF>=1,10 E
trade_count>=200) e grade fixa de `max_half_life_hours`. Implementei
`scripts/run_signal_entry_filter_experiment.py` + testes, rodei a grade
real: `STOP_SIGNAL_ITERATION`.

Despachei Quant + QA em revisao formal. QA: PASSA. Quant achou um P1 real:
a grade `[240,120,72,48,24,12]`h era NAO-VINCULANTE (so 0,064% dos trades
excluidos -- a distribuicao de half-life trailing das entradas ja e quase
toda <12h), entao a conclusao original extrapolava o que foi testado.

Corrigi generalizando o runner para grade configuravel (`--grid`) e
adicionando `binding_check` (audita automaticamente se uma grade exclui
fracao material de trades, sem hardcode). Pre-registrei um Run 2
independente com grade bem mais agressiva `[240,12,6,3,1.5,0.75,0.375]`h --
essa sim vinculante (99,88% excluidos no threshold mais apertado). Reescrevi
o relatorio final consolidando as duas execucoes com honestidade (Run 1
re-escopado, nao apagado) e uma secao de observacao descritiva claramente
rotulada como nao-decisoria (concentracao de gross edge em half-life muito
curto, mas amostra pequena demais para confirmar).

Re-despachei o Quant sobre o estado corrigido: PASSA, confirmando que
`binding_check` e generico (nao hardcoded) e que a decisao final
`STOP_SIGNAL_ITERATION` decorre honestamente da regra pre-registrada.

Fechei TASK-SIG-003 (DONE) no board, task file, HANDOFFS e PROJECT_STATE.
304 testes, ruff limpo, diff limpo. **Isto encerra a Signal Iteration 1**
(SIG-001/002/003) -- decisao macro de proximos passos volta para o usuario.
Nada commitado.

## 2026-07-03 (Signal Iteration 1 - TASK-SIG-002, experimento de reversao rapida)

Continuei de onde a sessao anterior parou (ela tinha implementado o runner e
as correcoes do QA mas parou no meio da validacao, deixando um teste
quebrando -- fixture de `compare_variant_results` sem a chave `outcome_counts`
que a funcao passou a consumir; alinhei o fixture ao contrato real).

Rerodei o experimento corrigido (com a barra confirmadora): baseline reproduz
o Sprint 8 canonico exatamente, e `max_vertical_bars=4` NAO melhora (gross
-15.427 bps, net -2.044 bps, PF -0.016). Decisao `STOP_FAST_REVERSION_PATH`.
A hipotese de reversao rapida do TASK-SIG-001 era survivorship ex-post.

Revisao formal (estado final, pos-correcoes): despachei Quant Research e
QA/Chaos frescos (os revisores da sessao anterior nao eram acessiveis daqui);
ambos PASSA, mais Backtest (sessao anterior) PASSA e PM PASSA. Quant e QA
levantaram o mesmo P3: a regressao da barra confirmadora era acoplada a mock.
Adicionei um teste com o resolvedor real, verificado que falha se a janela
voltar para `+1`.

Fechei TASK-SIG-002 (DONE) no board, HANDOFFS e PROJECT_STATE. 292 testes,
ruff limpo, diff limpo. Decisao estrategica sobre TASK-SIG-003 (teste ex-ante
de entrada) vs. encerrar iteracao de sinal esta com o usuario. Nada commitado.

## 2026-07-03 (Signal Iteration 1 - diagnostico de edge bruto)

Usuario decidiu explicitamente iterar o sinal primeiro antes de abrir Sprint
10 ou testar execucao passiva/maker. Criei `tasks/signal_iteration/` com
TASK-SIG-001 e TASK-SIG-002.

TASK-SIG-001 implementado:

```text
src/research/signal_diagnostics.py
scripts/run_signal_diagnostics.py
tests/test_signal_diagnostics.py
reports/signal_diagnostics.md
data/research/binance_public/cost_pilot/signal_diagnostics_sprint8_canonical.json
data/research/binance_public/cost_pilot/signal_diagnostics_sprint8_canonical.csv
```

Analise real dos 62.878 trades resolvidos do Sprint 8 canonico, sem rerodar
backtest nem carregar raw: gross PnL -48.248,03 bps (-0,7673 bps/trade),
gross profit factor 0,9866, net PnL -861.874,19 bps. PROFIT e muito mais
frequente que STOP (69% vs 10%), entao a hipotese "STOP demais" nao se
confirmou. `|z| >= 3.0` piora contra `2.0-2.5`. O recorte mais forte e
temporal: trades resolvidos em 2-4h tem gross medio +41,42 bps/trade,
enquanto holds de 5h+ sao fortemente negativos. Como `bars_held` e
`outcome` sao ex-post, a proxima tarefa nao pode filtrar retrospectivamente;
TASK-SIG-002 deve rerodar um experimento causal com `max_vertical_bars=4`.

Revisao formal:

```text
Quant Research Agent: PASSA, com ressalva de nao usar bars_held/outcome como
feature de entrada.
Backtest Agent: MUDANCAS SOLICITADAS -> PASSA apos materializar bucket 25h+
zerado e rebaixar OU half-life curto para hipotese secundaria.
QA / Chaos Testing Agent: MUDANCAS SOLICITADAS -> PASSA apos fail-closed para
status/side/outcome invalidos, bars_held<=0, |z|<2.0 e nenhum trade resolvido.
```

Verificacao: `pytest tests/test_signal_diagnostics.py` 13 passed;
`pytest tests -q` 283 passed; `ruff check src tests scripts` limpo;
`git diff --check` limpo. Sprint 10 permanece NAO ABERTA.

## 2026-07-03 (Sprint 8 Canonico - Triple Barrier + backtest estatistico)

User pediu para voltar e construir de verdade o Sprint 8 canonico do roadmap
mestre (ADR-0008 ja documentava a divergencia; ADR-0009 decidiu construir
retroativamente como trabalho separado, TASK-008C-01/02/03).

Implementado: `src/research/triple_barrier.py` (labeling triple barrier
direcional), `src/backtest/statistical_backtest.py` (backtest candle-level
com custo fixo conservador + funding real), `scripts/run_sprint8_canonical_backtest.py`.

Revisao formal: 4 agentes independentes na primeira passada (Backtest Agent
+ QA/Chaos Agent em triple_barrier.py; Quant Research Agent + QA/Chaos Agent
em statistical_backtest.py) encontraram 4 bugs P1 reais -- dois em cada
arquivo, incluindo o mesmo bug (`profit_factor_gate_pass` rejeitando `+inf`)
encontrado independentemente por dois revisores diferentes em
statistical_backtest.py. Todos corrigidos e re-revisados por 2 agentes
independentes adicionais: ambas as rodadas PASSA.

Execucao real: 41 pares estatisticos do Sprint 7, 526.080 barras reais.
Resultado: 0/41 pares aprovados (profit factor liquido >= 1.10). Portfolio
profit factor 0,782. Consistente com o NAO PASSA da Sprint 9 (metodologia
diferente, mesma conclusao direcional). `reports/backtest_statistical.md`
escrito com metodologia completa e ressalva de nao-comparabilidade com
Sprint 9. `project_control/RISKS.md` atualizado para fechar o debito tecnico
do ADR-0008. Suite completa: 270 testes passando, ruff limpo.

## 2026-07-02 (continuacao final - roadmap mestre, Sprint 9, correcao de dados)

User forneceu o roadmap mestre completo de 28 sprints e pediu para seguir a
Sprint 9 dele ("Backtest executavel com simulacao de ordens"), reusando os
13 pares do Sprint 8 e os 17GB de dados brutos ja baixados.

Governanca:

```text
Salvei o roadmap em project_control/ROADMAP.md (fonte de verdade de
sequenciamento de sprints).
Comparei contra o Sprint 8 ja executado neste projeto: diverge do Sprint 8
canonico do roadmap ("Triple Barrier + backtest estatistico"). Registrei
isso como ADR-0008 -- debito tecnico explicito, nao revertido, nao
escondido.
Criei tasks/sprint_09/ com 6 tarefas detalhadas (dono, revisor, arquivos
permitidos/proibidos, criterio de pronto, testes obrigatorios).
```

Implementacao Sprint 9:

```text
src/backtest/fill_model.py: MARKET/IOC e LIMIT+TTL contra top-of-book real
(nivel 1), latencia, ACK_UNKNOWN (hash deterministico por order_id,
integrado com AckGuardOrderStatus real do Sprint 3).
src/backtest/execution_simulator.py: round-trip por par com peso beta,
LEG_FILL_MISMATCH, integracao real com evaluate_ack_guard para atrasar
saida quando entrada ainda esta ACK_UNKNOWN.
src/backtest/replay_engine.py: replay causal dos mesmos sinais do Sprint 8,
cache de dias limitado (FIFO, max 4) apos um crash de memoria anterior por
carregar um mes inteiro de uma vez.
```

Crash de memoria e correcao:

```text
Primeira tentativa do lote completo (13 pares) morreu por OOM (codigo 137)
processando BTCUSDT/ETHUSDT. Investigacao revelou bug real: o runner usava
contract.approved_pairs (os 31 pares do cost-gate) em vez dos 13
backtest-approved do Sprint 8 -- incluindo BTCUSDT, um simbolo pesadissimo
que nem deveria estar em consideracao. Corrigido: default agora le
backtest_approved_pairs de sprint8_backtest_results.json. Reduzi
day_cache_size de 8 para 4 e adicionei gc.collect() entre pares como
margem de seguranca extra. Testei cautelosamente par a par (ETHUSDT
isolado) antes de rodar o lote completo de novo.
```

Bug real de PnL encontrado via inspecao manual de diagnostico:

```text
Ao inspecionar manualmente um trade simulado, percebi que a perna B tinha
filled_quantity=308.6 (preenchimento parcial real) mas average_price=None.
Causa raiz: estimate_slippage (Sprint 6, ja revisado) zera average_price/
slippage_bps sempre que a ordem nao preenche 100%, mesmo com preenchimento
parcial real e spent_notional populado. O execution_simulator usava
`average_price is None` como proxy de "nada aconteceu", entao zerava
SILENCIOSAMENTE o PnL real da perna em ~40-50% dos trades (onde havia
preenchimento parcial).
Corrigido em fill_model.py::_realized_price_and_slippage: calcula o VWAP
real a partir de spent_notional/filled_quantity (sempre populados) em vez
de confiar no average_price nulificado.
Resultado ANTES da correcao: portfolio -$1729.96 (todos os 13 pares
negativos).
Resultado DEPOIS da correcao: portfolio -$2266.27 (ainda todos os 13
pares negativos, mas MAIS negativo -- consistente com a mecanica do bug:
restaurar PnL real a pernas antes zeradas so podia piorar uma distribuicao
ja negativa, nunca melhorar artificialmente).
```

Revisoes formais (4 agentes, todas reais -- ver nota sobre sessao anterior
abaixo):

```text
Backtest Agent: MUDANCAS SOLICITADAS na comunicacao do relatorio (nao no
codigo) -- precisa de ressalva explicita de que MARKET_IOC nas duas pontas
e o cenario de custo mais caro possivel, e faltava metrica de fill parcial
na SAIDA (corrigido: adicionei partially_filled_exit_leg_count e
unclosed_residual_quantity ao resumo agregado).
QA Agent: PASSA -- re-derivou matematicamente a correcao do bug e confirmou
correta, confirmou que simulate_limit_fill nunca teve o bug, nao achou
padrao similar escondido, confirmou que o resultado mais negativo pos-
correcao e exatamente consistente com a mecanica do bug (nao suspeito).
Market Data Agent: MUDANCAS SOLICITADAS -- achou um P1 real: checksum era
computado mas nunca verificado contra o esperado antes de usar os dados
(fail-open, nao fail-closed). Corrigido com verify_checksum_file.
Execution/Risk Agent (consultivo): latencia de 250ms razoavel mas otimista
(sem variancia modelada); taxa de ACK_UNKNOWN de 2% nao calibrada por dados
reais; confirmou que simulate_limit_fill nunca e chamado pelo runner real
(lacuna real vs promessa do roadmap de testar IOC vs maker); risco de
perna residual nao fechada e de primeira classe, precisa de Hedge Engine/
Barrier Manager/Emergency Exit futuros; recomenda nao concluir "sem edge"
sem testar variante LIMIT/maker primeiro.
```

Nota importante sobre revisoes: dois dos quatro agentes (QA Agent e
Execution/Risk Agent) foram despachados numa sessao anterior que caiu antes
de eu receber os resultados reais deles. Em vez de escrever no relatorio
final o que eu ACHAVA que eles diriam, retomei os dois via SendMessage
nesta sessao e obtive as conclusoes genuinas deles antes de escrever
qualquer coisa. Nenhum conteudo de revisao fabricado foi para o relatorio
final ou HANDOFFS.md.

Resultado final real: 247 sinais, 239 trades executados, **0 dos 13 pares
sao liquido-positivos**, portfolio -$2266.27. 70/239 trades com
desbalanceamento de perna; 11.470,92 unidades de posicao nunca fechadas
(exposicao residual nao marcada a mercado). Todos os 13 pares invertem de
positivo (Sprint 8 idealizado) para negativo (Sprint 9 realista),
incluindo os dois melhores do Sprint 8 (ETCUSDT/LTCUSDT 542.58bps,
ARBUSDT/AVAXUSDT 456.59bps).

Verificacao:

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests -q
Result: passed, 242 tests.
UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src scripts tests
Result: passed.
```

Correcao de rastreamento de dados (a pedido explicito do usuario):

```text
Usuario explicou que alterna entre 2 computadores (um com pouco espaco) e
queria poder commitar tudo essencial no git para nao depender dos dados
brutos o tempo todo. Descoberta: .gitignore tinha uma regra generica
`data/` que ignorava TUDO em data/research/, inclusive os resumos
pequenos essenciais -- trocar de maquina hoje significaria perder tudo,
nao so os arquivos brutos grandes.
Corrigido .gitignore: agora versiona os JSON/CSV pequenos derivados
(~26MB) + um backup comprimido do bars.csv do Sprint 7 (330MB -> 67MB via
gzip -9, por escolha explicita do usuario, dado o custo de regenerar).
Deixado de fora do git (grande, regeneravel): bars.csv sem compressao,
ZIPs brutos do Sprint 7 (83MB), e os 17GB de bookTicker do Sprint 8/9
(TASK-008-08 continua bloqueada aguardando decisao de limpeza).
Commit 174d327 criado e enviado para origin/main com autorizacao explicita
do usuario ("pode da push tbm depois" / "pode da push" / confirmacoes
subsequentes). Local git user.email ja estava correto
(arthureich@hotmail.com), nenhuma mudanca de config necessaria.
```

Status:

```text
TASK-009-01 a TASK-009-06 movidas para DONE. Sprint 9 fechada com gate NAO
PASSA para "PnL positivo em cenario conservador" -- resultado honesto, nao
mascarado. Atualizados TASK_BOARD, CURRENT_SPRINT, PROJECT_STATE, RISKS,
TEST_MATRIX, HANDOFFS. Escopo do Sprint 10 nao definido -- decisao pendente
do usuario, com recomendacao explicita do Execution/Risk Agent de testar
variante LIMIT/maker antes de decidir se a estrategia tem edge.
```

## 2026-07-02 (continuacao - Sprint 8 execucao, revisao e correcao de P1s)

User instruction: "veja e continue pq o outro administrador acabou a cota,
gerencie os agentes" seguido de "administre a 8, para completar".

Takeover:

```text
Previous PM session (quota exhausted) had already implemented
project_control/SPRINT8_UNIVERSE.json, src/research/sprint8.py,
scripts/run_sprint8_backtest.py, and 3 test files (14 tests), and run a first
backtest (31 evaluated, 17 approved, portfolio net_pnl_bps=-125.83). It was
interrupted mid-ruff-fix on the runner script.
Finished the ruff fix (2 auto-fixable import-order issues).
Confirmed 204 tests passed before touching anything further.
```

Mandatory review (per CURRENT_SPRINT.md's own reviewer list, none of this had
been reviewed yet):

```text
Dispatched Backtest Agent, Quant Research Agent, Market Data Agent, and QA
Agent in parallel against the untouched first implementation.
Result: 3 blocking P1 findings (not cosmetic):
1. Backtest Agent: beta-weighting mismatch between signal generation
   (beta-weighted Kalman spread) and PnL calculation (1:1 leg combination).
2. Quant Research Agent: look-ahead in the mean-reversion/half-life gate --
   estimate_ou fit once on each pair's full 30-day series, letting a later
   regime approve earlier signals.
3. Market Data Agent: missing exit cost -- only entry cost was charged,
   understating round-trip cost by roughly half.
QA Agent: PASSA, 1 P2 (runner script had zero direct test coverage).
```

Fixes:

```text
1. _one_hour_gross_edge_bps now weights leg B's return by abs(intent.beta).
2. generate_pair_signal_intents now refits OU on a trailing causal window
   (ou_window=168h) ending at each candidate index instead of once over the
   full series; also uses per-index kalman.unstable_points instead of the
   aggregate beta_unstable flag (same bug class). Added
   test_generate_pair_signal_intents_is_causal_across_appended_future_bars:
   builds a 60-bar prefix and a 100-bar extended version with a sharply
   different trend, asserts signals inside the original window are
   byte-identical between the two runs.
3. _round_trip_symbol_cost_map (replacing _causal_symbol_cost_map) now sums
   causal cost at both entry and exit time per leg.
4. Renamed misleading gate_pass (true with just 1/31 pairs positive) to
   any_pair_backtest_approved, added explicit portfolio_gate_pass
   (portfolio_net_pnl_quote > 0, currently false).
5. Added tests/test_sprint8_backtest_runner.py (6 tests) covering the
   previously-untested runner functions, closing QA's P2.
```

Confirmation review (second pass):

```text
Backtest Agent + QA Agent combined re-review: PASSA. Independently verified
beta-weighting direction against the Kalman spread definition, confirmed the
OU window never reads past the candidate index, judged the new causal test
genuine, confirmed round-trip cost sums correctly.
One P3 investigated personally by PM (not just accepted): total_trades
identical (622) before/after the OU-gate fix. Reproduced independently via
a standalone script: for these pairs the full-sample half-life is very short
(~1-1.5h), so the causal window agrees with the full-sample fit at nearly
every index within a single 30-day month. Confirmed not a bug -- the fix
still changed net PnL materially via beta-weighting and exit-cost.
```

Corrected result:

```text
Reran scripts/run_sprint8_backtest.py after fixes.
Before: 31 evaluated, 17 approved, portfolio net_pnl_bps=-125.83.
After:  31 evaluated, 13 approved, 18 rejected, portfolio net_pnl_bps=-1716.67,
        portfolio_net_pnl_quote=-$171.67, total_trades=622 (unchanged, see
        above), any_pair_backtest_approved=true, portfolio_gate_pass=false.
More conservative after the fix, as expected from removing look-ahead and
cost understatement -- treated as a signal the fix worked, not a problem to
paper over.
```

Verification:

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests -q
Result: passed, 211 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src scripts tests
Result: passed.
```

Deliverable:

```text
Wrote reports/sprint_08_backtest.md: full methodology, results (13
approved / 18 rejected / portfolio negative, reported separately and
explicitly not conflated), review history including the 3 P1 findings and
fixes, and residual risks (fixed 1h exit, median-only cost, per-pair-only
drawdown).
```

Status:

```text
TASK-008-01 through TASK-008-07 moved to DONE. TASK-008-08 (cleanup of 17GB
raw evidence) remains BLOCKED pending explicit user acceptance -- not
deleted. Sprint 8 gate: PASSA, scoped to 13 backtest-approved pairs. Updated
PROJECT_STATE, CURRENT_SPRINT, TASK_BOARD, RISKS, TEST_MATRIX, HANDOFFS
accordingly. Sprint 9 scope/tasks not yet defined -- flagged for user
decision, not invented unilaterally.
```

## 2026-07-02 (abertura coordenada da Sprint 8)

User instruction: "administre entao a prox etapa".

Governance action:

```text
Opened Sprint 8 as "Backtest walk-forward cost-aware" in
project_control/CURRENT_SPRINT.md.

Sprint 8 scope is intentionally narrow:
- only the 31 pairs with genuine June-2023 cost_gated_pass=true;
- the 10 ADAUSDT pairs remain blocked by WIDE_MEDIAN_SPREAD;
- no live trading;
- no paper trading;
- no order router;
- no ledger/recovery/execution edits;
- no XGBoost/P_fill/P_profit.
```

Tasks created:

```text
tasks/sprint_08/TASK-008-01-freeze-universe-evidence.md
tasks/sprint_08/TASK-008-02-walk-forward-split.md
tasks/sprint_08/TASK-008-03-offline-signal-intent.md
tasks/sprint_08/TASK-008-04-cost-aware-backtest.md
tasks/sprint_08/TASK-008-05-metrics-ranking.md
tasks/sprint_08/TASK-008-06-qa-tests.md
tasks/sprint_08/TASK-008-07-report-gate.md
tasks/sprint_08/TASK-008-08-evidence-cleanup-plan.md
```

Task board decision:

```text
TASK-008-01 is READY.
TASK-008-02 through TASK-008-08 are BLOCKED by explicit dependencies.
This prevents agents from implementing backtest logic before the universe and
evidence contract is frozen.
```

Next executable dispatch:

```text
PM Agent should execute TASK-008-01.
Goal: create a machine-readable Sprint 8 universe/evidence contract with 31
approved pairs, 10 blocked ADAUSDT pairs, exact June-2023 evidence scope, and
tests that fail closed for ADAUSDT or out-of-universe pairs.
```

## 2026-07-02 (expansao all-candidates do cost gate de junho/2023)

User asked whether the other pairs could be tested, then approved doing what
was necessary to unblock Sprint 8, with explicit warning to avoid memory
blow-up and remove raw files later.

Memory-safety hardening before expansion:

```text
The existing daily runner already processed one symbol-day at a time, but it
still reused the generic `read_zip_csv`, which reads the whole ZIP member into
bytes before pandas. For BTCUSDT/ETHUSDT daily bookTicker files this was the
largest remaining OOM risk.

Updated `scripts/run_sprint7_execution_cost_download.py` to stream-read the
single CSV member directly from the ZIP with `zipfile.open`, explicit
BOOK_TICKER_COLUMNS, and numeric dtypes. Focused test passed:
tests/test_execution_cost_download.py = 3 passed. Ruff passed for the script.
```

Real expanded run:

```text
Target scope: all symbols appearing in the 41 Sprint 7 statistical candidate
pairs, June 2023 only:
ADAUSDT, ARBUSDT, ATOMUSDT, AVAXUSDT, BTCUSDT, DOGEUSDT, DOTUSDT, ETCUSDT,
ETHUSDT, LINKUSDT, LTCUSDT, OPUSDT, SOLUSDT, UNIUSDT, XRPUSDT.

The first attempt without network escalation failed at ATOMUSDT 2023-06-01
with temporary DNS failure, after reprocessing already-local ADA/ARB files.
Retried with network approval for only the 9 missing symbols:
ATOMUSDT, BTCUSDT, DOGEUSDT, ETHUSDT, LINKUSDT, LTCUSDT, SOLUSDT, UNIUSDT,
XRPUSDT.

The real run completed with no OOM. BTCUSDT and ETHUSDT included very large
single days (BTCUSDT 2023-06-14: 28,328,075 raw rows; ETHUSDT 2023-06-14:
22,467,809 raw rows), validating the streaming reader path.
```

Artifacts:

```text
data/research/binance_public/cost_pilot/missing_candidates_202306_hourly_cost.csv
data/research/binance_public/cost_pilot/all_candidates_202306_hourly_cost_raw.csv
data/research/binance_public/cost_pilot/all_candidates_202306_hourly_cost.csv
data/research/binance_public/cost_pilot/all_candidates_202306_duplicate_hours.csv
data/research/binance_public/cost_pilot/all_candidates_202306_bars.csv
data/research/binance_public/cost_pilot/all_candidates_202306_summary.json
data/research/binance_public/cost_pilot/all_candidates_202306_archive_manifest.csv
data/research/binance_public/cost_pilot/all_candidates_202306_manifest.json
data/research/binance_public/cost_pilot/all_candidates_202306_source_review.json
data/research/binance_public/cost_pilot/all_candidates_202306_execution_cost_gate.json
data/research/binance_public/cost_pilot/all_candidates_202306_execution_cost_gate.csv
```

Audit counts:

```text
450 daily Binance bookTicker ZIPs + .CHECKSUM files present.
17.98GB compressed archive bytes; cost_pilot directory now ~17GB.
10827 raw hourly rows.
27 duplicate symbol-hours / 54 duplicate rows at day boundaries.
10800 deduplicated hourly rows used by the gate.
10800 June-2023 1h bars for the 15 symbols.
```

Gate result:

```text
scripts/run_sprint7_execution_cost_evidence.py ran offline against the local
checksum-verified source_review manifest. Result: cost_gated_pass=true,
31/41 candidate pairs pass, 10/41 fail.

All failed pairs contain ADAUSDT:
ADAUSDT/DOTUSDT, ADAUSDT/AVAXUSDT, ADAUSDT/ETCUSDT, ADAUSDT/LINKUSDT,
ADAUSDT/DOGEUSDT, ADAUSDT/ETHUSDT, ADAUSDT/ARBUSDT, ADAUSDT/XRPUSDT,
ADAUSDT/ATOMUSDT, ADAUSDT/SOLUSDT.

Failure reason is correct and conservative: ADAUSDT fails the symbol-level
gate with WIDE_MEDIAN_SPREAD (median spread 3.52bps > 3.0bps threshold).
```

Verification:

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests --basetemp=pytest_temp_sprint8_gate_expand -o cache_dir=pytest_temp_sprint8_gate_expand/.pytest_cache
Result: 190 passed, 1 pytest config warning.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src tests scripts
Result: passed.

git diff --check
Result: passed.
```

Status:

```text
Sprint 8 may now open, SCOPED to the 31 pairs with genuine verified
June-2023 cost evidence. The 10 ADAUSDT failed pairs and any month outside
June 2023 remain statistical-only / blocked from cost-gated claims.

Raw archives should not be deleted until this manifest/evidence state is
accepted and, ideally, backed up externally. When deletion is approved, keep
the manifest, summary, source_review, gate JSON/CSV, bars CSV, deduped hourly
cost CSV, and duplicate-hours CSV.
```

## 2026-07-01 (continuacao 2 - piloto real de custo, ADR-0007, desbloqueio escopado)

User instruction: "faça o que falta então para podemos avançar com segurança"
(do what's needed so we can advance safely), in response to the 4 policy
options presented after the TASK-007-09/TASK-007-10 closure.

Feasibility check before acting:

```text
Full verified-window bookTicker download (20 symbols x 11 months) estimated
at ~273GB compressed via the S3 listing already captured. Downloading that
much data was judged unsafe/infeasible for this session (many hours). Chose
instead a bounded, real, non-fabricated pilot: 6 non-BTC/ETH top candidate
symbols x 1 verified month.
```

Crash and fix:

```text
First attempt (monthly bookTicker download for ETCUSDT alone) was OOM-killed
(exit 137); memory climbed to 24GiB used / swap engaged just downloading one
symbol-month, because read_zip_csv loads the whole decompressed CSV into
memory and a monthly bookTicker archive for a mid-cap symbol is multiple GB.
Rewrote the approach to use Binance DAILY bookTicker archives (~30x smaller),
processing one symbol-day at a time and freeing the raw frame immediately.
Verified with a single real symbol-day (ETCUSDT 2023-06-01: 847,659 raw rows,
memory returned to normal) before scaling up.
```

Implementation:

```text
Added BinanceDataFamily.BOOK_TICKER to src/research/historical_dataset.py
(additive; existing default families list and callers unaffected).
Wrote scripts/run_sprint7_execution_cost_download.py: downloads+verifies
checksum+normalizes+aggregates one symbol-day at a time.
Wrote ADR-0007 in project_control/DECISIONS.md: cost-gated PASS claims must
cite their exact verified evidence window; daily (not monthly) ingestion;
live Market Data Plane is the source of truth for forward cost evidence.
Added tests/test_execution_cost_download.py (mocked network, fail-closed
checksum test, day-range test) and a bookTicker path test in
tests/test_historical_dataset.py.
```

Real execution:

```text
Ran scripts/run_sprint7_execution_cost_download.py for real (live Binance
network) against ARBUSDT, OPUSDT, ADAUSDT, DOTUSDT, ETCUSDT, AVAXUSDT for
June 2023 (180 symbol-days). No errors, no OOM. Produced 4326 real
checksum-verified hourly spread rows in
data/research/binance_public/cost_pilot/pilot_202306_hourly_cost.csv.

Built a scoped bars/summary (6 symbols, June 2023, 4320 bars, 6 candidate
pairs) and ran scripts/run_sprint7_execution_cost_evidence.py with
--probe-binance-source scoped to this window.

Result: cost_gated_pass=true overall; 5 of 6 pairs pass (ARBUSDT/OPUSDT,
ARBUSDT/ETCUSDT, ARBUSDT/DOTUSDT, AVAXUSDT/DOTUSDT, DOTUSDT/ETCUSDT);
ADAUSDT/DOTUSDT correctly rejected (ADAUSDT median spread 3.52bps > 3.0bps
threshold).
```

Reviews:

```text
Market Data Agent reviewed the new download code + BOOK_TICKER enum addition:
PASSA, 1 P3 (non-blocking: normalize_symbol_archive_files has no explicit
guard against BOOK_TICKER misuse via the kline-oriented path, not exercised
by the actual code used).

QA Agent independently re-verified the result's genuineness: ran the focused
tests, manually recomputed ADAUSDT's median spread from the raw CSV (matched
3.52 exactly), manually verified SHA256 of a raw downloaded ZIP against its
.CHECKSUM file and the recorded source_checksum (matched), unzipped and
inspected real tick prices, checked git history for threshold tampering
(none found), and compared the full-36-month source_review
(complete_for_window=false) against the scoped pilot source_review
(complete_for_window=true) to confirm the probe is scope-sensitive and not
hardcoded to always pass. Found one non-blocking data-quality note: 12 of
4326 hourly rows are duplicates at day-boundary stitching (ADAUSDT +4,
DOTUSDT +2), not materially affecting reported medians. Verdict: PASSA,
result is genuine and must be communicated as scoped to June 2023 / 6 symbols
only, not generalized to Sprint 7/8 as a whole.
```

Verification:

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests -q
Result: passed, 190 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research scripts tests
Result: passed.
```

Status:

```text
At that point, BLOCKER-2026-06-30-S7-REAL-DATASET-GATE was downgraded from
ACTIVE/P1 to PARTIALLY RESOLVED/P2 with a 5-pair scope. This was superseded on
2026-07-02 by the expanded all-candidate June-2023 run: Sprint 8 may now open
for 31 cost-gated pairs. PROJECT_STATE, CURRENT_SPRINT, TASK_BOARD, BLOCKERS,
RISKS, TEST_MATRIX, HANDOFFS, DECISIONS (ADR-0007), and
reports/research_sprint_07.md were updated accordingly. Opening/scoping
Sprint 8 itself (objective, deliverables, tasks) remains separate planning
work pending user confirmation.
```

## 2026-07-01 (continuacao - fechamento TASK-007-09/TASK-007-10)

Governance audit:

```text
User asked to confirm/create the 12 project_control files. All 12 already
existed and were consistent with each other. No file was missing; audited
PROJECT_STATE, CURRENT_SPRINT, TASK_BOARD, AGENTS, OWNERSHIP, INTERFACES,
DECISIONS, RISKS, BLOCKERS, HANDOFFS, TEST_MATRIX, DAILY_LOG, RELEASE_CHECKLIST.
Confirmed the mandatory dispatch protocol (agent, sprint, task, contexto,
arquivos permitidos/proibidos, criterio de pronto, testes, handoff) going
forward.
```

User asked to complete Sprint 7:

```text
Found that TASK-007-10 work (src/research/execution_cost_evidence.py,
scripts/run_sprint7_execution_cost_evidence.py) had already been implemented
and run against the real Binance source after the last control-file update,
producing data/research/binance_public/normalized/
sprint7_binance_usdm_202306_202605_execution_cost_source_review.json and
_execution_cost_gate.json, not yet reflected in project_control.
```

PM verification before trusting the result:

```text
Independently queried the live Binance S3 endpoint
(s3-ap-northeast-1.amazonaws.com/data.binance.vision) via curl for BTCUSDT:
monthly bookTicker prefix returned KeyCount=24, MaxKeys=1000,
IsTruncated=false, last archive 2024-04; daily bookTicker prefix returned
KeyCount=640, MaxKeys=1000, IsTruncated=false, last archive 2024-03-30.
Confirmed the coverage gap is real and not a pagination artifact of
_fetch_s3_objects/parse_s3_list_objects (which do not handle
IsTruncated/NextContinuationToken).
```

Formal reviews dispatched in parallel (per governance protocol, no vague task):

```text
1. Market Data Agent review of TASK-007-09 (paths, checksum, funding as-of,
   sidecars, global mutable state). Result: PASSA, 2 P3 findings.
2. QA Agent review of TASK-007-09 (fail-closed: checksum mismatch, gaps,
   runner smoke, select_pairs integration). Result: PASSA, 2 P2 + 1 P3
   findings, no P1.
3. QA Agent independent re-review of TASK-007-10 (S3 pagination risk,
   no-default-approve on missing evidence). Result: PASSA, confirmed PM's
   verification, 1 P2 finding (pagination handling should be added as
   future hardening, harmless today).
```

Verification:

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_execution_cost_evidence.py tests/test_historical_dataset.py tests/test_pair_selection.py -q
Result: passed, 26 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests -q
Result: passed, 186 tests.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research/execution_cost_evidence.py tests/test_execution_cost_evidence.py scripts/run_sprint7_execution_cost_evidence.py
Result: passed.
```

Status:

```text
TASK-007-09 moved to DONE (100%). TASK-007-10 moved to DONE (100%) with a
definitive negative finding: Binance Public Data bookTicker coverage exists
for only 11 of 36 required months, identically for all 20 accepted symbols;
cost_gated_pass=false for all 41 candidate pairs, unconditionally.
Sprint 7 technical implementation is complete. Sprint 8 start remains blocked,
but the blocker changed from "evidence not yet produced" to "verified
evidence does not exist on this source for this window" - a policy decision
for the user/PM, not further execution work. Updated PROJECT_STATE,
CURRENT_SPRINT, TASK_BOARD, BLOCKERS, RISKS, TEST_MATRIX, HANDOFFS, and
reports/research_sprint_07.md accordingly. BLOCKER-2026-06-30-S7-REAL-DATASET-GATE
kept ACTIVE, reframed as a decision blocker.
```

## 2026-07-01

Sprint 7 TASK-007-09 historical loader continuation:

```text
User corrected the previous instruction: active project state is Sprint 7, not
Sprint 5. PM restored PROJECT_STATE.md, CURRENT_SPRINT.md, BLOCKERS.md, and
related control files to the Sprint 7 state before continuing.
```

Implementation:

```text
Updated src/research/historical_dataset.py so Binance ZIP CSV reading handles
headerless public-data CSVs without dropping the first data row.
Checksum parsing now accepts sha256sum-style binary filename markers such as
`*BTCUSDT-1h-2023-06.zip`.
Added tests for checksum parser/verifier, checksum mismatch before
normalization, headerless ZIPs, archive-plan normalization feeding select_pairs,
and local no-download runner smoke.
```

Verification:

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_historical_dataset.py tests/test_pair_selection.py --basetemp=pytest_temp_run_task00709_focus -o cache_dir=pytest_temp_run_task00709_focus/.pytest_cache
Result: passed, 21 tests, 1 pytest config warning for unknown asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests --basetemp=pytest_temp_run_sprint7_real_gate_all -o cache_dir=pytest_temp_run_sprint7_real_gate_all/.pytest_cache
Result: passed, 182 tests, 1 pytest config warning for unknown asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research/historical_dataset.py tests/test_historical_dataset.py scripts/run_sprint7_historical_dataset.py
Result: passed.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check .
Result: failed on pre-existing notebook lint issues in notebooks/01_pair_selection.ipynb
and notebooks/02_kalman_ou.ipynb. Scoped TASK-007-09 ruff passed, so notebook
cleanup is left out of this loader task.

UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_historical_dataset.py --symbols BTCUSDT --start-month 2023-06 --end-month-exclusive 2023-07 --dataset-version sprint7_real_smoke_202306_btcusdt --data-root /tmp/crypto_pair_trading_sprint7_real_smoke --correlation-window 2
Result: passed. Downloaded/checksumed real Binance Public Data for BTCUSDT
2023-06 across klines, markPriceKlines, indexPriceKlines, premiumIndexKlines,
and fundingRate. Normalized output contains 720 bars.
```

Status:

```text
TASK-007-09 moved to IN_REVIEW at 90%.
Market Data Agent and QA Agent review remain mandatory before DONE.
Real one-month smoke passed, but real 36 complete-month Binance USD-M dataset
execution remains pending and continues to block Sprint 8.
```

Sprint 7 real-dataset gate execution:

```text
User asked to do the remaining Sprint 7 work.

Full real dataset run completed:
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_historical_dataset.py --symbols BTCUSDT ETHUSDT BNBUSDT SOLUSDT XRPUSDT ADAUSDT DOGEUSDT AVAXUSDT LINKUSDT LTCUSDT BCHUSDT DOTUSDT TRXUSDT ETCUSDT UNIUSDT ATOMUSDT APTUSDT ARBUSDT OPUSDT SUIUSDT --start-month 2023-06 --end-month-exclusive 2026-06 --dataset-version sprint7_binance_usdm_202306_202605 --data-root data/research/binance_public --correlation-window 168 --download-workers 12

Artifacts:
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_summary.json

Result:
526080 normalized 1h bars, 20 accepted symbols, 0 rejected symbols, 41
statistical candidate pairs, and 149 rejected pairs.

Real research gate completed:
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/run_sprint7_research_gate.py --bars-csv data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv --summary-json data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_summary.json --output-json data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.json --output-csv data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.csv

Artifacts:
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.json
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.csv

Result:
41 candidate pairs evaluated; 41 statistical-only accepts; 0 statistical
rejects; cost_gated_pass=false because verified historical top-of-book/L2
execution-cost evidence is unavailable.
```

Implementation follow-up:

```text
Added scripts/run_sprint7_research_gate.py and an automated smoke test that
executes it against a synthetic normalized bars CSV.
Added dataset_version to future run_sprint7_historical_dataset.py summaries.
Added explicit cost_gate_reason and generated_at_utc to research gate JSON
output.
```

Verification:

```text
UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_historical_dataset.py tests/test_pair_selection.py --basetemp=pytest_temp_run_task00709_gate_focus -o cache_dir=pytest_temp_run_task00709_gate_focus/.pytest_cache
Result: passed, 22 tests, 1 pytest config warning for unknown asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests --basetemp=pytest_temp_run_sprint7_real_gate_all -o cache_dir=pytest_temp_run_sprint7_real_gate_all/.pytest_cache
Result: passed, 182 tests, 1 pytest config warning for unknown asyncio_mode.

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check src/research/historical_dataset.py tests/test_historical_dataset.py scripts/run_sprint7_historical_dataset.py scripts/run_sprint7_research_gate.py
Result: passed.
```

Status:

```text
TASK-007-09 remains IN_REVIEW and moved to 95%.
The dataset execution part of BLOCKER-2026-06-30-S7-REAL-DATASET-GATE is no
longer pending.
Sprint 8 remains blocked by cost-gated execution-cost evidence and mandatory
Market Data Agent + QA Agent review.
```

TASK-007-10 delegation:

```text
User instructed PM to send the remaining work.
PM opened TASK-007-10 - Produzir evidencia historica de custo de execucao.

Delegated agent: Market Data Agent.
Subagent nickname: Ptolemy.
Mandatory reviewers: QA Agent + PM Agent.
Status: IN_PROGRESS, 25%.

Scope:
- produce or disprove verified historical top-of-book/L2 execution-cost
  evidence for the 41 Sprint 7 statistical pairs;
- keep evidence incomplete/absent fail-closed;
- do not touch ledger, execution, live engine, or models.

Sprint 8 remains blocked until TASK-007-10 produces cost-gated evidence and
TASK-007-09 receives Market Data Agent + QA Agent review.
```

## 2026-06-30

Pre-Sprint 7 gate audit:

```text
PM Agent received instructions to validate Sprint 5 and Sprint 6 before opening
Sprint 7.
Existing focused gate tests passed:
UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_book_health.py tests/test_execution_features.py tests/test_slippage_estimator.py --basetemp=pytest_temp_run_s7_gate_precheck -o cache_dir=pytest_temp_run_s7_gate_precheck/.pytest_cache
Result: passed, 37 tests, 1 pytest config warning for asyncio_mode.
```

QA / Chaos audit:

```text
Gate blocked against the literal checklist because the codebase had book health
helpers but no explicit LocalOrderBook/BookBuilder applying snapshots and diffs,
and BookExecutionFeatures did not expose book_age_ms/in_sync required by the
BookFeatures contract.
```

Corrective actions:

```text
Created BLOCKER-2026-06-30-S5S6-GATE-LOCAL-BOOK.
Created TASK-031, TASK-032, and TASK-033.
Delegated TASK-031 to Market Data Agent.
Delegated TASK-032 to Execution / Risk Agent.
Sprint 7 remains blocked until TASK-033 revalidates the gate.
```

Sprint 5/6 gate correction closure:

```text
Market Data Agent implemented LocalOrderBook/BookBuilder with snapshot/diff,
sequence validation, old update discard, gap invalidation, zero-quantity level
removal, best bid/ask, book_age_ms, in_sync, stale detection, and empty-book
invalidity.
Execution / Risk Agent added explicit BookExecutionFeatures book_age_ms and
in_sync fields.
Focused gate checks passed: 47 tests.
Full suite passed: 140 tests.
Ruff passed globally.
QA / Chaos Testing Agent re-review returned PASSA with no P1/P2/P3 findings.
BLOCKER-2026-06-30-S5S6-GATE-LOCAL-BOOK closed.
TASK-031, TASK-032, and TASK-033 moved to DONE.
Sprint 7 opened in project control as Research base: pair selection, Kalman e OU.
```

Sprint 7 execution:

```text
TASK-007-01 historical dataset minimum was delegated to Quant Research Agent.
Market Data Agent requested changes for impossible historical bookTicker
coverage, ambiguous 36-month window, and missing funding carry formula.
PM corrected the dataset contract:
- canonical window is 2023-06-01 <= open_time < 2026-06-01;
- bookTicker is not mandatory; execution spread requires verified top-of-book/L2
  evidence and cost-gated PASS fails closed without it;
- funding carry formula is conservative absolute bps/day.
Market Data Agent re-review passed TASK-007-01 with no remaining P1/P2/P3.
TASK-007-01 moved to DONE.
TASK-007-02 pair_selection.py, TASK-007-03 stationarity.py, and TASK-007-04
Kalman Filter were delegated to Quant Research Agents with disjoint write sets.
Implementation agents hit usage limits, so PM Agent performed fallback
integration for the research core and added TASK-007-05 OU estimator.
Focused Sprint 7 research core verification passed:
pytest tests/test_pair_selection.py tests/test_stationarity.py tests/test_kalman.py tests/test_ou.py returned 28 passed.
Full suite verification passed: pytest tests returned 168 passed.
Ruff verification passed for src/research and Sprint 7 research tests.
TASK-007-02 through TASK-007-05 moved to IN_REVIEW.
```

Sprint 7 research core review closure:

```text
Backtest Agent requested fixes for rolling-correlation look-ahead and pair
selection execution-cost evidence. PM corrected rolling_correlation to shift(1),
made partial execution_cost_quality fail closed as INCOMPLETE, and stopped
fabricating p95/p99 spread from median-only evidence.
QA Agent requested a fix for OU continuous sigma when dt != 1. PM removed the
extra dt factor and added a non-unit-dt regression test.
Focused reviewed verification passed: 31 tests.
Full suite passed: 171 tests.
Ruff passed for src/research and Sprint 7 research tests.
Backtest Agent re-review returned PASSA.
QA Agent re-review returned PASSA.
TASK-007-02 through TASK-007-05 moved to DONE.
TASK-007-06 notebooks, TASK-007-07 test review, and TASK-007-08 report remain
pending before Sprint 7 can close.
```

Sprint 7 technical report closure:

```text
Created notebooks/01_pair_selection.ipynb and notebooks/02_kalman_ou.ipynb with
deterministic synthetic smoke examples.
Notebook code-cell execution check passed for both notebooks.
Final Sprint 7 report was updated with dataset contract, cleaning summary,
filters, module status, synthetic examples, verification, risks, and conclusion.
Documentation Agent requested one cleaning-summary fix; PM added it and
Documentation Agent re-review returned PASSA.
Quant Research Agent review passed TASK-007-07 test coverage.
TASK-007-06, TASK-007-07, and TASK-007-08 moved to DONE.
Technical implementation of Sprint 7 is complete, but Sprint 8 advancement gate
is NAO PASSA until the real 36 complete-month historical dataset is executed.
PROJECT_STATE marked blocked for Sprint 8.
```

Sprint 7 real-dataset gate continuation:

```text
User asked to continue.
PM opened TASK-007-09 to implement a Binance Public Data historical
loader/normalizer and runner. This task targets the active Sprint 8 blocker but
does not start Sprint 8.
```

## 2026-06-28

Initialized project management control plane for crypto futures pairs trading system.

Created:

```text
project_control/
tasks/sprint_01/
```

Notes:

```text
Repository appears empty and not initialized as git.
No implementation code has started.
Sprint 1 is ready for delegation.
```

Readiness reviews:

```text
Architect Agent: GO for TASK-001 with P1 architecture clarifications.
Ledger/Recovery Agent: GO for TASK-003 and TASK-005 with P1 reconciliation clarifications.
QA / Chaos Testing Agent: GO for Sprint 1 with P1 closure criteria added.
```

TASK-001:

```text
Architect Agent created docs/architecture.md.
PM review accepted scope and safety invariants.
TASK-001 moved to IN_REVIEW at 75%.
PM final review passed.
TASK-001 moved to DONE at 100%.
```

Updated PM instructions received:

```text
Control files normalized to required templates.
Sprint folders tasks/sprint_01 through tasks/sprint_28 created.
INTERFACES.md expanded with versioned contract skeletons.
TASK-002 state machine intake accepted and moved to IN_REVIEW at 75%.
```

TASK-003:

```text
Delegated to Ledger Agent.
TASK_BOARD and CURRENT_SPRINT moved TASK-003 to IN_PROGRESS at 25%.
Ledger Agent completed docs/event_contracts.md.
TASK-003 moved to IN_REVIEW at 75%.
```

TASK-004:

```text
Delegated to Execution / Risk Agent.
TASK_BOARD and CURRENT_SPRINT moved TASK-004 to IN_PROGRESS at 25%.
Execution / Risk Agent completed docs/risk_limits.md.
TASK-004 moved to IN_REVIEW at 75%.
Daily realized loss and drawdown thresholds remain live-readiness blockers, with live entries fail-closed until approved.
```

TASK-005:

```text
Delegated to Ledger Agent.
TASK_BOARD and CURRENT_SPRINT moved TASK-005 to IN_PROGRESS at 25%.
Ledger Agent completed docs/recovery_protocol.md.
TASK-005 moved to IN_REVIEW at 75%.
```

Sprint 1 reviews:

```text
Architect Agent passed TASK-002.
Architect Agent requested TASK-003 metadata cleanup; PM corrected task metadata and TEST_MATRIX, then accepted DONE.
QA / Chaos Testing Agent passed TASK-004 and TASK-005.
TASK-002, TASK-003, TASK-004, and TASK-005 moved to DONE.
```

Sprint 1 closure:

```text
reports/sprint_01_review.md created.
Sprint 1 gate passed.
PROJECT_STATE status moved to PRONTO.
Next recommended sprint: Sprint 2 - Ledger base with SQLite WAL.
```

Sprint 2 start:

```text
CURRENT_SPRINT moved to Sprint 2 - Ledger Base with SQLite WAL.
Created Sprint 2 task breakdown TASK-006 through TASK-010.
TASK-006 moved to IN_PROGRESS and prepared for Ledger Agent delegation.
No exchange, signal, live, or ML implementation is in scope.
```

TASK-006:

```text
Ledger Agent completed migrations/001_initial_schema.sql.
TASK-006 moved to IN_REVIEW at 75%.
Architect review requested.
Architect Agent returned CHANGES_REQUESTED.
Required fixes: enforce delta_fill = max(0, exchange_cum_qty - ledger_cum_qty) and make fills.exchange_order_id required.
Ohm corrected both findings and returned TASK-006 to IN_REVIEW.
PROJECT_STATE and CURRENT_SPRINT synchronized to IN_REVIEW at 90%.
Architect re-review passed with no P0/P1/P2 findings.
TASK-006 moved to DONE at 100%.
TASK-007 moved to IN_PROGRESS and prepared for Ledger Agent delegation.
Ledger Agent completed src/ledger/db.py and src/ledger/__init__.py.
TASK-007 moved to IN_REVIEW at 100%; QA review requested.
TASK-008 moved to IN_PROGRESS and delegated to Ledger Agent.
QA / Chaos Testing Agent passed TASK-007.
TASK-007 moved to DONE at 100%.
Ledger Agent completed src/ledger/models.py and updated exports.
TASK-008 moved to IN_REVIEW at 100%; Architect review requested.
Architect Agent passed TASK-008.
TASK-008 moved to DONE at 100%.
TASK-009 moved to IN_PROGRESS and delegated to Ledger Agent.
Ledger subagent for TASK-009 hit usage limit before producing files.
PM Agent took over the narrow EventStore task to keep Sprint 2 moving.
Created src/ledger/event_store.py and updated exports.
Focused EventStore checks passed.
TASK-009 moved to IN_REVIEW at 100%.
Architect Agent passed TASK-009.
QA / Chaos Testing Agent requested changes: EventStore accepted aggregate sequence gaps.
PM Agent fixed contiguous per-aggregate sequence validation in EventStore.append().
Focused sequence-gap checks passed.
TASK-009 moved back to IN_REVIEW for QA re-review.
QA / Chaos Testing Agent passed TASK-009 re-review.
TASK-009 moved to DONE at 100%.
TASK-010 moved to IN_PROGRESS and prepared for QA delegation.
QA / Chaos Testing Agent completed tests/test_event_store.py.
pytest tests/test_event_store.py passed with 7 tests.
Ledger/PM review passed TASK-010.
TASK-010 moved to DONE at 100%.
Sprint 2 gate passed.
```

Sprint 3 start:

```text
CURRENT_SPRINT moved to Sprint 3 - Idempotency, clientOrderId, and Cumulative Reconciliation.
Created Sprint 3 task breakdown TASK-011 through TASK-015.
TASK-011 moved to IN_PROGRESS and prepared for Execution / Risk Agent delegation.
No exchange connector, live router, recovery boot, market data, signal, or ML work is in scope.
```

Sprint 3 implementation wave:

```text
Execution / Risk Agent completed TASK-011 clientOrderId implementation.
Ledger Agent completed TASK-012 idempotency helper implementation.
Ledger Agent completed TASK-013 cumulative fill reconciliation implementation.
Local verification passed: pytest tests/test_client_order_id.py tests/test_idempotency.py tests/test_cumulative_reconciliation.py tests/test_event_store.py returned 43 passed.
TASK-011, TASK-012, and TASK-013 moved to IN_REVIEW at 80%.
Architect review requested for TASK-011; QA review requested for TASK-012 and TASK-013.
TASK-014 remains BACKLOG until clientOrderId and idempotency reviews pass.
```

Sprint 3 reviews:

```text
Architect Agent passed TASK-011 with residual note to prefer build_client_order_id when canonical_id persistence matters.
QA / Chaos Testing Agent passed TASK-012 and TASK-013 with no blocking findings.
TASK-011, TASK-012, and TASK-013 moved to DONE at 100%.
TASK-014 moved to IN_PROGRESS at 25% and prepared for Execution / Risk Agent delegation.
```

TASK-014:

```text
Execution / Risk Agent completed ACK_UNKNOWN retry guard implementation.
Created src/execution/ack_guard.py and tests/test_ack_guard.py.
Local verification passed: pytest tests/test_ack_guard.py returned 16 passed.
Sprint verification passed: pytest tests/test_client_order_id.py tests/test_idempotency.py tests/test_cumulative_reconciliation.py tests/test_ack_guard.py tests/test_event_store.py returned 59 passed.
TASK-014 moved to IN_REVIEW at 80%.
Ledger Agent and QA / Chaos Testing Agent review requested.
```

TASK-014 review correction:

```text
Ledger Agent passed TASK-014.
QA / Chaos Testing Agent requested change: retry resolution matched only client_order_id and ignored venue/account/trade/leg scope.
PM Agent fixed retry matching to require same client_order_id and same venue/account/trade/leg scope.
Added regression test for resolved state from wrong scope failing closed.
TASK-014 remains IN_REVIEW at 80% for QA re-review.
```

TASK-014 closure:

```text
QA / Chaos Testing Agent re-review passed TASK-014.
TASK-014 moved to DONE at 100%.
TASK-015 moved to IN_PROGRESS at 25% and prepared for QA / Chaos Testing Agent delegation.
```

TASK-015 PM correction:

```text
PM review found ORDER_INTENT_CREATED idempotency keys did not label attempt versus slice_id, creating a possible collision between attempt="slice-1" and slice_id="slice-1".
Updated src/ledger/idempotency.py so ORDER_INTENT_CREATED keys use attempt-* and slice-* domains.
Added regression coverage for attempt/slice domain separation and updated Sprint 3 integration expectations.
```

TASK-015 review and Sprint 3 closure:

```text
Ledger Agent passed TASK-015.
Non-blocking task-file status nit fixed by PM.
TASK-015 moved to DONE at 100%.
Sprint 3 gate passed.
reports/sprint_03_review.md created.
Next recommended sprint: Sprint 4 - recovery/order lifecycle failure routes.
```

Environment setup note:

```text
User reported project environment setup completed: uv/Python 3.12, dependency lock, Taskfile, Ruff, Pyright, pre-commit, pytest temp/cache configuration, README, GitHub Actions CI, MkDocs, Docker Compose, Dockerfile, .env.example, and 64 passing tests.
PM accepted this as Sprint 4 operational context.
```

Sprint 4 start:

```text
CURRENT_SPRINT moved to Sprint 4 - Recovery and Order Lifecycle Failure Routes.
Created Sprint 4 task breakdown TASK-016 through TASK-020.
TASK-016 moved to IN_PROGRESS and prepared for Ledger Agent delegation.
No exchange connector, live router, actual send/cancel/hedge side effect, market data implementation, signal, ML, or real trading endpoint is in scope.
```

TASK-016:

```text
Ledger Agent subagent hit usage limit before delivering TASK-016.
PM Agent took over the narrow unresolved ORDER_SENT scanner to keep Sprint 4 moving.
Created src/recovery/order_state.py, src/recovery/__init__.py, and tests/test_recovery_order_state.py.
Focused verification passed: pytest tests/test_recovery_order_state.py --basetemp=pytest_temp_run_recovery -o cache_dir=pytest_temp_run_recovery/.pytest_cache returned 9 passed.
Full verification passed with isolated temp: pytest tests --basetemp=pytest_temp_run -o cache_dir=pytest_temp_run/.pytest_cache returned 73 passed.
TASK-016 moved to IN_REVIEW at 80%.
TASK-017 moved to IN_PROGRESS at 25%.
```

TASK-017:

```text
PM Agent implemented recovery boot gate helper in src/recovery/recovery_boot.py.
Created tests/test_recovery_boot.py and exported recovery boot helpers from src/recovery/__init__.py.
Focused verification passed: pytest tests/test_recovery_boot.py --basetemp=pytest_temp_run_boot -o cache_dir=pytest_temp_run_boot/.pytest_cache returned 8 passed.
Sprint 4 recovery verification passed: pytest tests/test_recovery_order_state.py tests/test_recovery_boot.py --basetemp=pytest_temp_run_s4a -o cache_dir=pytest_temp_run_s4a/.pytest_cache returned 17 passed.
Full verification passed: pytest tests --basetemp=pytest_temp_run_all2 -o cache_dir=pytest_temp_run_all2/.pytest_cache returned 81 passed.
TASK-017 moved to IN_REVIEW at 80%.
TASK-018 moved to IN_PROGRESS at 25%.
```

TASK-018:

```text
PM Agent implemented partial-fill route helper in src/recovery/partial_fill_route.py.
Updated src/recovery/__init__.py and created tests/test_partial_fill_route.py.
Focused verification passed: pytest tests/test_partial_fill_route.py --basetemp=pytest_temp_run_partial -o cache_dir=pytest_temp_run_partial/.pytest_cache returned 9 passed.
Sprint 4 helper verification passed: pytest tests/test_recovery_order_state.py tests/test_recovery_boot.py tests/test_partial_fill_route.py --basetemp=pytest_temp_run_s4b -o cache_dir=pytest_temp_run_s4b/.pytest_cache returned 26 passed.
Full verification passed: pytest tests --basetemp=pytest_temp_run_all3 -o cache_dir=pytest_temp_run_all3/.pytest_cache returned 90 passed.
TASK-018 moved to IN_REVIEW at 80%.
TASK-019 moved to IN_PROGRESS at 25%.
```

TASK-019:

```text
PM Agent added Sprint 4 chaos/integration tests for crash-after-ORDER_SENT, recovery boot resume gating, and partial-fill route behavior.
Updated TEST_MATRIX Sprint 4 rows to passed.
Sprint 4 focused verification passed: pytest tests/test_recovery_order_state.py tests/test_recovery_boot.py tests/test_partial_fill_route.py --basetemp=pytest_temp_run_s4d -o cache_dir=pytest_temp_run_s4d/.pytest_cache returned 29 passed.
Full verification passed: pytest tests --basetemp=pytest_temp_run_all5 -o cache_dir=pytest_temp_run_all5/.pytest_cache returned 93 passed.
Ruff verification passed with local uv cache.
Pyright could not run because Node failed before type checking with EPERM on lstat C:\Users\arthu.
TASK-019 moved to IN_REVIEW at 80%.
TASK-020 moved to IN_PROGRESS at 25%.
```

Sprint 4 closure:

```text
PM fallback review passed TASK-016, TASK-017, TASK-018, and TASK-019 because subagent usage limit prevented normal reviewer delegation.
TASK-016 through TASK-020 moved to DONE at 100%.
Sprint 4 gate passed.
reports/sprint_04_review.md created.
Next recommended sprint: Sprint 5 - Market Data Book Health and Gap Detection.
```

Sprint 5 start:

```text
CURRENT_SPRINT moved to Sprint 5 - Market Data Book Health and Gap Detection.
Created Sprint 5 task breakdown TASK-021 through TASK-025.
TASK-021 moved to IN_PROGRESS at 25%.
No live WebSocket, exchange REST connector, order routing, signal, ML, or real trading endpoint is in scope.
```

Sprint 5 implementation and closure:

```text
Market Data Agent implemented src/market_data/book_health.py and tests/test_book_health.py.
TASK-021 through TASK-023 moved to IN_REVIEW at 80%.
Execution / Risk Agent passed TASK-021/TASK-023 review with no blocking findings.
QA / Chaos Testing Agent passed TASK-022/TASK-024 review with no blocking findings.
PM added a non-blocking regression for snapshot_complete=True with missing snapshot_last_sequence requiring resync.
Focused verification passed: pytest tests/test_book_health.py --basetemp=pytest_temp_run_s5_gate -o cache_dir=pytest_temp_run_s5_gate/.pytest_cache returned 20 passed.
Full verification passed: pytest tests --basetemp=pytest_temp_run_s5_gate_all -o cache_dir=pytest_temp_run_s5_gate_all/.pytest_cache returned 113 passed.
Ruff verification passed: ruff check src\market_data tests\test_book_health.py.
TASK-021 through TASK-025 moved to DONE at 100%.
Sprint 5 gate passed.
reports/sprint_05_review.md created.
```

Sprint 6 start:

```text
CURRENT_SPRINT moved to Sprint 6 - Execution Features and Slippage.
Created Sprint 6 task breakdown TASK-026 through TASK-030.
No full Execution Risk Gate, order router, live market-data ingestion, signal, Kalman/OU, ML, backtest, paper trading, or real trading endpoint is in scope.
```

Sprint 6 implementation and closure:

```text
Execution Features / Slippage implementer created src/features/execution_features.py, src/execution/slippage_estimator.py, src/market_data/feature_cache.py, and focused tests.
Initial Sprint 6 verification passed with 125 total tests.
PM review added regressions for zero-quantity book levels.
Execution / Risk Agent passed TASK-026/TASK-029 review with no blocking findings.
Market Data Agent passed TASK-027/TASK-028 review with no blocking findings.
QA / Chaos Testing Agent found P1 gaps for malformed book levels and invalid slippage requests.
PM corrected P1 findings so malformed book levels fail closed and invalid slippage requests return INVALID_REQUEST.
Focused verification passed: pytest tests/test_execution_features.py --basetemp=pytest_temp_run_s6_p1_features -o cache_dir=pytest_temp_run_s6_p1_features/.pytest_cache returned 10 passed.
Focused verification passed: pytest tests/test_slippage_estimator.py --basetemp=pytest_temp_run_s6_p1_slippage -o cache_dir=pytest_temp_run_s6_p1_slippage/.pytest_cache returned 7 passed.
Full verification passed: pytest tests --basetemp=pytest_temp_run_s6_p1_all -o cache_dir=pytest_temp_run_s6_p1_all/.pytest_cache returned 130 passed.
Ruff verification passed for Sprint 6 touched code and tests.
QA / Chaos Testing Agent re-review passed Sprint 6 with no remaining blockers.
TASK-026 through TASK-030 moved to DONE at 100%.
Sprint 6 gate passed.
reports/sprint_06_review.md created.
Sprint 7 was not started; explicit user confirmation is required.
```

2026-07-07 - TASK-ALT-005 opened:

```text
PM Agent opened ADR-0023 and docs/pre_registers/TASK-ALT-005.md.
Scope: validate only funding_price_divergence in genuine new OOS.
Old 2023-06/2026-05 dataset may be used only as causal 90d context, not
as decision evidence.
Lightweight availability probe completed with escalated network after a
transient DNS failure inside sandbox: 20 symbols x 5 monthly families x
2026-06 = 100/100 .CHECKSUM sidecars found, no ZIPs downloaded.
TASK-ALT-005 marked READY; implementation/download/diagnostic not run yet.
No Execution, Ledger, Recovery, ML, live, SignalIntent, or order-routing
files touched.
```

2026-07-07 - TASK-ALT-005 runner prepared, real download deferred:

```text
PM Agent implemented scripts/diagnostic_alt_funding_divergence_new_oos.py
and tests/test_alt_funding_divergence_new_oos.py.
Focused verification:
PYTHONPATH=. UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_alt_funding_divergence_new_oos.py tests/test_info_content.py
Result: 18 passed, 1 warning.
UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check scripts/diagnostic_alt_funding_divergence_new_oos.py tests/test_alt_funding_divergence_new_oos.py
Result: All checks passed.
git diff --check
Result: passed.
User requested no download now: "vou fazer o download e continuar depois".
TASK-ALT-005 remains IN_PROGRESS at 60%; real 2026-06 download,
normalization, data gate, rho diagnostic, report, JSON, and final control
updates remain pending.
```

2026-07-07 - TASK-ALT-005 real execution completed, NAO_PROMOVE (sign reversed):

```text
User said "continue" in a follow-up session. Ran the exact deferred
command from docs/pre_registers/TASK-ALT-005.md:
PYTHONPATH=. UV_CACHE_DIR=.uv-cache uv run --offline python scripts/diagnostic_alt_funding_divergence_new_oos.py --start-month 2026-06 --end-month-exclusive 2026-07 --dataset-version sprint_alt_funding_divergence_202606 --download-workers 4
No code changed for this run -- runner/tests already implemented and
verified in the prior entry.
Downloaded 100 monthly archives (20 symbols x 5 families: klines,
markPriceKlines, indexPriceKlines, premiumIndexKlines, fundingRate) for
2026-06 only, all SHA256 checksum-verified. Normalized to
sprint_alt_funding_divergence_202606_bars.csv.gz.
Data gate: PASS (20/20 symbols, 5/5 families, coverage >=99%, no
duplicates, full_sample_n=13920, above the 10000 floor).
Information result: rho=-0.118324 (n=13920, single complete month) --
sign REVERSED vs the 3 original sub-periods (all positive, 0.0230 to
0.0276), magnitude ~4x the original full-sample rho.
Decision: NAO_PROMOVE, applied strictly per the pre-registered rule
(rho>=0.03 AND positive) -- no threshold adjustment, no new feature, no
second month tested after seeing this result.
funding_price_divergence closes definitively: SEM_INFORMACAO in the
original window (TASK-ALT-001) and NAO_PROMOVE in the new OOS
(TASK-ALT-005). Family G has no remaining open threads.
Updated project_control/DECISIONS.md (ADR-0023 addendum),
docs/pre_registers/TASK-ALT-005.md (status DONE), TASK_BOARD.md,
CURRENT_SPRINT.md, PROJECT_STATE.md, HANDOFFS.md, RISKS.md,
TEST_MATRIX.md.
Verification: full suite 431 tests passed, ruff clean (src tests
scripts docs).
No Execution, Ledger, Recovery, ML, live, SignalIntent, or
order-routing files touched.
```

2026-07-07 - TASK-ALT-006 pre-registered, execution blocked (data-mining risk flagged):

```text
User asked "oq agora?" after TASK-ALT-005 closed. Chose to keep
exploring Family J's regime information via a different operational
mechanism, rather than reconsidering Order Flow or closing the phase.
Decomposed TASK-ALT-004's already-closed result: the 1187 EXCLUDED
high-vol trades carried +13800.78bps net in isolation (more than the
strategy's entire original +7690.14bps profit); the 2758 KEPT
low/mid-vol trades are net -6110.64bps in isolation. TSREV's edge is
concentrated entirely inside the high-volatility regime.
Flagged explicitly: the natural next hypothesis ("keep only high-vol
entries") was built directly from seeing this number on the
2025-06/2026-05 window already analyzed multiple times -- the most
direct data-mining risk this session (more direct than the Payoff
Engineering SHORT-only lead or funding_price_divergence).
Asked user how to handle it; user chose to pre-register the exact
inverse filter now (docs/pre_registers/TASK-ALT-006.md, ADR-0024:
realized_vol_168h[t] > causal 67th percentile, same feature/window as
TASK-ALT-004, same TSREV-001 gate structure) but BLOCK execution until
genuinely new OOS data exists -- same discipline as TASK-PAYOFF-002.
Operational resume trigger: >=750 new resolved TSREV Family A 24h
trades (all vol levels) past 2026-05-31, estimated ~2.3 months given
the historical ~30.08% high-vol ratio (yields ~226 high-vol trades,
margin over the 200-trade gate floor). TASK-ALT-005's already-
downloaded 2026-06 month is reusable without a new download once the
window grows.
Updated project_control/DECISIONS.md (ADR-0024), TASK_BOARD.md,
CURRENT_SPRINT.md, PROJECT_STATE.md, HANDOFFS.md, RISKS.md.
No code written, no download, no execution -- pre-registration only.
No Execution, Ledger, Recovery, ML, live, SignalIntent, or
order-routing files touched.
```

2026-07-08 - TASK-ALT-007 (Familia H) reconnaissance + implementation, download interrupted mid-run:

```text
With TASK-ALT-006 blocked on calendar time, user authorized a
cost/scoping reconnaissance of Family H (Order Flow) -- last original
Research Phase II family, deferred since ADR-0019 for cost.
Real S3 listing probes against data.binance.vision found `bookDepth`
(percentage-from-mid-price aggregated depth, event-sampled), a
DIFFERENT family from `bookTicker` (the 17.98GB/month, gapped-since-
2024-04 source used in Sprint 7/9/10). Confirmed: continuous coverage
2023-01 through at least 2026-06 for all 20 symbols, ~432-515KB/day/
symbol, ~10.2GB estimated for the full 3-year window -- cheaper than
one month of bookTicker.
User approved pre-registering TASK-ALT-007 (docs/pre_registers/TASK-ALT-007.md,
ADR-0025): 5 features (book_imbalance_1pct, book_imbalance_5pct,
depth_concentration, depth_change_24h, imbalance_price_divergence),
same methodology/threshold/sub-periods/24h horizon as G/F/J -- not
re-decided per family.
Implemented scripts/download_alt_book_depth.py (dedicated daily
downloader, reuses verify_checksum_file unchanged, memory-safe per
symbol) and scripts/diagnostic_alt_order_flow.py (reuses
info_content.py unchanged). Smoke test (BTCUSDT, 3 days) validated the
full pipeline before the real download started. Added
tests/test_download_alt_book_depth.py (9 tests). Full suite 438
passed, ruff clean.
Started the real ~10.2GB download; SESSION DROPPED mid-run (not a code
error) during the 3rd symbol (ARBUSDT). State on disk: ADAUSDT and
APTUSDT complete (~31.7M event rows each -> ~26,250-26,274 hourly
rows), ARBUSDT partial, ~1.4GB cached under
data/research/binance_public/cost_pilot/raw/book_depth/ (gitignored,
not lost). The downloader is idempotent (skips files already on disk),
so resuming should pick up exactly where it stopped.
No normalized output CSV exists yet (written only after all 20 symbols
finish) and the diagnostic has not run -- no rho, no
TEM_INFORMACAO/SEM_INFORMACAO verdict for any of the 5 features yet.
Updated project_control/DECISIONS.md (ADR-0025), TASK_BOARD.md,
CURRENT_SPRINT.md, PROJECT_STATE.md, HANDOFFS.md, RISKS.md to reflect
the interrupted, in-progress state honestly (not as if it finished).
Next step already locked, just needs to run:
  UV_CACHE_DIR=.uv-cache uv run --offline python scripts/download_alt_book_depth.py
  UV_CACHE_DIR=.uv-cache uv run --offline python scripts/diagnostic_alt_order_flow.py
No Execution, Ledger, Recovery, ML, live, SignalIntent, or
order-routing files touched.
```

2026-07-08 - TASK-ALT-007 completed: real bug fixed, real network failures handled, closed sem informacao:

```text
Resumed the bookDepth download. C: drive filled up completely during
OPUSDT's download (14th of 20 symbols) -- found a REAL bug: the
original exception handling (`except Exception: return None`) treated
ANY error, including a local disk-write failure, identically to a
genuine 404 (day absent). This silently corrupted OPUSDT (5.45M of
~31.7M expected event rows, no visible error).
Fixed: replaced the catch-all with `except HTTPError as exc: if
exc.code == 404: return None` in download_alt_book_depth.py -- only a
confirmed 404 is treated as absent, everything else now propagates.
Applied the identical fix to download_alt_open_interest.py (same
latent bug, that task had already succeeded before and did not need
re-running).
Moved the book_depth raw cache (~6.6GB) from C: (0.01GB free) to
D:/CryptoPairTrading/book_depth_raw, same precedent as bookTicker's
raw cache in this project. Deleted corrupted OPUSDT and incomplete
SOLUSDT, re-downloaded both from scratch with the fixed code --
confirmed correct counts afterward (~31.7M event rows each).
Two genuine ConnectionResetError ([WinError 10054]) transient network
failures interrupted the download after the disk-full fix (not a code
bug). Added retry-with-backoff (4 attempts, URLError specifically) to
_fetch_to_file in both downloaders. Download completed on next resume.
Real download completed: 20/20 symbols, 524,878 hourly rows,
checksum-verified. Ran scripts/diagnostic_alt_order_flow.py.
Result: NONE of the 5 features (book_imbalance_1pct,
book_imbalance_5pct, depth_concentration, depth_change_24h,
imbalance_price_divergence) meet the 0.03 threshold. book_imbalance_1pct
and depth_concentration repeat the DECAYING pattern from Family F's
oi_delta/oi_acceleration. imbalance_price_divergence is the closest
near-miss (rho=0.0208, 0.0092 short) and the ONLY pattern in the whole
Research Phase II with a GROWING trajectory across the 3 sub-periods
(0.0131 -> 0.0215 -> 0.0236) -- flagged as a candidate for a future
new-OOS validation, not a retest.
This closes the last originally-planned Research Phase II family (F,
G, H, J all executed with real data; I remains formally blocked).
Updated project_control/TASK_BOARD.md, CURRENT_SPRINT.md,
PROJECT_STATE.md, HANDOFFS.md, RISKS.md to reflect the final result.
Verification: full suite 438 tests passed, ruff clean (src tests
scripts docs).
No Execution, Ledger, Recovery, ML, live, SignalIntent, or
order-routing files touched.
```
