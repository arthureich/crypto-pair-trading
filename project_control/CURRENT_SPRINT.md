# CURRENT_SPRINT

Last updated: 2026-07-08

## Workstream atual: Research Phase II -- TASK-ALT-007 (Familia H, Order Flow) IN_PROGRESS, download real interrompido (ADR-0025)

Com `TASK-ALT-006` bloqueada por calendario, o usuario autorizou uma
reconnaissance de custo de Familia H (Order Flow) -- escopo limitado,
sem compromisso de download grande a priori.

**Achado que mudou o calculo:** a familia `bookDepth` (profundidade
agregada por faixa % de distancia do mid-price, amostrada por evento)
tem cobertura CONTINUA desde 2023-01 ate pelo menos 2026-06 para os 20
symbols -- sem o gap que o `bookTicker` tem desde 2024-04 (achado do
Sprint 7/TASK-007-10). Tamanho estimado: **~10,2GB para os 3 anos
inteiros**, menor que os 17,98GB que o `bookTicker` custou para UM
UNICO MES. Isso mudou a viabilidade de Familia H de "cara demais" para
"acionavel agora."

Usuario aprovou pre-registrar `TASK-ALT-007` (`docs/pre_registers/TASK-ALT-007.md`,
ADR-0025): 5 features de book depth formalizadas (book_imbalance_1pct,
book_imbalance_5pct, depth_concentration, depth_change_24h,
imbalance_price_divergence), mesma metodologia info-content (Spearman +
3 subperiodos + limiar 0,03) e mesmo horizonte de 24h ja usados em
G/F/J -- reusados por consistencia, nao re-escolhidos.

`scripts/download_alt_book_depth.py` (downloader dedicado para
arquivos diarios, reusa `verify_checksum_file` sem modificacao,
memory-safe symbol-a-symbol) e `scripts/diagnostic_alt_order_flow.py`
implementados. Smoke test em escopo minimo (1 symbol, 3 dias) validou
o pipeline completo antes do download real. 9 testes novos
(`tests/test_download_alt_book_depth.py`). Ruff limpo, suite completa
438 testes.

**Download real EM ANDAMENTO, interrompido por queda de sessao:** 2 de
20 symbols completos (ADAUSDT, APTUSDT), ARBUSDT parcial, ~1,4GB ja em
cache local (`data/research/binance_public/cost_pilot/raw/book_depth/`,
nao versionado -- gitignored por design, mas reutilizavel: arquivos ja
no disco nao sao re-baixados ao retomar, ja que
`_download_and_parse_one_day` checa `archive_path.exists()` antes de
buscar).

**Proximo passo (ja travado, so precisa rodar):**

```text
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/download_alt_book_depth.py
UV_CACHE_DIR=.uv-cache uv run --offline python scripts/diagnostic_alt_order_flow.py
```

O primeiro comando e idempotente (pula arquivos ja em disco, deve ser
rapido para ADAUSDT/APTUSDT e retomar ARBUSDT de onde parou); o
segundo roda o diagnostico de conteudo informacional sobre o dataset
normalizado resultante. Nenhum resultado real de `TASK-ALT-007` existe
ainda -- nao ha `rho` calculado, nao ha veredito de TEM_INFORMACAO/
SEM_INFORMACAO.

## Workstream anterior: Research Phase II -- TASK-ALT-006 pre-registrada, execucao BLOCKED aguardando novo OOS (ADR-0024)

Apos `TASK-ALT-005` fechar (Familia G sem pistas abertas), o usuario
decidiu explorar outro uso operacional da informacao de regime de
Familia J, em vez de reconsiderar Order Flow ou encerrar a fase.

Decompondo o resultado ja fechado de `TASK-ALT-004` (bloqueio de
alta-vol, NAO_PASSA): as 1.187 trades EXCLUIDAS (alta-vol) tinham net
+13.800,78bps isoladamente -- mais que o lucro total original da TSREV
(+7.690,14bps). As 2.758 trades MANTIDAS (baixa/media vol) sao net
**-6.110,64bps isoladamente**. O edge da TSREV esta inteiramente
concentrado no regime de alta volatilidade.

Isso motiva a hipotese oposta -- manter SO as entradas de alta-vol --
mas essa hipotese foi construida DIRETAMENTE a partir de ter visto o
resultado de TASK-ALT-004 no periodo 2025-06/2026-05. Testar isso no
mesmo periodo nao teria valor probatorio. O usuario escolheu: travar o
desenho agora, bloquear a execucao ate existir dado genuinamente novo
(mesma disciplina de `TASK-PAYOFF-002`).

`TASK-ALT-006` (`docs/pre_registers/TASK-ALT-006.md`, ADR-0024): TSREV
Family A 24h restrita a `realized_vol_168h[t] > percentil causal 67%`
(filtro EXATAMENTE inverso de TASK-ALT-004), mesmo gate estrutural da
TASK-TSREV-001 (net PF>1,05 E net PnL>0 E DD<=baseline recalculado E
trade_count>=200 pos-filtro). Gatilho operacional: >=750 trades TSREV
totais novas resolvidas (~2,3 meses estimados, ~226 trades de alta-vol
esperadas). `TASK-ALT-005` ja baixou/normalizou 2026-06 completo
(`sprint_alt_funding_divergence_202606_bars.csv.gz`), reutilizavel sem
novo download quando a janela crescer.

