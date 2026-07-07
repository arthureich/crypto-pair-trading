# PROJECT_STATE

Last updated: 2026-07-07

## Atualizacao 2026-07-07: TASK-ALT-002 (Familia F, Open Interest) fechada sem informacao -- padrao de decaimento, nao estabilidade (ADR-0020)

Seguindo a sequencia ja acordada em ADR-0019 (G primeiro, depois F),
executado o download real e pequeno (~21.920 arquivos diarios, ~260MB,
mesmo bucket publico da Binance, familia `metrics` -- confirmada
disponivel na reconnaissance da task anterior) via
`scripts/download_alt_open_interest.py`. Cada arquivo verificado por
checksum SHA256 antes do uso (reusa `verify_checksum_file` de
`historical_dataset.py` sem modificacao); processamento memory-safe
(um symbol por vez, resample de 5min para 1h -- ultimo valor observado
por hora, convencao correta para uma variavel de estoque como Open
Interest -- descartando o frame de 5min antes do proximo symbol).
Resultado: 525.784 linhas horarias normalizadas para todos os 20
symbols, escritas em
`data/research/binance_public/normalized/sprint_alt_open_interest_202306_202605.csv.gz`.

`docs/pre_registers/TASK-ALT-002.md` formaliza 5 features de Open
Interest ANTES de rodar qualquer diagnostico: `oi_delta` (variacao
24h), `oi_volume_ratio` (OI relativo ao volume negociado, razao
estoque/fluxo), `oi_percentile` (percentil causal dentro da propria
historia de 90 dias), `oi_acceleration` (variacao da variacao),
`oi_price_divergence` (mesma formalizacao de
`funding_price_divergence`, trocando funding por OI). Reusa
integralmente a metodologia, limiar (0,03) e particao em 3 subperiodos
ja fixados em TASK-ALT-001/ADR-0019 -- nao re-decidida por familia.

**Resultado real** (`reports/alt_info_open_interest_diagnostic.md`,
`scripts/diagnostic_alt_open_interest.py`, reusa
`src/research/info_content.py` sem modificacao): **nenhuma das 5
features cumpre o criterio pre-registrado**, e nenhuma se aproxima do
limiar como `funding_price_divergence` fez na Familia G -- a mais
forte (`oi_delta`, rho=-0,0189 na amostra completa) fica a 0,0111 do
limiar de 0,03, mais que o dobro da distancia do near-miss anterior.

**Padrao notavelmente diferente do observado na Familia G: aqui o
achado interessante e DECAIMENTO, nao estabilidade.** `oi_delta` e
`oi_acceleration` mostram sinal consistente nos 3 subperiodos, mas a
magnitude decai MONOTONICAMENTE ao longo do tempo -- `oi_delta`:
-0,0321 (2023-06/2024-05) -> -0,0202 (2024-06/2025-05) -> -0,0048
(2025-06/2026-05), praticamente zero no periodo mais recente;
`oi_acceleration` mostra o mesmo padrao. Leitura consistente com a
narrativa de eficiencia de mercado crescente ja registrada na Fase 1
de Payoff Engineering (BTC/ETH, os symbols mais liquidos, tiveram os
piores desempenhos ali) -- se este efeito de OI ja existiu de forma
mais forte no passado, o mercado parece te-lo incorporado
progressivamente. `oi_price_divergence` e a unica feature com
inversao de sinal entre subperiodos.

Nenhum re-teste com limiar ajustado, nenhuma nova feature, nenhum novo
horizonte -- per a mesma disciplina de TASK-ALT-001. Nenhum strategy
design decorrente. 13 testes novos cobrindo o resample/parsing (sem
mock de rede -- mesmo precedente ja aceito para `historical_dataset.py`
em `RISKS.md`). Suite completa: 413 testes, ruff limpo.

**Estado atual da Research Phase II:** Familias G e F ambas fechadas
sem informacao. Pendencias: near-miss de `funding_price_divergence`
(candidato a task futura separada, nao um re-teste); Familia J (Regime
Detection) ainda nao iniciada; Familia H (Order Flow) continua
adiada/cara; Familia I (Liquidation Dynamics) continua BLOQUEADA por
falta de fonte historica.

## Atualizacao 2026-07-06: Research Phase II (Alternative Information) aberta; TASK-ALT-001 (Familia G, Funding Structure) fechada sem informacao -- near-miss notavel e estavel (ADR-0019)

Apos Research Family E fechar (CS-001 e CS-002 ambos NAO PASSA, ADR-0018),
o usuario propos um paradigma diferente: "Research Phase II -
Alternative Information," com regra explicita -- nenhuma hipotese pode
se basear apenas em OHLCV -- cobrindo 5 familias candidatas: F (Open
Interest), G (Funding Structure), H (Order Flow/L2), I (Liquidation
Dynamics), J (Regime Detection, camada de contexto sem trades proprios).
O usuario tambem propos inverter o fluxo de trabalho: medir conteudo
informacional (capacidade preditiva, estabilidade temporal, persistencia)
ANTES de desenhar qualquer regra operacional, em vez de backtest primeiro.

**Reconnaissance real de dados executada ANTES de qualquer
pre-registro** (probes de leitura via `ListObjectsV2` no bucket publico
`data.binance.vision`, mesma infra ja usada por
`historical_dataset.py`, nenhum download comitado ao repositorio):

