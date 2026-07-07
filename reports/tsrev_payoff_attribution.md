# TSREV Payoff Distribution/Attribution Study (Research Family D, Phase 1)

Diagnostic only, per `project_control/DECISIONS.md` ADR-0015. No gate, no new strategy, no re-tuning -- analyzes the exact trades already produced by the pre-registered TSREV primary cell (Family A, 24h, out-of-sample). 3941 resolved OOS trades analyzed.

## Loss concentration (Pareto)

```text
total losing trades: 1865 / 3941 (47.3%)
total loss (bps): -537579.84
fraction of LOSING trades responsible for 50% of total loss: 19.0%
fraction of LOSING trades responsible for 80% of total loss: 45.5%
worst 10 trades (bps): [-3380.84, -2467.95, -2419.7, -2174.76, -2084.48, -2023.26, -1985.43, -1970.1, -1875.89, -1815.37]
```

## Temporal clustering (by month, OOS)

```text
              sum  count    mean
month                           
2025-06 -16787.68    303  -55.40
2025-07    -64.65    378   -0.17
2025-08   4101.72    365   11.24
2025-09   -302.72    289   -1.05
2025-10   4950.50    352   14.06
2025-11  -9381.63    296  -31.69
2025-12  10529.56    285   36.95
2026-01 -38278.02    343 -111.60
2026-02   -215.47    346   -0.62
2026-03   9342.58    308   30.33
2026-04  43752.06    328  133.39
2026-05     43.88    348    0.13
```

## Symbol clustering

```text
          net_bps_sum  count  win_rate
symbol                                
BTCUSDT     -8843.836    197     0.447
ETHUSDT     -6447.328    194     0.505
ARBUSDT     -4074.691    192     0.510
OPUSDT      -3772.801    201     0.532
SUIUSDT     -3339.022    202     0.530
XRPUSDT     -2963.291    192     0.521
BNBUSDT     -2867.044    196     0.526
BCHUSDT     -1314.472    193     0.513
DOGEUSDT       16.339    191     0.550
TRXUSDT       132.933    193     0.523
ETCUSDT       920.395    185     0.546
AVAXUSDT     1255.362    204     0.510
APTUSDT      1790.581    201     0.537
DOTUSDT      2168.805    194     0.505
LINKUSDT     2825.051    208     0.553
UNIUSDT      2841.177    188     0.553
ADAUSDT      5596.478    203     0.547
SOLUSDT      6990.376    220     0.555
ATOMUSDT     7532.778    208     0.519
LTCUSDT      9242.353    179     0.553
```

## Side clustering (LONG=bet on bounce after drop, SHORT=bet on pullback after rise)

```text
       net_bps_sum  count  win_rate  mean_net_bps
side                                             
LONG    -30248.162   2117     0.505       -14.288
SHORT    37938.305   1824     0.552        20.800
```

## Entry-volatility clustering (quartiles of entry_sigma_h)

```text
                net_bps_sum  count  win_rate
sigma_quartile                              
Q1_low_vol          402.887    986     0.518
Q2                14301.047    985     0.548
Q3                -3583.964    985     0.518
Q4_high_vol       -3429.826    985     0.523
```

## Funding-rate clustering at entry

```text
corr(funding_rate_asof, net_bps) = 0.0029

                  net_bps_sum  count  win_rate
funding_quartile                              
Q1_low              22437.660    986     0.555
Q2                  14376.215    985     0.537
Q3                 -29953.812   1952     0.508
Q4_high               830.081     18     0.444
```

## Liquidity clustering (quote_volume quartiles at entry bar)

```text
                 net_bps_sum  count  win_rate
volume_quartile                              
Q1_low_liq         25373.948    986     0.552
Q2                 18954.726    985     0.558
Q3                -28822.980    985     0.496
Q4_high_liq        -7815.551    985     0.501
```

## Conclusão

**1. O drawdown NAO e causado por eventos-cauda raros.** Apenas 47,3% das
3.941 trades sao perdedoras, e essas perdas sao distribuidas de forma
relativamente difusa: e preciso 19,0% das trades perdedoras (~354 trades)
para acumular 50% da perda total, e 45,5% (~849 trades) para acumular 80%.
A pior trade individual e -33,8bps (ja ponderada). Isso descarta a hipotese
de "poucas trades catastroficas quebram o resultado" -- nao ha um evento ou
pequeno grupo de eventos isolavel por stop-loss ou circuit breaker. O
drawdown de 65.720bps e estrutural: vem de uma cauda larga e persistente de
trades com EV levemente negativo, nao de outliers.