**`TASK-ALT-006` esta BLOCKED** -- nenhum codigo, nenhuma execucao ate
o gatilho ser atingido. Sizing continuo por vol (ideia relacionada, ja
mencionada mas nao pre-registrada) permanece como candidato futuro
distinto, nao aberto por esta ADR.

## Workstream anterior: Research Phase II -- TASK-ALT-005 FECHADA, NAO_PROMOVE (ADR-0023 addendum); Familia G sem pistas abertas

`TASK-ALT-005` validou a unica pista remanescente da Family G
(`funding_price_divergence`) em dado genuinamente novo, per a
disciplina ja fixada (2023-06/2026-05 apenas como contexto causal, novo
OOS decisivo a partir de 2026-06-01).

Execucao real completada em 2026-07-07:

```text
PYTHONPATH=. UV_CACHE_DIR=.uv-cache uv run --offline python scripts/diagnostic_alt_funding_divergence_new_oos.py --start-month 2026-06 --end-month-exclusive 2026-07 --dataset-version sprint_alt_funding_divergence_202606 --download-workers 4

100 arquivos mensais baixados (20 symbols x 5 familias), checksum
SHA256 verificado em cada um. data_gate=PASS, full_sample_n=13.920.
rho (novo OOS, 2026-06)=-0,118324.
Decisao: NAO_PROMOVE.
```

**Resultado: sinal invertido, nao apenas ausente.** Os 3 subperiodos
originais de `TASK-ALT-001` eram todos positivos e estaveis (+0,0276,
+0,0230, +0,0239). No novo OOS o rho e -0,118324 -- sinal trocado,
magnitude ~4x maior. Per a regra pre-registrada (rho>=0,03 E positivo),
a decisao e NAO_PROMOVE, aplicada sem ajustar limiar ou testar um
segundo mes.

**`funding_price_divergence` fecha definitivamente.** Familia G
(Funding Structure) nao tem mais nenhuma pista aberta -- SEM_INFORMACAO
no periodo original (TASK-ALT-001) e NAO_PROMOVE no novo OOS
(TASK-ALT-005). Ver `reports/alt_info_funding_divergence_new_oos.md`.

Verificacao: suite completa 431 testes, ruff limpo (nenhum codigo novo
alterado nesta execucao -- apenas rodou o runner ja implementado e
testado na sessao anterior).

**Estado atual da Research Phase II:** G e F fecharam sem informacao
(incluindo o near-miss de G, agora tambem fechado); J encontrou
informacao real de regime/volatilidade, mas seu primeiro uso
operacional (TASK-ALT-004) nao melhorou o TSREV. Pendencias: Familia H
adiada/cara; Familia I BLOQUEADA por falta de fonte historica;
PAYOFF-002 bloqueada aguardando dados novos. Nenhuma nova task desta
fase esta pre-aprovada -- decisao de proximo passo pertence ao usuario.

## Workstream anterior: Research Phase II -- TASK-ALT-004 FECHADA NAO_PASSA (ADR-0022)

`TASK-ALT-004` (regime-conditioning sobre TSREV 24h, DONE): follow-up da
Family J, feasibility only. Filtro pre-registrado: bloquear entradas da
TSREV Family A 24h quando `realized_vol_168h[t]` esta acima do percentil
causal 67% da propria historia 90d do symbol; missing regime bloqueia;
trades remanescentes sao renormalizadas por inverse-vol.

Resultado real (`reports/regime_conditioned_tsrev_feasibility.md`):
**NAO_PASSA**. O filtro bloqueou 1.187 de 3.946 trades OOS e manteve
2.758 resolvidas, mas piorou a economia:

```text
Original TSREV 24h OOS:        PF 1,0143; net +7.690,14bps; DD 65.719,66bps
Regime-filtered TSREV 24h OOS: PF 0,9822; net -6.110,64bps; DD 61.748,50bps
Buy-and-hold DD baseline:      11.003,94bps
```

Decisao: variante encerrada. A informacao de regime existe, mas este
filtro simples de alto-vol nao salva TSREV nem merece novo-OOS proprio.

**Estado atual da Research Phase II:** G e F fecharam sem informacao;
J encontrou informacao de regime; o primeiro uso operacional minimo de J
(TASK-ALT-004) falhou. Pendencias: near-miss de
`funding_price_divergence`, Familia H adiada/cara, Familia I BLOQUEADA,
PAYOFF-002 bloqueada aguardando dados novos.

## Workstream anterior: Research Phase II -- Familia J FECHADA com informacao de regime (ADR-0021)

`TASK-ALT-003` (Familia J, Regime Detection, DONE): diagnostico de
contexto/risco, nao alpha direcional. Target pre-registrado:
`future_abs_return_24h = abs(log_price[t+24h] - log_price[t])`, para medir
risco/volatilidade futura, nao lado long/short.

