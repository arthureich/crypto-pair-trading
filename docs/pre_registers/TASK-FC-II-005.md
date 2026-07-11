# TASK-FC-II-005 - Definicao e pre-registro: Time-Series Momentum CLASSICO vol-targeted (distinto do TSMOM Donchian)

## Status

ACCEPTED (locked) - travado 2026-07-11 antes de qualquer resultado. Sob
ADR-0027. Backtest de desenvolvimento na janela existente; SEM veredito de
promocao (gate real, se aplicavel, em OOS). E o unico retest barato que
sobra na familia PRECO.

## Motivacao

Um survey externo da literatura (2020-2026, Man AHL et al.) ranqueia TSM
alto, atribuindo a rentabilidade ao **volatility-targeting**, nao a forca
bruta do sinal. O nosso TASK-TSMOM-001 (Donchian breakout + ATR trailing
stop) falhou por drawdown ~10x o lucro -- MAS nao era TSM classico e NAO
tinha vol-targeting. O TSM classico (posicao = sinal do retorno trailing,
tamanho ~ 1/vol) e uma construcao GENUINAMENTE nao-testada no projeto, em
dado que ja temos (OHLCV). Prior honesto-baixo (a familia preco esta toda
nula), mas e a peca que o survey diz ser a chave e que nunca rodamos.

## Especificacao (LOCKED, sem varredura)

```text
Universo: 20 symbols, bars horarios sprint7 (2023-06/2026-05).
Sinal (por symbol, causal): sign(log_price[t] - log_price[t-LOOKBACK]),
  LOOKBACK = 672h (28 dias -- o horizonte "metabolismo rapido" do survey).
Vol (causal): desvio-padrao do retorno horario, shift(1).rolling(168h).
Peso por perna: raw_i = sign_i / vol_i; normalizado por rebalanceamento
  para sum_i |peso_i| = 1 (gross unitario -> SEM knob de alavancagem;
  inverse-vol/"risk-parity trend"). Exposicao liquida = sum_i peso_i (a
  aposta direcional do TSM). Vol_i indefinido/<=0 -> perna peso 0.
Rebalanceamento/hold: a cada HOLD = 120h (5 dias).
PnL do intervalo: sum_i peso_i * (log_price[t+HOLD] - log_price[t]).
Custo: sum_i |peso_i(t) - peso_i(t-1)| * COST_BPS/1e4, COST_BPS = 6,0/leg
  (mesmo custo conservador do backtest canonico). net = gross - custo.
Variante descritiva (nao decide): long-only (sign clamp a {0,+1}), pois o
  survey diz que a perna curta em bear e arriscada.
Baseline: buy-and-hold equal-weight dos 20 symbols, mesma grade de rebalance.
```

## Criterio (desenvolvimento, descritivo -- sem veredito)

```text
A afirmacao do survey e sobre RISCO-AJUSTADO. Reporta-se, na janela de
desenvolvimento (nao e promocao):
  - Sharpe anualizado (TSM vs baseline),
  - max drawdown (TSM vs baseline),
  - net PnL, turnover.
Leitura: o TSM vol-targeted bate o buy-and-hold em Sharpe E tem drawdown
menor? Se nem no dev set melhorar risco-ajustado sobre o baseline, fecha a
familia preco definitivamente. Se melhorar, e CANDIDATO a OOS (task
separada) -- nunca um veredito aqui, e sujeito a custo realista.
```

## Invariantes

```text
- Sinal e vol causais (vol usa shift(1) antes do rolling; sinal usa lag).
- O TARGET (retorno futuro do intervalo) e o unico dado posterior a t.
- Params LOCKED (LOOKBACK/VOL_WINDOW/HOLD/COST) -- nao varridos apos ver
  resultado. Sem gate economico "de promocao" no dev; sem acao real.
- Gross unitario (sem alavancagem tunavel).
```

## Fora de escopo

```text
- Varrer LOOKBACK/HOLD/target (seria multiple-testing/curve-fit).
- Estrategia/OOS/promocao (task separada se o dev for promissor).
- Outras familias; dado externo.
```