```text
Familia G (Funding Structure): dado JA EXISTE (funding_rate_asof,
    100% cobertura, zero NaN, verificado nesta sessao) -- zero novo
    download.
Familia F (Open Interest): familia `metrics` confirmada disponivel
    (5min: sum_open_interest, sum_open_interest_value, long/short
    ratios de top traders e geral, taker buy/sell volume ratio) para
    todos os 20 symbols do universo, cobertura desde antes de
    2023-06-01 (o mais recente, SUIUSDT, desde 2023-05-03) -- mesma
    infra ja construida, arquivos pequenos (~12KB/dia/symbol), nada
    parecido com o problema de 17,98GB do bookTicker.
Familia H (Order Flow/L2): continua exigindo dado tick-level caro,
    ja mapeado e adiado em sessoes anteriores -- sem mudanca.
Familia I (Liquidation Dynamics): BLOQUEADA -- `liquidationSnapshot`
    (diario E mensal, checado sem filtro de symbol) esta
    COMPLETAMENTE VAZIO no bucket publico para todos os symbols. A
    Binance nao publica mais esse dataset em bulk historico (provavel
    descontinuacao por privacidade de posicoes). Nenhum backtest
    historico e possivel desta fonte; so captura forward-only via
    WebSocket `forceOrder` (sem historico) ou fornecedor terceiro (nao
    autorizado).
```

Diante disso, o usuario decidiu: (1) sequenciar Familia G primeiro
(zero dado novo), depois Familia F (download pequeno, mesma infra); (2)
Familia I fica formalmente BLOQUEADA, adiada indefinidamente, sem
avaliar fornecedor terceiro nem captura forward-only agora; (3) Familia
J pode usar features derivadas de OHLCV (volatilidade, tendencia), pois
nao afirma ter descoberto alfa -- e camada de segmentacao/contexto; (4)
a metodologia de "conteudo informacional primeiro" usa correlacao de
Spearman (nao mutual information) como metrica primaria, com um
criterio de estabilidade de sinal em 3 subperiodos cronologicos
nao-sobrepostos de ~12 meses -- decisao explicita pela mesma preferencia
por simplicidade que ja levou este projeto a abandonar Kalman/OU e
rejeitar purged CV.

`TASK-ALT-001` (DONE, `docs/pre_registers/TASK-ALT-001.md`, ADR-0019):
diagnostico puro (sem gate economico) sobre 4 features de funding
formalizadas ANTES de rodar qualquer coisa -- `funding_extreme`
(z-score causal 90d), `funding_reversal` (variacao 24h),
`funding_acceleration` (variacao da variacao), `funding_price_divergence`
(divergencia entre momentum de funding e momentum de preco, ambos
normalizados). Target: retorno futuro de 24h (reusa o horizonte de
TASK-CS-002). Criterio pre-registrado de "tem informacao":
`|rho| >= 0,03` E sinal consistente nos 3 subperiodos E na amostra
completa.

`src/research/info_content.py` implementado como infraestrutura
GENERICA e reutilizavel para toda a Fase II (nao especifica de funding)
-- correlacao de Spearman causal + particao em subperiodos + checagem
de consistencia de sinal. 12 testes novos.

**Resultado real** (`reports/alt_info_funding_structure_diagnostic.md`,
dataset existente, sem novo download): **nenhuma das 4 features cumpre
o criterio pre-registrado.** Tres (`funding_extreme`, `funding_reversal`,
`funding_acceleration`) mostram INVERSAO DE SINAL entre os 3
subperiodos -- exatamente o tipo de efeito espurio de amostra completa
que o criterio de estabilidade foi desenhado para filtrar. A quarta
(`funding_price_divergence`) mostra sinal POSITIVO notavelmente estavel
(0,0276 / 0,0230 / 0,0239 nos 3 subperiodos, faixa de apenas 0,0046;
0,0248 na amostra completa) -- mas fica a 0,0052 do limiar de 0,03.
Classificado estritamente como SEM_INFORMACAO, sem ajuste de limiar
apos ver o numero (mesma disciplina do near-miss do Funding Carry
incremental, TASK-FUND-003, 0,0096 do gate). Diferenca notavel: aquele
near-miss era um numero unico; este e estavel em 3 janelas
independentes -- documentado como pista legitima para uma FUTURA task
separada, nao um re-teste desta. Nenhum strategy design decorrente
nesta task. Familia F (Open Interest) e a proxima na sequencia
acordada. Suite completa: 406 testes, ruff limpo.

## Atualizacao 2026-07-05: Research Family E FECHADA -- TASK-CS-002 (Mean Reversion) tambem NAO PASSA; linha de fatores classicos de preco encerrada (ADR-0018)

Apos `TASK-CS-001` fechar NAO PASSA, o usuario propos executar CS-002
(Cross-Sectional Mean Reversion) com o mesmo rigor e, se tambem falhar,
encerrar a pesquisa baseada em fatores classicos de preco e abrir uma
categoria de informacao genuinamente nova (nao "Family F") -- Market
Microstructure/Alternative Data. O usuario tambem decidiu explicitamente
NAO mudar o universo de trading agora (a literatura sugere maior gross
edge em small-caps/menor liquidez, mas tambem maior custo/risco
operacional) -- registrado como ideia futura, nao iniciada, para
preservar comparabilidade com toda a pesquisa ja feita.

**Verificacao matematica ANTES de escrever o pre-registro:** se CS-002
usasse o MESMO horizonte de CS-001 (168h) com o MESMO ranking (retorno
bruto), apenas invertendo os lados, o net PnL OOS ja seria negativo por
CONSTRUCAO -- o portfolio de reversao no mesmo horizonte e o espelho
exato do portfolio de momentum (`gross_reversal = -gross_momentum`,
custo identico), entao `net_reversal_mirror = 64,61 - 306,00 =
-241,39bps`, sem rodar nenhum backtest novo. Rodar esse espelho exato
nao seria um teste informativo. Perguntado, o usuario escolheu usar 24h
-- horizonte genuinamente distinto, consistente com a literatura tratar
reversao de curto prazo e momentum de medio prazo como fenomenos em
escalas de tempo diferentes (nao o mesmo sinal com sinal trocado).

**Divulgacao explicita registrada no pre-registro, ANTES do backtest
rodar:** TSREV Familia B (`TASK-TSREV-002`, ADR-0014), horizonte 24h,
ranking por z-score (vol-normalizado, nao bruto), decil k=2, full-sample
(nao OOS-split), ja mostrava profit factor 0,87 e net PnL -9.035,01bps
-- direcionalmente na mesma linha, embora nao seja o mesmo teste (metrica
de ranking diferente, K diferente, amostra diferente). Essa proximidade
foi divulgada ANTES de rodar CS-002, para que o resultado fosse lido
corretamente e nao como uma surpresa nova.