Seis features causais OHLCV/contexto foram testadas no dataset Sprint 7 ja
normalizado, sem novo download: `realized_vol_24h`,
`realized_vol_168h`, `trend_intensity_168h`, `volume_shock_24h`,
`market_dispersion_24h`, `market_abs_return_24h`.

Resultado real (`reports/alt_info_regime_detection_diagnostic.md`): **as
6 features cumprem o criterio `TEM_INFORMACAO`** contra retorno absoluto
futuro de 24h. Mais fortes: `realized_vol_168h` rho=0,3009 e
`realized_vol_24h` rho=0,2927; todas mantem sinal positivo nos 3
subperiodos. Interpretacao: informacao robusta de volatilidade/regime
(volatility clustering/contexto de stress), nao edge direcional.

**Estado atual da Research Phase II:** G e F fecharam sem informacao
direcional/alternativa; J encontrou informacao de regime. Pendencias:
(1) decidir se abre uma task futura separada para uso operacional de regime
como camada de condicionamento; (2) near-miss de
`funding_price_divergence` como candidato separado; (3) Familia H continua
adiada/cara; (4) Familia I continua BLOQUEADA por falta de fonte historica.

## Workstream anterior: Research Phase II -- Familias G e F ambas FECHADAS sem informacao (ADR-0019/0020); J e near-miss de G pendentes

`TASK-ALT-002` (Familia F, Open Interest, DONE): novo download real e
pequeno (~21.920 arquivos diarios, ~260MB, checksum SHA256 verificado
em cada um) via a familia `metrics` do bucket publico da Binance --
Open Interest + long/short ratios em 5min, resample memory-safe para 1h.
Resultado: `data/research/binance_public/normalized/sprint_alt_open_interest_202306_202605.csv.gz`
(525.784 linhas, 20 symbols).

5 features formalizadas (`oi_delta`, `oi_volume_ratio`, `oi_percentile`,
`oi_acceleration`, `oi_price_divergence`), mesma metodologia/limiar/
subperiodos de TASK-ALT-001. Resultado real
(`reports/alt_info_open_interest_diagnostic.md`): **nenhuma cumpre o
criterio** -- a mais forte (`oi_delta`, rho=-0,0189) fica a 0,0111 do
limiar de 0,03, mais de 2x mais longe que o near-miss da Familia G.
Padrao notavel: `oi_delta`/`oi_acceleration` mostram sinal consistente
mas magnitude DECAINDO monotonicamente nos 3 subperiodos (ex.: oi_delta
-0,0321 -> -0,0202 -> -0,0048), quase zero no periodo mais recente --
leitura de eficiencia de mercado crescente.

**Estado naquela etapa da Research Phase II:** G e F ambas fechadas sem
informacao. Este trecho foi supersedido pelo workstream atual acima:
Familia J ja foi executada e fechou com informacao de regime. Pendencias
remanescentes depois de `TASK-ALT-004`: near-miss de
`funding_price_divergence`, Familia H adiada/cara e Familia I BLOQUEADA
por falta de fonte historica.

## Workstream anterior: Research Phase II -- Alternative Information aberta (ADR-0019); TASK-ALT-001 (Familia G, Funding Structure) FECHADA sem informacao (near-miss notavel)

Apos Research Family E fechar (ambos CS-001/CS-002 NAO PASSA), o usuario
propos uma mudanca de paradigma: nao mais uma nova familia de sinal
sobre OHLCV, mas uma nova FASE de pesquisa sobre fontes de informacao
alternativas (Open Interest, Funding Structure, Order Flow, Liquidation
Dynamics, Regime Detection), invertendo a ordem de trabalho (medir
conteudo informacional antes de desenhar regra).

Reconnaissance real de dados (leitura de listagem S3 do bucket publico
`data.binance.vision`, sem download comitado): Familia G (funding) ja
tem dado no dataset existente; Familia F (Open Interest) tem dado
disponivel via a familia `metrics` (5min, mesma infra, download
pequeno); Familia H (Order Flow/L2) continua cara; Familia I
(Liquidation Dynamics) esta **BLOQUEADA** -- `liquidationSnapshot` vazio
para todos os symbols no bucket publico, sem fonte historica.

Decisoes travadas: sequenciar G -> F; adiar I indefinidamente; Familia J
(Regime Detection) pode usar OHLCV (nao afirma alfa, so segmenta);
metodologia de "conteudo informacional primeiro" usa correlacao de
Spearman + estabilidade de sinal em 3 subperiodos (nao mutual
information).

`TASK-ALT-001` (DONE, `docs/pre_registers/TASK-ALT-001.md`): 4 features
de funding formalizadas (extreme z-score 90d causal, reversal 24h,
acceleration, price divergence), rodadas contra retorno futuro 24h.
`src/research/info_content.py` criado como motor generico reutilizavel
para toda a Fase II.

