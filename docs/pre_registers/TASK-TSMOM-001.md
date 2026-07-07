# TASK-TSMOM-001 - Seguidor de Tendencia Causal (Donchian Breakout + ATR Trailing Stop)

## Status

Pre-registrado, execucao autorizada explicitamente pelo usuario nesta
sessao (Fase 3 do pivot autonomo TSMOM), apesar do diagnostico anterior
(`reports/tsmom_diagnostic.md`) ter recomendado NAO avancar sem decisao
explicita.

## Por que isto nao e uma reabertura do teste ja abortado

`reports/tsmom_diagnostic.md` testou uma proxy simples: retorno passado
(janela W) prediz retorno futuro (MESMA janela W, holding period FIXO).
Esse teste mostrou reversao fraca e sistematica (sign persistence <50% em
todas as janelas, piorando com o horizonte). A estrategia aqui e
estruturalmente diferente: holding period VARIAVEL (saida por trailing
stop, nao por horizonte fixo), payoff potencialmente assimetrico (perdas
pequenas e rapidas via stop, ganhos que "surfam" a tendencia sem alvo
fixo). O diagnostico anterior nao mede -- e nao pode medir -- essa
assimetria especifica. Isto e uma hipotese nova, nao uma re-tentativa da
mesma configuracao ja abortada.

## Escolha da janela (feita ANTES de rodar este backtest)

O diagnostico reportou, por janela, a razao entre o movimento medio
quando a tendencia continua (`continued_abs_bps`) e quando reverte
(`reversed_abs_bps`):

```text
4h:  117.59 / 110.70 = 1.062
8h:  168.27 / 160.32 = 1.050
12h: 210.09 / 197.63 = 1.063
24h: 302.55 / 283.50 = 1.067  <- ESCOLHIDA
```

**Nota de honestidade metodologica:** as quatro razoes sao muito
proximas entre si (1.05-1.07x) -- nao ha uma janela claramente superior
no diagnostico anterior. A escolha de 24h e defensavel (maior razao,
maior magnitude absoluta, mais folga sobre o custo de 12bps), mas nao e
um sinal fortemente diferenciado. Isto e registrado aqui para que o
resultado do backtest completo nao seja lido como confirmando uma escolha
"obviamente correta" de janela -- foi a melhor entre opcoes semelhantes,
nao uma vencedora clara.

## Hipotese pre-registrada

### Universo e dados

Os mesmos 20 simbolos do dataset ja normalizado da Sprint 7
(`sprint7_binance_usdm_202306_202605_bars.csv.gz`), 2023-06-01 a
2026-05-31, barras horarias. Usa `high`/`low`/`close` reais (nao
`log_price`), ja presentes no dataset -- nenhum novo download.

### Sinal de entrada (causal, Donchian breakout)

```text
donchian_high[t] = max(high[t-24:t-1])   (24 barras anteriores, EXCLUINDO t)
donchian_low[t]  = min(low[t-24:t-1])

LONG entry  se close[t] > donchian_high[t]
SHORT entry se close[t] < donchian_low[t]

Apenas uma posicao por simbolo por vez (sem pyramiding). Uma entrada so
pode ocorrer quando o simbolo esta FLAT.
```

### ATR (14 periodos, causal)

```text
true_range[t] = max(high[t]-low[t], |high[t]-close[t-1]|, |low[t]-close[t-1]|)
atr[t] = media móvel simples de true_range sobre as 14 barras
         ANTERIORES a t (shift(1), nao inclui a barra t)
```

Media movel simples, nao a suavizacao exponencial classica de Wilder --
simplificacao explicita, documentada.

### Saida (trailing stop, SEM profit target fixo)

```text
LONG:  running_max_close = max(close desde a entrada até t, inclusive)
       stop_level[t] = running_max_close[t] - 3 * atr[t]
       Sai quando close[t] <= stop_level[t]

SHORT: running_min_close = min(close desde a entrada até t, inclusive)
       stop_level[t] = running_min_close[t] + 3 * atr[t]
       Sai quando close[t] >= stop_level[t]
```

`atr[t]` no stop usa o ATR CORRENTE (recalculado a cada barra, causal),
nao o ATR fixado no momento da entrada -- o stop se adapta a volatilidade
atual. Posicao ainda aberta no fim do dataset e marcada `OPEN_AT_END`,
excluida das metricas resolvidas (nao fabrica um preco de saida).

### Tamanho de posicao (inversamente proporcional a volatilidade)

```text
peso_i = (1 / atr_pct_entrada_i) / media(1 / atr_pct_entrada em todos os trades)
atr_pct_entrada_i = atr_na_entrada_i / preco_de_entrada_i
```

Peso medio normalizado para 1.0. Ativos mais volateis na entrada recebem
peso menor. PnL de portfolio = soma ponderada do retorno percentual de
cada trade.

### Custo (pre-registrado, conservador)

```text
cost_bps_roundtrip = 12.0 (Taker-Taker duplo, pior cenario -- sem desconto
                            de maker, ao contrario do funding carry)
```

Custo fixo deduzido do retorno bruto de cada trade resolvido, nao do
book de portfolio (cada trade e independente no tempo, nao um
rebalanceamento periodico sincronizado).

### Gate (pre-registrado, binario, decidido antes de rodar)

```text
PASSA se, no agregado dos 20 simbolos:
  net_profit_factor >= 1.20  E  win_rate >= 30%

Nenhum parametro (janela, multiplicador de ATR, custo, limiar de gate)
muda depois de ver o resultado.
```

## Invariantes obrigatorios

```text
- Donchian channel e ATR usam estritamente dados até t-1 (shift(1)),
  nunca a barra t -- verificado por teste dedicado.
- Trailing stop nunca fecha uma posicao usando preco futuro -- o stop e
  avaliado bar-a-bar, sequencialmente, no fechamento de cada barra.
- Posicao aberta no fim do dataset nunca e fabricada como fechada.
- Apenas uma posicao por simbolo por vez.
```

## Fora de escopo

```text
- Novo download de dados.
- Reutilizacao literal de execution_simulator.py (pair-based, beta-weighted,
  incompativel com uma estrategia de single-asset trailing-stop) -- este
  modulo usa o mesmo PADRAO de backtest causal candle-level ja estabelecido
  (triple_barrier.py / funding_carry.py fase 1), nao o simulador tick-level
  de pares.
- Otimizacao de qualquer parametro apos ver o resultado.
- Paper/live trading, alavancagem, ML.
```