`src/research/cs_reversion.py` implementado (mesma estrutura de
`cs_momentum.py`, lados invertidos: LONG perdedores/SHORT vencedores,
default de 24h). 15 testes novos, incluindo um teste de IDENTIDADE
MATEMATICA dedicado (`test_mirrors_cs_momentum_gross_pnl_exactly`) que
verifica `gross_reversal = -gross_momentum` no fixture hand-computed,
confirmando a logica que motivou a escolha do horizonte de 24h.

**Resultado real** (`reports/cs_reversion_backtest_final.md`, dataset
existente, sem novo download): gate **NAO PASSA em todos os 3 cortes**
(OOS/in-sample/full-sample) -- net profit factor 0,94 (OOS), 1,00 (IS),
0,98 (full), nunca cruzando o piso de 1,10 em nenhum periodo. Net PnL OOS
-2.985,35bps sobre 2.912 pernas resolvidas. Gross PnL OOS tambem
negativo (-801,35bps) -- mesmo padrao de CS-001, nao ha edge bruto
direcional para o custo consumir. Win rate 49,35% (OOS)/50,14% (IS),
ruido. Drawdown isoladamente teria passado (3.396,38bps vs baseline
11.003,94bps).

**Decisao final (per ADR-0018 e a recomendacao do usuario):** com CS-001
e CS-002 ambos NAO PASSA -- e nenhum dos dois com efeito bruto detectavel
pre-custo -- a linha de pesquisa baseada EXCLUSIVAMENTE em fatores
classicos de preco (candles) fecha nesta sessao. Isso cobre,
cumulativamente, 5 familias de pesquisa (A: Kalman/OU mean-reversion; B:
Funding Carry; TSMOM: Donchian breakout; C: TSREV; E: Cross-Sectional
Momentum/Mean Reversion), todas com veredito NAO PASSA sob custo
realista neste universo (20 perpetuos USD-M liquidos) e periodo
(2023-2026). CS-003 (Residual Momentum), CS-004 (PCA Statistical
Arbitrage), CS-005 (Ensemble) permanecem backlog formalmente nao
cancelado, mas o proximo passo natural recomendado -- nao automatico,
decisao do usuario -- e abrir uma categoria de informacao genuinamente
nova (Market Microstructure/Alternative Data: open interest, order
flow, liquidacoes, funding como feature), com seu proprio
pre-registro. Suite completa: 395 testes, ruff limpo.

## Atualizacao 2026-07-05: Research Family E -- Cross-Sectional Factors aberta; TASK-CS-001 (Momentum) FECHADA com NAO PASSA decisivo (ADR-0017)

Apos recomendacao explicita do usuario (nao pivotar para Order Flow
ainda; replicar um efeito ja documentado na literatura de fatores cripto
antes de inventar qualquer sinal novo), foi aberta a Research Family E,
com execucao sequencial (uma task por vez, cada uma com seu proprio
pre-registro) -- nao paralela, para preservar o mesmo rigor de nao
formular hipotese futura apos ver resultado de uma anterior.

`TASK-CS-001` (DONE, `docs/pre_registers/TASK-CS-001.md`): replicacao
fiel de Cross-Sectional Momentum semanal, estilo Liu & Tsyvinski (2021,
JFE) -- formulacao especifica de cripto (nao a convencao classica 12-1 de
equities, que teria poder estatistico baixo demais neste universo de 20
symbols/3 anos). Sinal: rank por retorno BRUTO de formacao de 168h (sem
normalizacao por sigma, diferente do z-score usado em TSREV), LONG no
quintil superior (K=4 vencedores), SHORT no quintil inferior (K=4
perdedores), equal-weight dollar-neutro, full rebalance, custo 6,0bps.
Reusa o mesmo split OOS ja pre-registrado em TASK-TSREV-001 (nunca
re-escolhido por hipotese). Metodologia de validacao: split cronologico
simples in-sample/OOS (nao walk-forward/purged CV -- decisao explicita
do usuario, justificada por nao haver sweep de hiperparametro nesta
regra fixa).

`src/research/cs_momentum.py` implementado, reusando
`split_out_of_sample`/`buy_and_hold_max_drawdown_bps` de `tsrev.py`. 14
testes novos, incluindo um teste de causal-independence (mutar barras
estritamente posteriores a uma barra de ranking nao muda a selecao de
vencedores/perdedores decidida naquela barra). Um bug real de DESENHO
DE TESTE foi encontrado e corrigido antes de reportar: o caso "drawdown
excede baseline" originalmente usava uma sequencia 100% vencedora (sem
nenhum drawdown real), tornando a asserção contra qualquer baseline
nao-negativo trivialmente satisfeita; corrigido com uma sequencia com um
drawdown intermediario genuino.

**Resultado real** (`reports/cs_momentum_backtest_final.md`, rodado no
dataset existente, sem novo download): gate **NAO PASSA
decisivamente**, nao por margem minima -- net profit factor **0,98**
(abaixo do empate) e net PnL **-370,61bps** sobre 408 pernas resolvidas
no periodo OOS decisivo. Diferente de TODAS as familias anteriores
(onde havia sempre algum gross edge bruto real, consumido por custo ou
por drawdown), aqui o efeito BRUTO pre-custo tambem e negativo
(-64,61bps) -- nao ha edge direcional detectavel para comecar. Win rate
fica em ~50% em ambos os periodos (49,40% in-sample, 51,96% OOS),
essencialmente ruido, contrastando com o sinal direcional genuino e
estavel do TSREV primario (52,68%/52,71%). O criterio de drawdown,
isoladamente, teria passado (2.154,52bps vs baseline 11.003,94bps de
buy-and-hold) -- a falha e em PF/PnL, nao em risco. A hipotese tambem
nao cruza o gate in-sample (PF 1,08<1,10) -- nao e um caso de "parecia
bom antes do OOS."