Resultado real (`reports/alt_info_funding_structure_diagnostic.md`):
**nenhuma das 4 features cumpre o criterio pre-registrado** (rho
absoluto >=0,03 E sinal consistente em 3 subperiodos). 3 mostram
inversao de sinal entre subperiodos (ruido). A 4a
(`funding_price_divergence`) mostra sinal POSITIVO notavelmente estavel
(0,0276/0,0230/0,0239 nos 3 subperiodos, 0,0248 na amostra completa) mas
fica a 0,0052 do limiar -- near-miss classificado estritamente como SEM
informacao, sem ajuste de limiar. Documentado como pista para uma futura
task independente, nao um re-teste. Familia F (Open Interest) e a
proxima na sequencia.

## Workstream anterior (fechado): Research Family E -- Cross-Sectional Factors FECHADA (CS-001 e CS-002, ambos NAO PASSA, ADR-0017/0018)

Por recomendacao explicita do usuario (nao pivotar para Order Flow ainda;
replicar literatura documentada antes de inventar), foi aberta a
Research Family E, executada sequencialmente (uma task por vez).

`TASK-CS-001` (DONE): replicacao fiel de Cross-Sectional Momentum
semanal estilo Liu & Tsyvinski (2021, JFE) -- rank por retorno bruto de
formacao (168h), quintil K=4 de 20 symbols, equal-weight dollar-neutro,
full rebalance, custo 6,0bps, mesmo split OOS do TASK-TSREV-001. Ver
`docs/pre_registers/TASK-CS-001.md`.

Resultado real (`reports/cs_momentum_backtest_final.md`): gate **NAO
PASSA decisivamente** -- net PF 0,98 (abaixo do empate), net PnL
-370,61bps sobre 408 pernas OOS. Nem o efeito bruto pre-custo existe
(gross PnL OOS negativo, -64,61bps) e o win rate fica em ~50% em ambos
os periodos (ruido), contrastando com o TSREV primario (sinal
direcional real ~52,7% em ambos os periodos, que falhou so na
economia). Drawdown isoladamente teria passado.

`TASK-CS-002` (DONE): antes de escrever o pre-registro, uma verificacao
matematica mostrou que espelhar CS-001 no MESMO horizonte (168h) faria o
net PnL OOS negativo por construcao (`gross_reversal=-gross_momentum`,
custo identico) -- confirmado numericamente sem rodar nenhum backtest.
Por isso `docs/pre_registers/TASK-CS-002.md` usa 24h, genuinamente
distinto, com divulgacao previa explicita de que TSREV Familia B (24h,
z-score, descritivo) ja mostrava profit factor 0,87 na mesma direcao.

Resultado real (`reports/cs_reversion_backtest_final.md`): gate **NAO
PASSA** em todos os 3 cortes (OOS/IS/full-sample, PF 0,94/1,00/0,98 --
nunca cruza 1,10). Gross PnL OOS tambem negativo (-801,35bps). Win rate
49,35% (OOS), ruido. Drawdown isolado teria passado.

**Decisao final (ADR-0018, recomendacao do usuario):** com CS-001 e
CS-002 ambos NAO PASSA, a linha de pesquisa baseada EXCLUSIVAMENTE em
fatores classicos de preco fecha nesta sessao -- cumulativamente 5
familias (A: Kalman/OU; Funding Carry; TSMOM; C: TSREV; E:
Cross-Sectional) todas NAO PASSA sob custo realista neste
universo/periodo. CS-003 (Residual Momentum), CS-004 (PCA Statistical
Arbitrage), CS-005 (Ensemble) permanecem backlog formalmente nao
cancelado. O usuario tambem decidiu explicitamente NAO mudar o universo
agora (para small-caps/menor liquidez, onde a literatura sugere maior
edge bruto mas tambem maior custo) -- registrado como ideia futura, nao
iniciada, para preservar comparabilidade com toda a pesquisa ja feita.
Proximo passo recomendado (nao automatico, decisao do usuario): abrir
uma categoria nova de informacao -- Market Microstructure/Alternative
Data (open interest, order flow, liquidacoes, funding como feature) --
com seu proprio pre-registro.

## Workstream em paralelo: Research Family D -- Payoff Engineering, Fase 2 PRE-REGISTRADA (TASK-PAYOFF-002/ADR-0016), execucao BLOCKED aguardando dados novos

Apos o encerramento da Funding Carry Signal Iteration (ADR-0013), o usuario
conduziu tres pivots de sinal sucessivos, todos com pre-registro formal e
todos com gate **NAO PASSA**:

```text
TSMOM-1  (Donchian breakout + ATR trailing stop, TASK-TSMOM-001): net PF 1,005 vs gate 1,20
Family C (TSREV, celula primaria 24h, OOS, ADR-0014/TASK-TSREV-001/002): net PF 1,0143 vs gate 1,05;
          drawdown ~6x o baseline buy-and-hold; win rate estavel 52,68% (OOS) vs 52,71% (in-sample)
```

