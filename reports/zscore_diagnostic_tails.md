# Z-Score Cross-Sectional Reversion: Tail Diagnostic

Diagnostic only, not a pre-registered backtest. Answers whether the
reversion signal observed informally this session strengthens at more
extreme |Z| thresholds, whether long/short sides are asymmetric, and
whether the extreme tail is dominated by a handful of high-vol symbols.

## Full slice table

```text
formation forward  threshold     side     n  mean_bps  median_bps  frac_positive
       1h      1h        2.0 COMBINED 28039  0.870888    4.475024       0.524626
       1h      1h        2.0     LONG 12040  0.709823    1.173757       0.506894
       1h      1h        2.0    SHORT 15999  0.992098    7.351053       0.537971
       1h      1h        2.5 COMBINED 12646  1.775996    7.815481       0.535031
       1h      1h        2.5     LONG  4934  2.328153    3.103249       0.514187
       1h      1h        2.5    SHORT  7712  1.422737   10.914213       0.548366
       1h      1h        3.0 COMBINED  5334  1.642899   10.863795       0.542557
       1h      1h        3.0     LONG  1830  3.006190    6.272486       0.519126
       1h      1h        3.0    SHORT  3504  0.930907   14.594358       0.554795
       1h      1h        3.5 COMBINED  1771  4.278939   17.475025       0.560136
       1h      1h        3.5     LONG   499 -1.824770    0.067492       0.501002
       1h      1h        3.5    SHORT  1272  6.673396   23.066906       0.583333
       2h      1h        2.0 COMBINED 28223  0.620518    4.713511       0.526556
       2h      1h        2.0     LONG 11699  0.491852    1.906396       0.510215
       2h      1h        2.0    SHORT 16524  0.711614    7.328205       0.538126
       2h      1h        2.5 COMBINED 12809  0.115153    6.422608       0.530408
       2h      1h        2.5     LONG  4660 -0.100241    1.040882       0.506438
       2h      1h        2.5    SHORT  8149  0.238327   10.623321       0.544116
       2h      1h        3.0 COMBINED  5472 -1.220656    9.112528       0.536915
       2h      1h        3.0     LONG  1682  1.033417    2.827167       0.510702
       2h      1h        3.0    SHORT  3790 -2.221013   12.885999       0.548549
       2h      1h        3.5 COMBINED  1814  0.721033   12.177358       0.541345
       2h      1h        3.5     LONG   466 -2.797878    0.161682       0.502146
       2h      1h        3.5    SHORT  1348  1.937511   18.832724       0.554896
```

## Symbol concentration in the |Z| > 3.0 tail (formation=1h)

```text
symbol
SUIUSDT     1011
APTUSDT      509
BCHUSDT      497
UNIUSDT      484
OPUSDT       360
DOGEUSDT     299
AVAXUSDT     268
LINKUSDT     247
```

## Volatility-scaling check

corr(cross-sectional Z, asset's-own-30d-vol-scaled return) = 0.4476

## Observação não-decisória: assimetria Long/Short

A tabela mostra uma assimetria real e monotônica entre os lados, que a
regra de decisão (COMBINED) dilui: o lado SHORT (desvanecer picos de alta,
Z >> 0) fortalece de forma consistente conforme o limiar sobe -- mediana
7.35 -> 10.91 -> 14.59 -> 23.07 bps e frac_positive 53.8% -> 54.8% ->
55.5% -> 58.3% (1h formação) conforme |Z| vai de 2.0 a 3.5. O lado LONG
(apostar em "dead cat bounce" após queda, Z << 0) não mostra o mesmo
padrao e degrada no limiar mais extremo (mean vira negativo, -1.82bps;
frac_positive cai para 50.1%, essencialmente ruido, com amostra pequena,
n=499). Isto sugere que desvanecer picos de alta extremos e
mecanicamente mais consistente que apostar em recuperacao apos quedas
extremas neste universo/janela -- o oposto da hipotese original do
usuario ("recuo apos queda abrupta costuma ser mais consistente"). Esta
observacao NAO altera a decisao (a regra pre-registrada usa a metrica
COMBINED, nao o lado SHORT isoladamente) e nao autoriza, por si so, um
novo pre-registro so-SHORT sem uma decisao explicita do usuario.

A concentracao de simbolos na cauda extrema (4 de 20 simbolos respondem
por 47% de todas as observacoes |Z|>3.0) e a correlacao moderada (0,4476,
nao alta) entre o Z cross-sectional e o retorno escalado pela volatilidade
propria do ativo sao consistentes com a hipotese do usuario: parte
relevante da cauda "extrema" e simplesmente ruido idiossincratico cronico
de um pequeno grupo de simbolos mais volateis (SUIUSDT, APTUSDT, BCHUSDT,
UNIUSDT), nao um choque de mercado amplo.

## Decision

Primary test: formation=1h, forward=1h, |Z|>3.0, COMBINED long+short mean reversion = 1.643 bps (bar = 10.0 bps).

**DECISION: ABORT**