Limitacoes explicitas de fidelidade documentadas no relatorio: este
universo tem so 20 symbols (vs centenas na literatura original), e o
periodo testado (2023-2026, perpetuos USD-M) e mais recente/mais
arbitrado que o estudado no paper original (2014-2018) -- consistente
com a leitura de "eficiencia de mercado" ja registrada na Fase 1 de
Payoff Engineering. Nenhum sweep de parametro foi feito apos ver o
resultado. CS-002 (Cross-Sectional Mean Reversion), CS-003 (Residual
Momentum), CS-004 (PCA Statistical Arbitrage), CS-005 (Ensemble)
permanecem backlog planejado -- decisao de continuar, encerrar, ou
pivotar pertence ao usuario. Suite completa: 380 testes, ruff limpo.

## Atualizacao 2026-07-05: Research Family D -- Payoff Engineering, Fase 2 pre-registrada (ADR-0016), execucao BLOCKED aguardando dados novos

Apos ver os achados da Fase 1 (assimetria SHORT/LONG, symbol/liquidez,
clustering temporal), o usuario recomendou explicitamente NAO pivotar
para Order Flow ainda -- primeiro validar as hipoteses derivadas da Fase
1 num periodo out-of-sample genuinamente novo, dentro do mesmo framework
cientifico ja estabelecido. Verificacao imediata: o dataset normalizado
termina em 2026-05-31; hoje e 2026-07-05; nao existe dado real posterior
para o universo completo de 20 symbols em nenhum lugar do repositorio.
Isso bloqueia qualquer teste "genuinamente novo" agora.

Apresentadas 3 opcoes ao usuario: (a) baixar dados reais ja disponiveis
agora (~5 semanas, ~350-400 trades estimados, poder estatistico bem
menor); (b) aguardar mais meses de acumulacao real antes de testar; (c)
holdout interno do OOS ja usado (mais rapido, mas metodologicamente mais
fraco -- contaminacao parcial, pois a hipotese foi gerada olhando o
agregado das 12 meses). O usuario escolheu **(b) aguardar**.

Per a disciplina pre-registrada deste projeto (escolher a celula
primaria pelo prior, nao pelo resultado), o desenho da Fase 2 foi
travado AGORA, antes de qualquer dado novo existir
(`docs/pre_registers/TASK-PAYOFF-002.md`, ADR-0016 em `DECISIONS.md`):

```text
Primaria (decisoria, escolhida pelo usuario): SHORT-only na celula TSREV
    Family A 24h -- maior efeito absoluto da Fase 1 (+37.938 vs
    -30.248bps), replicado de forma independente pelo diagnostico
    Z-score cross-sectional anterior nesta sessao.
Secundarias (descritivas, nunca substituem a primaria): D2 exclusao
    BTC/ETH; D3 regime causal por retorno trailing 30 dias (shift(1),
    sem look-ahead); D4 filtro de liquidez Q2 (mesma metodologia de
    quartil da Fase 1).
Gate (so na primaria SHORT-only, so no OOS novo): mesma estrutura da
    TASK-TSREV-001 -- net PF>1,05 E net PnL>0 E max DD<=baseline
    (recalculado no novo periodo, nunca reusando os 11.003,94bps
    antigos) E trade_count SHORT resolvido >=200.
Gatilho operacional de retomada (nao e criterio de gate): dataset
    estendido alem de 2026-05-31 com >=500 trades totais resolvidos da
    configuracao primaria (margem de seguranca sobre o piso de 200
    SHORT, dado que SHORT historicamente e ~46% do total) --
    estimativa ~1,5 meses de dado novo real.
```

**TASK-PAYOFF-002 esta BLOCKED** (nao READY, nao IN_PROGRESS): nenhum
codigo, nenhum download, nenhuma execucao ate o gatilho ser atingido.
Order Flow/L2 microstructure permanece deferido -- so seria considerado
se esta Fase 2 tambem falhar o gate, conforme a propria recomendacao do
usuario.

## Atualizacao 2026-07-05: Research Family D -- Payoff Engineering, Fase 1 DONE (ADR-0015)

Apos o fechamento da Research Family C / TSREV (gate NAO PASSA, ver abaixo),
o usuario propos uma mudanca de foco: em vez de abrir mais uma familia de
sinal, estudar por que a familia ja pre-registrada (TSREV, celula
primaria, 24h, out-of-sample) perde -- de onde vem o drawdown, e se ha
concentracao de perdas por tempo, ativo, lado, volatilidade, funding ou
liquidez. Fase 1 e explicitamente diagnostica: nenhum novo sinal, nenhum
gate, nenhum re-tuning -- apenas analise de distribuicao sobre as 3.941
trades OOS ja produzidas pela celula primaria. ADR-0015 registra o escopo
e o limite explicito: Fase 2 (position sizing, volatility targeting,
regime filters, exposicao dinamica) e Order Flow/L2 microstructure
permanecem fora de escopo agora.

`TASK-PAYOFF-001` (DONE): `scripts/diagnostic_tsrev_payoff.py`
implementado, reusando `run_time_series_reversal_backtest` com a
configuracao EXATA da celula primaria (nenhum parametro novo), sem novo
download. Durante a analise foi encontrado e corrigido um bug real: a
funcao de concentracao de perdas (Pareto) usava
`(cumulative <= threshold).sum() / n`, que conta TODAS as posicoes da
serie cumulativa monotonica que satisfazem a condicao (nao so a primeira
travessia), produzindo o resultado logicamente impossivel
`frac_50 (81,1%) > frac_80 (54,5%)`. Corrigido com um helper
`_first_crossing_fraction()` (via `argmax()` no primeiro indice de
travessia); re-rodado, resultado corrigido e monotonico:
`frac_50=19,0% < frac_80=45,5%`.

Achados principais (`reports/tsrev_payoff_attribution.md`):