Apos o fechamento da Family C, o usuario abriu Research Family D --
**Payoff Engineering** (ADR-0015). Fase 1 (`TASK-PAYOFF-001`, DONE) e um
estudo puramente diagnostico/distributivo sobre as trades JA produzidas
pela celula primaria TSREV -- sem novo sinal, sem gate, sem re-tuning. Ver
`reports/tsrev_payoff_attribution.md` para a analise completa. Achado mais
acionavel: assimetria forte SHORT (net +37.938bps, WR 55,2%) vs LONG (net
-30.248bps, WR 50,5%), reforcada por symbol/liquidez (BTC/ETH e o quartil
de maior liquidez sao os piores desempenhos). Alerta metodologico
explicito no relatorio: qualquer filtro derivado desses cortes (SHORT-only,
exclusao BTC/ETH, exclusao de alta liquidez) so pode ser validado numa
Fase 2 com um split out-of-sample GENUINAMENTE NOVO (dados posteriores a
2026-05) -- nunca reaproveitando o mesmo periodo OOS que gerou a hipotese.

**Fase 2 (TASK-PAYOFF-002) foi pre-registrada (ADR-0016) mas a EXECUCAO
esta BLOCKED aguardando dados.** O usuario decidiu direcionar o proximo
passo para validar as hipoteses da Fase 1 em um periodo out-of-sample
genuinamente novo -- nao para Order Flow. Como o dataset termina em
2026-05-31 (hoje: 2026-07-05), nao existe ainda um periodo novo real
disponivel. Diante de 3 opcoes (baixar dados ja disponiveis agora ~5
semanas/~350-400 trades; aguardar mais meses; usar holdout interno do OOS
ja usado), o usuario escolheu **aguardar acumulacao real de dados novos**.

Design travado ANTES de qualquer dado novo existir
(`docs/pre_registers/TASK-PAYOFF-002.md`):

```text
Primaria (decisoria): SHORT-only na celula TSREV Family A 24h (escolhida
                       pelo maior efeito absoluto da Fase 1, replicado de
                       forma independente pelo diagnostico Z-score
                       anterior).
Secundarias (descritivas): exclusao BTC/ETH; regime causal por retorno
                       trailing 30 dias; filtro de liquidez Q2.
Gate (so na primaria, so no OOS novo): mesma estrutura da TASK-TSREV-001
                       (net PF>1,05 E net PnL>0 E DD<=baseline recalculado
                       E trade_count SHORT>=200).
Gatilho de retomada (operacional): dataset estendido alem de 2026-05-31
                       com >=500 trades totais resolvidos (~1,5 meses de
                       dado novo estimado).
```

**Order Flow/L2 microstructure permanece explicitamente deferido** --
so seria considerado se a Fase 2 tambem falhar o gate, per a recomendacao
do usuario.

## Historico (fechado): Sprint 10 (Execution Risk Gate) PAUSADA; pivot de sinal (ADR-0012)

Sprint 10 Bloco 1 (Passive/Maker Execution Variant) esta DONE -- ver
resultado real na secao `## Resultado real (2026-07-05)` abaixo e
`reports/passive_execution_variant.md`. Com base nesse resultado (0/13
pares liquido-positivos sob execucao passiva, selecao adversa evidente,
exposicao residual +27%), o usuario decidiu (ADR-0012, `DECISIONS.md`)
**pausar** o escopo completo da Sprint 10 (Execution Risk Gate) e pivotar
para uma nova familia de sinal, estruturalmente diferente de reversao a
media de curto prazo.

Candidatos apresentados pelo usuario:

```text
(a) Momentum cross-sectional
(b) Funding rate stat-arb / basis  <- ESCOLHIDO (usuario confirmou, "pode ir")
(c) Anomalias de fluxo de ordens intradiario (HFT, timeframes menores)
```

## Workstream aberto: Funding Carry Signal Iteration (ADR-0013)

`TASK-FUND-001` (DONE): hipotese pre-registrada em
`tasks/funding_carry/TASK-FUND-001-define-hypothesis.md`. Resumo: carry de
funding-rate cross-sectional -- a cada settlement real de funding (~3x/dia),
ranquear os 20 simbolos do universo estatistico da Sprint 7 por
`funding_rate_asof` (real, causal, cobertura 100%, dado ja existente --
nenhum novo download), short nos K de funding mais alto / long nos K de
funding mais baixo, dollar-neutro, rebalanceado a cada intervalo.
Configuracao primaria K=5, gate net profit factor >= 1,10 (mesmo limiar do
Sprint 8 canonico), K=3/K=8 apenas descritivos. Nenhum parametro muda apos
ver o resultado de K=5.

`TASK-FUND-002` (DONE): `src/research/funding_carry.py` implementado
exatamente per o pre-registro; `scripts/run_funding_carry_backtest.py`
rodado real no dataset ja existente (sem novo download). Resultado:

```text
K=5 (primario):  net profit factor 0.840, net PnL -10.729,82 bps (3.287 rebalanceamentos)
K=3 (descritivo): net profit factor 0.869, net PnL -11.232,14 bps
K=8 (descritivo): net profit factor 0.743, net PnL -14.039,04 bps
Gate (K=5): NAO PASSA (limiar >= 1,10)
```

Gross edge e real e positivo em todos os K (funding + componente de preco
correlacionado), mas o custo de rebalancear 100% do book a cada 8h por 3
anos (19.722,00 bps acumulados) excede o gross edge (8.992,18 bps em K=5).
Ver `reports/funding_carry_backtest.md`.

