# Time-Series Momentum (Trend Following) Diagnostic

Diagnostic only, not a pre-registered backtest. Autonomous pivot after
cross-sectional momentum (12h-7d) and cross-sectional Z-score
micro-reversion (1h-4h) both aborted at the diagnostic stage this
session (see reports/zscore_diagnostic_tails.md). Tests whether an
asset's OWN trailing return predicts its OWN forward return
(time-series momentum), matched formation/holding horizon, on the
existing 20-symbol Sprint 7 dataset. No new data.

## Summary by window

| Window | Pooled corr(trailing, forward) | Pooled sign persistence | Continued move avg (bps) | Reversed move avg (bps) | Extreme-decile cutoff (bps) | Extreme-decile sign persistence | Extreme-decile directional forward (bps) | n |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 4h | -0.0054 | 0.4856 | 117.59 | 110.70 | 259.08 | 0.4658 | 0.67 | 525920 |
| 8h | -0.0142 | 0.4910 | 168.27 | 160.32 | 369.83 | 0.4657 | -8.04 | 525760 |
| 12h | -0.0170 | 0.4898 | 210.09 | 197.63 | 457.34 | 0.4604 | -9.15 | 525600 |
| 24h | -0.0307 | 0.4807 | 302.55 | 283.50 | 651.61 | 0.4421 | -29.96 | 525120 |

`Pooled sign persistence`: fraction of all (symbol, time) observations
where the forward return has the SAME sign as the trailing return
(trend continuation). 0.50 = coin flip (no time-series momentum or
reversal); >0.50 = momentum; <0.50 = reversal.

`Extreme-decile`: restricted to the top 10% largest |trailing return|
observations (pooled across symbols) -- the "real trend" subset the
TSMOM hypothesis actually targets, not small/noisy moves.
`Extreme-decile directional forward (bps)`: mean of sign(trailing_return) * forward_return for that subset -- positive
means the extreme trend, on average, continued in the same direction
by that many bps (this is the metric to compare against the 6.0bps
round-trip cost floor and the "300-500bps target" framing).

## Per-symbol detail (24h window)

```text
  symbol     n      corr  sign_persistence
 ADAUSDT 26256 -0.073067          0.483057
 APTUSDT 26256 -0.025778          0.487087
 ARBUSDT 26256 -0.024007          0.483918
ATOMUSDT 26256 -0.020146          0.487420
AVAXUSDT 26256 -0.010280          0.494077
 BCHUSDT 26256 -0.045221          0.465087
 BNBUSDT 26256 -0.041117          0.478688
 BTCUSDT 26256 -0.051297          0.476843
DOGEUSDT 26256  0.008067          0.478897
 DOTUSDT 26256 -0.009030          0.492624
 ETCUSDT 26256 -0.055128          0.480535
 ETHUSDT 26256 -0.021068          0.479071
LINKUSDT 26256 -0.036901          0.481297
 LTCUSDT 26256 -0.050817          0.468252
  OPUSDT 26256 -0.007035          0.483220
 SOLUSDT 26256 -0.032509          0.485506
 SUIUSDT 26256 -0.031767          0.474364
 TRXUSDT 26256 -0.043487          0.493427
 UNIUSDT 26256 -0.053395          0.472447
 XRPUSDT 26256 -0.043704          0.467983
```

## Conclusão (diagnóstico)

**O sinal encontrado é o oposto do que a hipótese TSMOM precisa, e piora
com a janela, não melhora.** Nos quatro horizontes testados (4h-24h):

- Correlação pooled entre retorno passado e futuro é negativa em todos os
  casos, e fica MAIS negativa conforme a janela aumenta (-0,005 em 4h ->
  -0,031 em 24h) -- o oposto de "diluir o atrito buscando alvos maiores";
  janelas mais longas mostram reversão mais forte, não tendência mais
  limpa.
- Sign persistence (fração de vezes que o retorno futuro tem o MESMO
  sinal do passado) fica sistematicamente abaixo de 50% em todas as
  janelas (48,1%-49,1%), e cai ainda mais no decil mais extremo de
  movimento passado (44,2%-46,6%) -- exatamente o subconjunto que a
  hipótese TSMOM precisaria que confirmasse continuação, e é o que mais
  reverte.
- A métrica econômica decisiva (retorno direcional médio no decil mais
  extremo) é positiva e desprezível em 4h (+0,67bps), depois vira
  negativa e cresce em magnitude: -8,04bps (8h), -9,15bps (12h), **-29,96
  bps (24h)**. Ou seja: seguir a tendência mais extrema em 24h teria um
  custo esperado de quase 30bps por operação, antes de qualquer taxa --
  o dobro da trava de custo de 6,0bps, na direção ERRADA.
- No detalhe por símbolo (janela 24h): **20 de 20 símbolos** mostram
  correlação negativa e sign persistence abaixo de 50% -- não é um
  resultado agregado distorcido por outliers, é unânime em todo o
  universo.

**Leitura:** neste dataset/universo, não há evidência de time-series
momentum em nenhum horizonte de 4h a 24h -- ao contrário, há reversão
fraca mas sistemática em nível de ativo individual, que se intensifica
com o horizonte. Isto é consistente com o padrão já observado nas outras
duas hipóteses de alta frequência testadas nesta sessão (Z-score
cross-sectional: lado short reverte, lado long não; e a extremidade de
24h aqui reforça esse mesmo viés de reversão-sobre-continuação em
criptoativos, mesmo fora do contexto cross-sectional). Recomendação:
**não avançar para pré-registro de TSMOM nestes horizontes** sem uma
decisão explícita do usuário sobre horizontes mais longos (semanas/meses,
já descartado por poder estatístico insuficiente na janela de 3 anos) ou
uma reformulação estrutural diferente.