```text
1. Drawdown e estrutural/difuso, nao causado por outliers -- pior trade
   individual so -33,8bps; e preciso 19,0% das trades perdedoras para
   50% da perda total e 45,5% para 80%.
2. Assimetria forte SHORT (net +37.938,31bps, WR 55,2%) vs LONG
   (net -30.248,16bps, WR 50,5%) -- replica o achado do diagnostico
   cross-sectional Z-score anterior nesta sessao.
3. BTCUSDT/ETHUSDT (mais liquidos/maior cap) sao os 2 piores symbols;
   quartil de maior liquidez tambem e negativo -- leitura de eficiencia
   de mercado (majors mais arbitrados).
4. Volatilidade de entrada e funding rate (corr=0,0029) NAO explicam o
   payoff de forma linear/limpa.
5. Clustering temporal: 2 de 12 meses OOS concentram a maior parte da
   variancia (2025-06 e 2026-01 fortemente negativos; 2026-04
   fortemente positivo) -- hipotese de regime, amostra pequena demais
   para confirmar.
```

Alerta metodologico explicito registrado no relatorio: qualquer filtro
inferido destes cortes (SHORT-only, exclusao BTC/ETH, exclusao de alta
liquidez) so pode ser validado numa Fase 2 pre-registrada com um split
out-of-sample GENUINAMENTE NOVO (dados posteriores a 2026-05) -- testar
esse filtro no mesmo periodo OOS que gerou a hipotese seria re-minerar os
mesmos dados, nao uma confirmacao valida. Nenhuma decisao de estrategia
foi tomada nesta fase. Verificacao: reusa funcoes ja testadas de
`tsrev.py` (nenhum teste novo requerido por ADR-0015), 366 testes da
suite completa, ruff limpo.

## Atualizacao 2026-07-05: Sprint 10 (Execution Risk Gate) PAUSADA; pivot de sinal decidido pelo usuario (ADR-0012)

Decisao do usuario, registrada em ADR-0012 (`DECISIONS.md`): pausar o
escopo completo da Sprint 10 (Execution Risk Gate) e pivotar para uma nova
familia de hipotese de sinal, estruturalmente diferente de reversao a
media de curto prazo. Motivo: o resultado real do Sprint 10 Bloco 1
(`reports/passive_execution_variant.md`) mostrou que mesmo com execucao
passiva (`LIMIT_MAKER_TTL`), o portfolio permanece 0/13 pares
liquido-positivos, com selecao adversa evidente (65 pernas de entrada e 36
de saida expiraram sem preencher; exposicao residual nao fechada aumentou
27% em vez de diminuir). Isto reforca, sob o angulo de realismo de
execucao, o que a ADR-0010 ja havia fechado sob o angulo estatistico: o
sinal Kalman/OU de reversao a media, neste universo e dataset, nao tem
edge exploravel sob nenhum estilo de execucao testado (agressivo ou
passivo).

A Sprint 10 (Execution Risk Gate completo) fica **PAUSADA, nao abandonada**
-- retoma quando um novo candidato de sinal demonstrar edge liquido sob
pelo menos um estilo de execucao realista. A infraestrutura das Sprints
1-6 e 9-10 (ledger, recovery, book local, fill_model/execution_simulator/
replay_engine com MARKET_IOC e LIMIT_MAKER_TTL) e agnostica a sinal e nao
foi revertida.

Proxima hipotese de sinal **escolhida**: funding-rate carry (usuario
confirmou a recomendacao do PM Agent com "pode ir"). ADR-0013 registra a
decisao e o achado de auditoria: os dados de funding real (causal, 100% de
cobertura, 20 simbolos, 2023-06/2026-05) ja existem no dataset normalizado
da Sprint 7 -- nenhum novo download necessario.

`TASK-FUND-001` (DONE): hipotese pre-registrada em
`tasks/funding_carry/TASK-FUND-001-define-hypothesis.md` -- carry
cross-sectional por `funding_rate_asof`, short top-K/long bottom-K
simbolos, dollar-neutro, rebalanceado a cada settlement real de funding.
Configuracao primaria K=5, gate net profit factor >= 1,10, antes de
qualquer codigo de backtest existir.

`TASK-FUND-002` (DONE): implementado e rodado real no dataset ja existente
(sem novo download). Gate (K=5, primario): **NAO PASSA** -- net profit
factor 0,840, net PnL -10.729,82 bps sobre 3.287 rebalanceamentos. K=3
(0,869) e K=8 (0,743) tambem falham, de forma monotonica, reforcando que
nao e artefato da escolha de K. Gross edge (funding + componente de preco
correlacionado) e real e positivo (+8.992,18 bps em K=5), mas o custo do
rebalanceamento completo a cada 8h por 3 anos (19.722,00 bps) o supera.
Ver `reports/funding_carry_backtest.md`. Convencao de sinal confirmada
correta por revisao adversarial independente (esta sessao).

`TASK-FUND-003` (DONE): rebalanceamento incremental por limiar de
rendimento marginal, reusando `cost_bps_per_leg_roundtrip` como o proprio
limiar (nenhum parametro novo, aprovado explicitamente pelo usuario).
Resultado real (`reports/funding_carry_incremental_backtest.md`): custo
cai 99,83% (19.722,00 -> 33,60 bps em K=5), net PnL vira positivo
(-10.729,82 -> +5.620,99 bps), mas o gate no K=5 primario **NAO PASSA por
margem minima** (net profit factor 1,0904 vs limiar 1,10, diferenca de
0,0096, com amostra grande -- 3.287 rebalanceamentos -- nao e problema de
poder estatistico). K=3 (1,1356) passa mas e descritivo, nao substitui a
decisao de K=5 per a disciplina pre-registrada (ADR-0010).

## Atualizacao 2026-07-04: Sprint 10 aberta (escopada) -- Passive/Maker Execution Variant