### TASK-FUND-003 (DONE): rebalanceamento incremental por limiar de rendimento

Regra pre-registrada, aprovada explicitamente pelo usuario: manter uma
perna held a menos que a troca por um candidato melhore o funding em mais
que `cost_bps_per_leg_roundtrip` (6,0bps, a MESMA constante -- nenhum
parametro novo). Resultado real
(`reports/funding_carry_incremental_backtest.md`):

```text
K=5 (primario):  net profit factor 1,0904 (limiar 1,10 -- faltam so 0,0096, NAO PASSA)
K=3 (descritivo): net profit factor 1,1356 (PASSA, mas nao substitui K=5)
K=8 (descritivo): net profit factor 1,0856 (NAO PASSA)

Custo cai de 19.722,00 bps (fase 1) para 33,60 bps em K=5 (-99,83%)
Net PnL vira positivo: -10.729,82 -> +5.620,99 bps em K=5
Gate (K=5): NAO PASSA -- mas por margem minima, com amostra grande
(3.287 rebalanceamentos, 6,57x o piso de 500), nao e problema de poder
estatistico.
```

Per a disciplina pre-registrada deste projeto (ADR-0010), K=3 passar nao
substitui a decisao de K=5 -- nenhum re-teste com K diferente apos ver o
resultado.

**Decisao final do usuario (2026-07-05, Addendum ADR-0013): aceitar NAO
PASSA como resultado final e ENCERRAR a Funding Carry Signal Iteration.**
Usuario recusou explicitamente abrir TASK-FUND-004 (K=4) por seria
curve-fitting pos-resultado. Esta linha nao sera reaberta. Proxima
hipotese de sinal em decisao entre momentum cross-sectional e order-flow
intradiario/HFT.

Nenhuma nova sprint numerada foi aberta ainda. A secao
`## Sprint 10 -- Passive/Maker Execution Variant` abaixo permanece como
registro historico do bloco 1, ja concluido.

## Workstream anterior (fechado): Sprint 10 aberta (escopada) -- Passive/Maker Execution Variant

Decisao do usuario (registrada em `project_control/DECISIONS.md` ADR-0011):
abrir Sprint 10, mas escopado apenas ao primeiro bloco recomendado pelo
Execution/Risk Agent no fechamento da Sprint 9 -- testar uma variante de
execucao passiva/LIMIT/maker antes de qualquer conclusao definitiva sobre
edge. O escopo completo de Sprint 10 do `ROADMAP.md` (Execution Risk Gate
com limites de perda/drawdown diarios, kill switch, etc.) permanece **fora
de escopo** deste bloco.

Ver secao `## Sprint 10 -- Passive/Maker Execution Variant` abaixo para
objetivo, escopo, invariantes e tasks. A secao `## Sprint 9` mais abaixo
neste arquivo permanece como registro historico da sprint anterior, ja
fechada, e nao foi alterada.

## Sprint 10 -- Passive/Maker Execution Variant + Execution Risk Gate prep

### Por que existe

`reports/backtest_executable_v1.md` (Sprint 9) mostrou 0/13 pares
liquido-positivos, mas usando MARKET_IOC agressivo (cruza o spread) nos dois
lados de entrada e saida -- o cenario de custo mais caro possivel, nao o
unico testado. O Execution/Risk Agent recomendou explicitamente testar uma
variante passiva/maker (`simulate_limit_fill`, ja implementada e testada na
Sprint 9, mas nunca chamada pelo runner real) antes de concluir que a
estrategia nao tem edge.

### Objetivo

Comparar, nos mesmos 13 pares aprovados, os mesmos sinais causais e os
mesmos dados reais de Junho/2023, dois estilos de execucao:

```text
MARKET_IOC       -- baseline Sprint 9, reproduzido aqui como regressao
LIMIT_MAKER_TTL  -- ordem passiva cotada no touch (bid para BUY, ask para
                    SELL), nunca cruza o spread ao ser colocada, so
                    preenche se o mercado cruzar de volta dentro do TTL
```

### Escopo permitido

```text
- src/backtest/fill_model.py: simulate_limit_fill ganha reference_price
  opcional para slippage_bps consistente com MARKET_IOC (corrige debito
  P3 do QA Agent, Sprint 9); no_quote_fill_outcome exposto publicamente.
- src/backtest/execution_simulator.py: novo ExecutionStyle
  (MARKET_IOC / LIMIT_MAKER_TTL); simulate_round_trip_trade aceita
  execution_style (default MARKET_IOC, compatibilidade retroativa).
- src/backtest/replay_engine.py: ReplayConfig.execution_style propagado.
- scripts/run_sprint10_passive_execution_variant.py: roda os dois estilos
  nos mesmos 13 pares / mesmos sinais / mesmos dados reais, com checagem
  de reproducao exata do baseline MARKET_IOC contra
  sprint9_replay_results.json antes de confiar na comparacao.
- reports/passive_execution_variant.md.
```

### Fora de escopo