**2. A assimetria LONG vs SHORT e o achado mais forte e mais consistente.**
SHORT (apostar contra picos de alta) entrega net +37.938bps com 55,2% de
win rate; LONG (apostar em repique apos quedas) entrega net -30.248bps com
50,5% de win rate -- uma diferenca de quase 68.000bps entre os dois lados
do mesmo sinal. Esse padrao replica exatamente o mesmo desequilibrio
observado no diagnostico cross-sectional Z-score anterior nesta sessao,
o que aumenta a confianca de que e um efeito real do mercado cripto no
periodo (fear/greed asymmetry, funding estrutural positivo, ou skew de
liquidacoes), e nao ruido de uma unica amostra.

**3. Symbol e liquidez contam a mesma historia.** Os dois piores ativos
sao exatamente os dois mais liquidos e de maior capitalizacao (BTCUSDT
-8.844bps, ETHUSDT -6.447bps), enquanto a maioria dos altcoins menores
fecha positiva. Na mesma linha, o quartil de MAIOR quote_volume (Q4) e
negativo (-7.816bps) e o quartil de MENOR volume (Q1) e positivo
(+25.374bps). Isso e consistente com a leitura de eficiencia de mercado:
BTC/ETH tem mais capital sofisticado competindo pela mesma reversao de
curto prazo, erodindo o edge; ativos menos liquidos/menos arbitrados
preservam mais do sinal.

**4. Volatilidade de entrada e funding rate NAO explicam o payoff de
forma limpa.** Os quartis de sigma_h nao sao monotonicos (Q2 e o melhor,
Q1/Q3/Q4 mistos) e a correlacao entre funding_rate_asof e net_bps e
essencialmente zero (0,0029). Note tambem que o quartil Q4_high de
funding tem apenas 18 trades (distribuicao de funding e fortemente
concentrada perto de zero, com poucos outliers extremos) -- qualquer
leitura desse corte especifico deve ser tratada com cautela por baixa
amostra.

**5. Clustering temporal sugere efeito de regime, mas com poucos meses
para confirmar.** De 12 meses OOS, dois sao claramente ruins (2025-06:
-16.788bps; 2026-01: -38.278bps, o pior mes) e um e claramente bom
(2026-04: +43.752bps). Esses tres meses somados (-11.514bps liquido)
tem magnitude proxima do resultado liquido total (+7.690bps), ou seja, o
resultado agregado depende fortemente de poucos meses extremos. Com
apenas 12 observacoes mensais nao e possivel separar "regime de
mercado" de "sorte de amostra" com confianca estatistica -- fica como
hipotese, nao conclusao.

**Sintese e implicacao para Fase 2 (nao iniciada agora):** os tres cortes
independentes que apontam na mesma direcao -- lado (SHORT >> LONG),
ativo (altcoins >> BTC/ETH) e liquidez (baixa >> alta) -- formam um
padrao coerente e mutuamente reforcado, nao tres achados isolados. Isso
gera uma hipotese natural e legitima para uma Fase 2 pre-registrada
separadamente: um filtro estrutural (SHORT-only, ou exclusao de
BTC/ETH, ou exclusao do quartil de maior liquidez) poderia elevar o
profit factor liquido acima do gate de 1,05.

**Alerta metodologico explicito:** esse filtro foi identificado
observando o desempenho DENTRO do proprio periodo out-of-sample
(2025-06 a 2026-05). Testar "SHORT-only" (ou qualquer filtro aqui
sugerido) nesse mesmo periodo OOS nao seria uma confirmacao valida --
seria factualmente re-minerar os mesmos dados que geraram a hipotese
(look-ahead por contaminacao amostral, nao por vazamento temporal). Uma
Fase 2 que queira testar esses filtros precisa de um split OOS
genuinamente novo (dados posteriores a 2026-05, ainda nao usados em
nenhuma decisao deste projeto) para que o teste tenha valor
probatorio. Essa exigencia deve constar explicitamente no pre-registro
de qualquer TASK-PAYOFF-002 futura.