Decisao do usuario, registrada em ADR-0011 (`DECISIONS.md`): abrir Sprint 10,
escopado apenas ao bloco recomendado pelo Execution/Risk Agent no fechamento
da Sprint 9 -- testar uma variante de execucao passiva/LIMIT/maker
(`LIMIT_MAKER_TTL`) contra o baseline agressivo (`MARKET_IOC`) nos mesmos 13
pares, mesmos sinais causais, mesmos dados reais de Junho/2023. O escopo
completo de Sprint 10 do `ROADMAP.md` (Execution Risk Gate com limites de
perda/drawdown diarios, kill switch) permanece fora de escopo deste bloco.

Implementado: `ExecutionStyle` (`MARKET_IOC`/`LIMIT_MAKER_TTL`) em
`src/backtest/execution_simulator.py`, propagado por
`src/backtest/replay_engine.py::ReplayConfig`; `simulate_limit_fill` em
`src/backtest/fill_model.py` ganhou `reference_price` opcional para
`slippage_bps` consistente com `MARKET_IOC` (corrige debito P3 do QA Agent
identificado na revisao da Sprint 9); `no_quote_fill_outcome` exposto
publicamente para reuso fail-closed. Nao muda geracao de sinal nem politica
de gate. Suite completa (324 testes) e ruff limpos apos a mudanca.

O diretorio `data/research/binance_public/cost_pilot/raw/` (17.98GB,
checksum-verificado, gitignored por design) nao estava presente nesta
maquina/sessao -- e machine-local, nao versionado no git. O usuario
autorizou explicitamente re-baixar os mesmos 450 arquivos de Junho/2023 (os
11 simbolos necessarios para os 13 pares aprovados) para
`D:/CryptoPairTrading/cost_pilot_raw` (fora do repositorio, por falta de
espaco em C:); 330 arquivos/checksums (11GB) verificados no total.

**Resultado real (2026-07-05):** checagem de reproducao do baseline PASS
(MARKET_IOC rerodado reproduz exatamente a Sprint 9). Comparando os 13
pares: **0/13 pares liquido-positivos em ambos os estilos**. Portfolio net
PnL melhora de -$2266.27 (MARKET_IOC) para -$2005.91 (LIMIT_MAKER_TTL),
+$260.35 (~11.5%), mas a exposicao residual nao fechada (unclosed residual
quantity) **aumenta 27%** (11470.92 -> 14565.31) e 65 pernas de entrada +
36 de saida expiram sem preencher dentro do TTL de 60s -- um modo de falha
impossivel no MARKET_IOC. 2 dos 13 pares (ETCUSDT/ETHUSDT, ETCUSDT/LTCUSDT)
pioram sob o estilo passivo. Gate para "PnL liquido positivo em cenario
conservador" permanece **NAO PASSA**. Isto fecha a pergunta especifica
deixada aberta pela Sprint 9 (Execution/Risk Agent): o resultado 0/13 nao
e um artefato de testar apenas o estilo de execucao mais caro. Nenhuma
promocao a paper/live. Ver `reports/passive_execution_variant.md`.

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

Sprint 10 Bloco 1 (Passive/Maker Execution Variant, ADR-0011) DONE -- ver
`reports/passive_execution_variant.md`. Sprint 10 completa (Execution Risk
Gate do `ROADMAP.md`) **PAUSADA** por decisao do usuario (ADR-0012).
**Z-Score Cross-Sectional Reversion (alta frequencia, 1h-2h) ENCERRADA na
origem (2026-07-05, diagnostico pre-pre-registro).** Apos o Momentum
Cross-Sectional (12h-7d) mostrar continuidade proxima de ruido (48-52%
positivo em todas as janelas), o usuario propos micro-reversao
cross-sectional via Z-score (1h-4h). Diagnostico dedicado
(`scripts/diagnostic_zscore_reversion.py`,
`reports/zscore_diagnostic_tails.md`) confirmou reversao real e
estatisticamente consistente (frac_positive > 51% em 9/9 combinacoes
formacao x limiar testadas), mas de magnitude economica insuficiente:
regra de decisao pre-registrada pelo usuario (formacao=1h, frente=1h,
|Z|>3.0, combinado long+short >= 10,0 bps) mediu 1,643 bps -> **DECISION:
ABORT**, aplicada estritamente. Achado nao-decisorio: lado SHORT (desvanecer
picos de alta) e consistentemente mais forte que o lado LONG (apostar em
recuperacao apos queda), o oposto da hipotese original do usuario; 47% da
cauda extrema concentra-se em so 4 de 20 simbolos (ruido idiossincratico,
nao choque de mercado amplo). Linha fechada, nao sera reaberta sem nova
decisao explicita do usuario.

**Momentum Cross-Sectional (12h-7d) ENCERRADO na origem (2026-07-05,
mesmo diagnostico).** Teste causal (rank por retorno trailing -> retorno
futuro resolvido) mostrou frac_positive entre 48-52% em todas as 4 janelas
(12h,24h,3d,7d) com horizonte de frente fixo de 24h, e mesmo no horizonte
casado (7d->7d, o melhor caso) o gap medio de +35bps e menos de 3% da
dispersao bruta cross-sectional medida na mesma janela (~1.324bps
mediana) -- indistinguivel de ruido nos horizontes intradiarios/curtos.
Usuario decidiu nao testar horizontes de meses (amostra de 3 anos daria
menos de 6 janelas nao-sobrepostas de 6 meses, poder estatistico
insuficiente) e nao retroceder para order-flow (falta L2 historico).
Pivot autonomo para Time-Series Momentum (TSMOM) em janelas de 4h-24h no
proprio ativo -- ver `reports/tsmom_diagnostic.md`.

**Time-Series Momentum (TSMOM, 4h-24h) diagnosticado e tambem
desencorajado (2026-07-05, mesmo pivot autonomo).** Resultado oposto ao
necessario para a hipotese: correlacao trailing-vs-forward negativa em
todas as 4 janelas, piorando com o horizonte (-0,005 em 4h -> -0,031 em
24h); sign persistence sistematicamente <50% (48,1%-49,1%), caindo ainda
mais no decil mais extremo (44,2%-46,6%); retorno direcional medio no
decil mais extremo vira negativo e cresce em magnitude: +0,67bps (4h),
-8,04bps (8h), -9,15bps (12h), -29,96bps (24h) -- o dobro da trava de
custo de 6,0bps, na direcao errada. 20 de 20 simbolos mostram o mesmo
padrao individualmente (unanime, nao e distorcao por outlier). Ver
`reports/tsmom_diagnostic.md`.