```text
- Execution Risk Gate completo (limites de perda/drawdown diarios, kill
  switch, sizing) -- isso e o resto do Sprint 10 do ROADMAP.md, nao este
  bloco.
- Qualquer promocao de par a paper trading ou live trading.
- Novo download de dados alem do necessario para repor o raw bookTicker
  de Junho/2023 (450 arquivos, 17.98GB, checksum-verificados) que nao
  estava presente nesta maquina -- mesmos dados, mesmo processo do
  ADR-0007, autorizados explicitamente pelo usuario nesta sessao para
  D:/CryptoPairTrading/cost_pilot_raw (fora do repositorio, fora de C:).
- Mudar geracao de sinal, gate de aprovacao de pares, ou politica de
  promocao.
- Apagar ou mover data/research/binance_public/cost_pilot/raw/ (permanece
  fora do escopo tocar TASK-008-08, que continua BLOCKED).
```

### Invariantes obrigatorios

```text
- sem cotacao => NO_QUOTE
- sem fill dentro do TTL => EXPIRED
- partial fill => exposicao residual explicita (unclosed_residual_quantity)
- ACK_UNKNOWN continua forcando reconciliacao simulada (evaluate_ack_guard)
- LIMIT_MAKER_TTL nunca cruza o spread na colocacao -- so preenche se uma
  cotacao POSTERIOR cruzar o preco (testado em
  tests/test_execution_simulator.py)
- MARKET_IOC com execution_style default deve reproduzir exatamente o
  resultado da Sprint 9 (checagem automatica no runner)
- nenhum resultado mascara exposicao residual como PnL positivo
```

### Sprint 10 tasks

| ID | Tarefa | Dono | Revisor | Status | Progresso |
|---|---|---|---|---|---:|
| TASK-010-01 | Abrir Sprint 10 escopado e definir contrato da variante passiva | PM Agent | Execution / Risk Agent | DONE | 100% |
| TASK-010-02 | Adaptar fill_model/execution_simulator/replay_engine para ExecutionStyle | Backtest Agent | QA / Chaos Testing Agent + Execution / Risk Agent | DONE | 100% |
| TASK-010-03 | Criar scripts/run_sprint10_passive_execution_variant.py | Backtest Agent | PM Agent | DONE | 100% |
| TASK-010-04 | Rodar replay real (MARKET_IOC vs LIMIT_MAKER_TTL) nos 13 pares | Backtest Agent | PM Agent + Quant Research Agent | DONE | 100% |
| TASK-010-05 | Gerar reports/passive_execution_variant.md | Documentation Agent | PM Agent + Backtest Agent | DONE | 100% |
| TASK-010-06 | Atualizar TEST_MATRIX/TASK_BOARD/CURRENT_SPRINT/PROJECT_STATE/HANDOFFS/RISKS | PM Agent | - | DONE | 100% |

### Nota de dados (2026-07-04)

O diretorio `data/research/binance_public/cost_pilot/raw/` (17.98GB,
checksum-verificado, gitignored por design) nao estava presente nesta
maquina/sessao. O usuario autorizou explicitamente re-baixar os MESMOS 450
arquivos de Junho/2023 (11 simbolos necessarios para os 13 pares
aprovados) via `scripts/run_sprint7_execution_cost_download.py`, com
destino em `D:/CryptoPairTrading/cost_pilot_raw` (fora do repositorio, por
falta de espaco em C:). Isto nao e um novo escopo de dados -- e o mesmo
dado, mesmo processo (ADR-0007), apenas reposicionado por falta de espaco
local. O download foi interrompido uma vez por queda da sessao anterior e
retomado com sucesso (o script pula download de arquivos ja existentes);
330 arquivos/checksums (11 simbolos x 30 dias, 11GB) verificados no total.

### Resultado real (2026-07-05)

Checagem de reproducao do baseline: **PASS** (MARKET_IOC rerodado pelo novo
codigo `ExecutionStyle`-aware reproduz exatamente o resultado da Sprint 9 --
todos os deltas de metricas em 0).

Comparando os 13 pares nos dois estilos:

```text
Pares liquido-positivos:     0/13 em ambos os estilos (MARKET_IOC e LIMIT_MAKER_TTL)
Portfolio net PnL:           MARKET_IOC -$2266.27  ->  LIMIT_MAKER_TTL -$2005.91  (+$260.35, ~11.5%)
Unclosed residual quantity:  MARKET_IOC 11470.92   ->  LIMIT_MAKER_TTL 14565.31   (+27%, PIOR)
Entry/exit legs EXPIRED:     0 (impossivel no MARKET_IOC)  ->  65 entrada / 36 saida no LIMIT_MAKER_TTL
```

Execucao passiva reduz o custo (11 dos 13 pares melhoram), mas nao chega
perto de tornar nenhum par liquido-positivo, e aumenta a exposicao residual
nao fechada em 27% no agregado (2 pares -- ETCUSDT/ETHUSDT e
ETCUSDT/LTCUSDT -- pioram sob o estilo passivo). Gate para "PnL liquido
positivo em cenario conservador" permanece **NAO PASSA**. Ver
`reports/passive_execution_variant.md` para metodologia completa,
tabela por par, e analise de riscos.