**TASK-TSMOM-001 (Donchian Breakout + ATR Trailing Stop) pre-registrada e
executada real -- ENCERRADA, gate NAO PASSA (2026-07-05).** Usuario
autorizou explicitamente avancar apesar do diagnostico anterior recomendar
cautela, sob a tese de que o mecanismo (trailing stop assimetrico, sem
profit target fixo) e estruturalmente diferente do proxy de holding
period fixo ja testado. Pre-registro em
`docs/pre_registers/TASK-TSMOM-001.md`: janela Donchian=24h, ATR=14h
(causal, shift(1)), stop=3xATR, custo=12,0bps (taker-taker), gate: net PF
>= 1,20 E win rate >= 30%. Implementado em
`src/research/tsmom_breakout.py` (14 testes focados, incluindo
causalidade do canal/ATR e trailing stop hand-computado), rodado real nos
20 simbolos/3 anos (sem novo download).

Resultado: 11.132 trades resolvidos, win rate 34,30% (supera o piso de
30%), mas net profit factor **1,005** (vs limiar 1,20 -- muito mais
distante que o quase-empate do funding carry incremental). Gross PnL
141.771,26bps quase inteiramente consumido pelo custo acumulado
(133.584,00bps = 11.132 trades x 12bps), sobrando so 8.187,26bps liquidos
em 3 anos. Max drawdown 85.654,62bps (~10,5x o PnL liquido total) --
perfil de risco/retorno inaceitavel mesmo ignorando o gate formal. Win
rate acima do piso confirma que a assimetria "cortar perdas rapido,
deixar ganhos correrem" se manifestou, mas fraca demais. Heterogeneidade
real entre simbolos (9/20 negativos, 11/20 positivos) documentada como
variancia esperada, nao como pista para um novo recorte pos-resultado.
Ver `reports/tsmom_backtest_final.md`. Nenhum parametro muda apos ver o
resultado. Aguardando revisao do usuario.

**Research Family C (TSREV) ENCERRADA (2026-07-05, ADR-0014).** Apos os
diagnosticos de momentum/reversao cross-sectional e o Donchian breakout
(TASK-TSMOM-001, tambem NAO PASSA) mostrarem que sofisticacao adicional
nao ajudava, o usuario propos um reset metodologico: reversao simples
(z=r/sigma), uma unica hipotese primaria pre-registrada por prior
empirico (nao por resultado observado), 7 celulas secundarias
explicitamente descritivas, e um periodo out-of-sample genuino decidindo
o gate. Pre-registro em `docs/pre_registers/TASK-TSREV-001.md`.

Resultado real (`reports/tsrev_backtest_final.md`): primaria (Familia A,
24h, out-of-sample) -- 3.941 trades resolvidos, win rate 52,68% (real,
estavel, quase identico ao in-sample 52,71% -- confirma reversao bruta
genuina), mas net profit factor **1,0143** (falha o limiar de 1,05) e max
drawdown 65.719,66bps contra um benchmark buy-and-hold de 11.003,94bps
(~6x pior -- falha decisivamente). Gate **NAO PASSA** em 2 dos 4
criterios. A divergencia in-sample (-48.496,48bps) vs out-of-sample
(+7.690,14bps) com win rate praticamente igual validou a decisao de exigir
periodo out-of-sample. Uma celula secundaria (Familia A, 48h) cruza PF e
net PnL mas ainda falha o mesmo criterio de drawdown -- nao promovida, per
a regra pre-registrada. Nenhum parametro mudou apos ver o resultado.
Decisao de abrir novo pre-registro (ex.: horizontes mais longos, ou
controle de risco/drawdown) pertence ao usuario.

**TSMOM (Donchian Breakout + ATR Trailing Stop) ENCERRADO (2026-07-05).**
Ver `reports/tsmom_backtest_final.md`: gate NAO PASSA, win rate 34,30%
(supera o piso de 30%, confirmando a assimetria esperada de um sistema de
trailing stop) mas net profit factor 1,005 (muito abaixo do limiar de
1,20) e max drawdown ~10,5x o lucro liquido total.

**Funding Carry Signal Iteration ENCERRADA (Addendum 2026-07-05, ADR-0013).**
`TASK-FUND-001/002/003` DONE. Resultado final aceito pelo usuario: gate
NAO PASSA no K=5 primario (fase 1: PF 0,840; fase 2 incremental: PF
1,0904, a 0,0096 do limiar de 1,10, amostra grande -- nao e problema de
poder estatistico). Usuario recusou explicitamente testar K=4 ou qualquer
ajuste de parametro pos-resultado (seria curve-fitting). Ver
`reports/funding_carry_backtest.md` e
`reports/funding_carry_incremental_backtest.md`. Nao sera reaberta.
Proxima hipotese de sinal em decisao (momentum cross-sectional vs
order-flow intradiario/HFT).

**Research Family D -- Payoff Engineering, Fase 1 (TASK-PAYOFF-001) DONE
(2026-07-05, ADR-0015).** Estudo puramente diagnostico sobre as trades
OOS ja produzidas pela celula primaria TSREV -- sem novo sinal, sem gate.
Achado mais acionavel: assimetria SHORT (net +37.938bps, WR 55,2%) vs
LONG (net -30.248bps, WR 50,5%), reforcada por symbol (BTC/ETH piores) e
liquidez (quartil de maior liquidez pior). Drawdown e difuso/estrutural,
nao causado por outliers. Ver `reports/tsrev_payoff_attribution.md`.