Isto fecha a pergunta especifica deixada aberta pela Sprint 9: o resultado
0/13 nao e simplesmente um artefato de testar apenas o estilo de execucao
mais caro. Nenhuma decisao de promocao a paper/live foi tomada; ADR-0011
nao muda politica de gate.

| ID | Tarefa | Dono | Revisor | Status | Progresso |
|---|---|---|---|---|---:|
| TASK-SIG-001 | Diagnosticar edge bruto do sinal | Quant Research Agent | Backtest + QA/Chaos + PM | DONE | 100% |
| TASK-SIG-002 | Testar reversao rapida com cap vertical causal | Backtest Agent | Quant Research + QA/Chaos + PM | DONE | 100% |
| TASK-SIG-003 | Falsificar filtro ex-ante de entrada por half-life | Backtest Agent | Quant Research + QA/Chaos + PM | DONE | 100% |
| TASK-SIG-004 | Checar reversao intrahora 5m em escopo pequeno | Backtest Agent | Quant Research + QA/Chaos + PM | DONE | 100% |

## Nota (2026-07-03): debito tecnico do ADR-0008 fechado

O Sprint 8 canonico do roadmap (Triple Barrier direcional + backtest
estatistico), citado como debito tecnico abaixo, foi construido
retroativamente como trabalho separado (`tasks/sprint_08_canonical/`,
TASK-008C-01/02/03) sem reabrir ou alterar este Sprint 9. Resultado: gate
NAO PASSA para os 41 pares estatisticos (ver `reports/backtest_statistical.md`
e `HANDOFFS.md`). `RISKS.md` atualizado para fechar essa linha. O proximo
sprint numerado do roadmap ainda nao foi iniciado.

## Sprint

Sprint 9 - Backtest executavel com simulacao de ordens (`project_control/ROADMAP.md`)

## Status

FECHADA. Gate NAO PASSA para "PnL liquido positivo em cenario conservador"
-- resultado real e revisado: 0 dos 13 pares aprovados no Sprint 8 sao
liquido-positivos com execucao realista (IOC agressivo, dados tick reais de
junho/2023). Ver `reports/backtest_executable_v1.md` para o relatorio
completo, incluindo um bug real de PnL encontrado e corrigido durante o
desenvolvimento, 4 revisoes formais completas, e a recomendacao explicita de
testar uma variante de execucao passiva/maker antes de concluir que a
estrategia nao tem edge.

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
| TASK-009-01 | Implementar fill_model.py | Backtest Agent | QA Agent + Execution/Risk Agent | DONE | 100% |
| TASK-009-02 | Implementar execution_simulator.py | Backtest Agent | Quant Research Agent + QA Agent | DONE | 100% |
| TASK-009-03 | Implementar replay_engine.py | Backtest Agent | QA Agent + Market Data Agent | DONE | 100% |
| TASK-009-04 | Testes de Sprint 9 (chaos, causalidade) | QA Agent | Backtest Agent + PM Agent | DONE | 100% |
| TASK-009-05 | Rodar replay real nos 13 pares | Backtest Agent | PM Agent + Quant Research Agent | DONE | 100% |
| TASK-009-06 | Relatorio e gate Sprint 9 | Documentation Agent | PM Agent + Backtest Agent | DONE | 100% |

## Resultado final (2026-07-02)

Durante o desenvolvimento, foi encontrado e corrigido um bug real: um
preenchimento parcial de perna retornava `average_price=None` (herdado de
`estimate_slippage`, Sprint 6), fazendo o simulador de execucao zerar
silenciosamente o PnL real dessa perna em ~40-50% dos trades. Corrigido
calculando o VWAP real a partir de `spent_notional/filled_quantity`.
Confirmado matematicamente correto pelo QA Agent em revisao independente.
Um segundo problema real (checksum computado mas nunca verificado antes de
usar os dados) foi encontrado pelo Market Data Agent e corrigido.

Resultado real e corrigido: 247 sinais, 239 trades executados, **0 dos 13
pares sao liquido-positivos** com execucao realista (IOC agressivo nas duas
pontas contra cotacoes reais tick-a-tick), portfolio `-$2266.27`. 70 de 239
trades (29%) tem desbalanceamento de perna; 11.470,92 unidades de posicao
ficaram sem fechar (exposicao residual nao marcada a mercado). Ver
`reports/backtest_executable_v1.md`.

## Gate para avancar ao Sprint 10 (Execution Risk Gate)

Sprint 10 pode abrir tecnicamente (implementacao completa, testada e
revisada), mas o criterio "PnL liquido positivo em cenario conservador" do
roadmap NAO PASSA:

```text
fill_model, execution_simulator e replay_engine implementados e testados: OK
replay real rodado nos 13 pares com dados verificados (nao mock): OK
PnL liquido realista reportado (positivo ou negativo, sem mascarar): OK -- e negativo
causalidade confirmada (nenhuma cotacao futura usada): OK
Backtest/QA/Market Data Agent registram PASSA; Execution-Risk Agent (consultivo)
  recomenda nao concluir "sem edge" sem testar variante LIMIT/maker primeiro
reports/backtest_executable_v1.md escrito: OK
PnL liquido positivo em cenario conservador: NAO -- 0/13 pares
```