**Research Family D -- Payoff Engineering, Fase 2 (TASK-PAYOFF-002)
pre-registrada, execucao BLOCKED (2026-07-05, ADR-0016).** Usuario
recomendou nao pivotar para Order Flow ainda; validar primeiro as 4
hipoteses da Fase 1 em OOS genuinamente novo. Dataset termina em
2026-05-31 -- nenhum dado novo existe ainda. Usuario escolheu aguardar
acumulacao real (nao baixar agora, nao usar holdout interno). Design
travado agora: primaria SHORT-only, 3 secundarias descritivas (exclusao
BTC/ETH, regime causal, liquidez Q2), mesmo gate estrutural da
TASK-TSREV-001, gatilho operacional >=500 trades novos (~1,5 meses). Ver
`docs/pre_registers/TASK-PAYOFF-002.md`.

Nenhuma sprint numerada nova aberta ainda. Workstream pos-Sprint 9 /
pre-Sprint 10 (Signal Iteration 1 + TASK-SIG-004) permanece fechado, sem
reabertura.

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

## Componentes concluidos (Sprint 10, Bloco 1)

- `ExecutionStyle` (`MARKET_IOC`/`LIMIT_MAKER_TTL`) em
  `src/backtest/execution_simulator.py`, propagado por
  `src/backtest/replay_engine.py::ReplayConfig`; default `MARKET_IOC`
  preserva o comportamento da Sprint 9 exatamente.
- `simulate_limit_fill` (`src/backtest/fill_model.py`) ganhou
  `reference_price` opcional para `slippage_bps` consistente com
  `MARKET_IOC` (corrige debito P3 do QA Agent da Sprint 9);
  `no_quote_fill_outcome` exposto publicamente.
- `scripts/run_sprint10_passive_execution_variant.py`: roda os dois
  estilos nos mesmos 13 pares/sinais/dados reais, com checagem automatica
  de reproducao exata do baseline Sprint 9 antes de confiar na comparacao.
- `reports/passive_execution_variant.md`: resultado real -- 0/13 pares
  liquido-positivos em ambos os estilos; LIMIT_MAKER_TTL melhora o
  portfolio net PnL em $260.35 (~11.5%) mas aumenta a exposicao residual
  nao fechada em 27%.
- Novos testes automatizados cobrindo: ordem passiva nunca cruza o spread
  na colocacao, expira dentro do TTL sem preencher, fail-closed sem
  cotacao, compatibilidade retroativa com MARKET_IOC. Suite completa: 324
  testes, ruff limpo.

## Componentes em andamento

- Nenhum item tecnico do Sprint 9 em andamento -- sprint fechada.
- Nenhuma tarefa da Signal Iteration 1 em andamento: TASK-SIG-001/002/003 e
  a checagem exploratoria TASK-SIG-004 estao DONE.
- TASK-008-08 (limpeza segura dos 17GB de arquivos raw preservados)
  permanece BLOCKED aguardando aceite explicito do usuario antes de
  qualquer exclusao.
- Sprint 10 Bloco 1 (Passive/Maker Execution Variant) esta DONE. O escopo
  completo de Sprint 10 do `ROADMAP.md` (Execution Risk Gate) permanece
  nao iniciado.

## Objetivo atual

Sprint 10 completa permanece pausada (ADR-0012). A pesquisa estatistica
classica baseada em fatores de preco (candles) fechou nesta sessao
(Families A, Funding Carry, TSMOM, C/TSREV, E/Cross-Sectional, todas NAO
PASSA). A Research Phase II (Alternative Information, ADR-0019) esta em
andamento sequencial: `TASK-ALT-001` (Familia G, Funding Structure) e
`TASK-ALT-002` (Familia F, Open Interest) fecharam AMBAS sem
informacao -- nenhuma das 9 features formalizadas (4 de funding + 5 de
OI) cumpriu o criterio pre-registrado, embora `funding_price_divergence`
(Familia G) mostre um near-miss estavel em 3 subperiodos independentes.

Decisao pendente do usuario (nao ha proxima acao ja acordada): (1) abrir
Familia J (Regime Detection, ainda nao iniciada, unica que pode usar
OHLCV); (2) abrir uma task separada investigando o near-miss de
`funding_price_divergence` com dado/periodo genuinamente novo (mesma
disciplina de nao reusar a mesma amostra que gerou a pista); (3)
reconsiderar Familia H (Order Flow, cara) ou Familia I (Liquidation
Dynamics, BLOQUEADA); (4) encerrar a Research Phase II como um todo.

Uma linha fica pendente por bloqueio de dados (nao por decisao): Fase 2
do Payoff Engineering (TASK-PAYOFF-002, ADR-0016) -- pre-registrada e
travada, mas BLOCKED aguardando periodo OOS posterior a 2026-05-31 com
>=500 trades novos.

Linhas formalmente adiadas/bloqueadas, nao pendentes de decisao imediata:
Familia H (Order Flow/L2, cara/machine-local); Familia I (Liquidation
Dynamics, BLOQUEADA -- sem fonte historica disponivel); CS-003/004/005
(backlog nao cancelado da Research Family E, usuario ja indicou
preferencia por nao continuar); mudanca de universo de trading
(small-caps/menor liquidez, adiada para preservar comparabilidade).

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

Sprint 10 Bloco 1 (Passive/Maker Execution Variant) DONE. Resultado real
(`reports/passive_execution_variant.md`): checagem de reproducao do
baseline PASS; 0/13 pares liquido-positivos sob `LIMIT_MAKER_TTL`, igual a
`MARKET_IOC`; portfolio net PnL melhora +$260.35 (~11.5%, ainda muito
negativo) mas exposicao residual nao fechada aumenta 27%. Gate para "PnL
liquido positivo em cenario conservador" permanece **NAO PASSA** sob os
dois estilos de execucao testados. Isto fecha a pergunta especifica
deixada aberta pela Sprint 9 -- o resultado negativo nao e um artefato de
testar apenas execucao agressiva. Decisao de avancar para o escopo
completo de Sprint 10 (Execution Risk Gate) ou pivotar e do usuario.

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
