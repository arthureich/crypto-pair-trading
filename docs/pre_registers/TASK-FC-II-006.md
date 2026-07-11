# TASK-FC-II-006 - Definicao e pre-registro: Robustez do TSM vol-targeted (decomposicao subperiodo / perna / regime)

## Status

ACCEPTED (locked) - travado 2026-07-11 antes de qualquer resultado. Sob
ADR-0027. Decomposicao DESCRITIVA in-sample do resultado do TASK-FC-II-005;
sem gate/veredito. Objetivo: decidir se o lead do TSM merece o pipeline de
OOS ou se e fragil (concentrado num regime/perna).

## Motivacao

O TASK-FC-II-005 (TSM classico vol-targeted) deu, na janela de dev, Sharpe
1,04 vs buy-hold -0,14 e maxDD 0,35 vs 1,38 -- o primeiro lead risco-
ajustado positivo do projeto. MAS o long-only deu Sharpe ~0, ou seja, a
perna SHORT carrega o resultado. Isso levanta a hipotese de que o edge e so
"shortar alts no trecho de baixa" da janela -- dependente de regime, o tipo
de coisa que falha OOS. Antes de gastar qualquer esforco de OOS, decompor.

## Metodologia (descritiva, in-sample, reusa a serie por-rebalance do FC-II-005)

```text
Reutiliza run_tsm_trend_backtest (params LOCKED do FC-II-005). Tres cortes:

1. SUBPERIODO: Sharpe, net PnL e maxDD do TSM em cada um dos 3 subperiodos
   fixos (2023-06/2024-05, 2024-06/2025-05, 2025-06/2026-05). Edge robusto
   => positivo e estavel nos 3; fragil => concentrado em um.

2. PERNA: contribuicao cumulativa da perna LONG vs perna SHORT para o net
   PnL do MESMO livro (pesos normalizados identicos; long_sleeve +
   short_sleeve = gross por construcao). Pergunta: a short carrega tudo?

3. REGIME: classificar cada rebalance pelo sinal do retorno trailing 28d do
   BTCUSDT ("BTC up" vs "BTC down"). Sharpe e net PnL do TSM em cada regime.
   Se o edge so existe em "BTC down", e uma aposta de bear disfarcada.
```

## Criterio (descritivo -- decide o proximo passo, nao promove)

```text
Edge AMPLO (merece OOS): net PnL positivo nos 3 subperiodos E a perna long
contribui materialmente (nao e ~so short) E ha performance em ambos os
regimes (nao so BTC-down).
Edge CONCENTRADO/FRAGIL (nao gastar OOS agora): performance so num
subperiodo, ou ~inteiramente da perna short, ou so em BTC-down.
Nenhum veredito de promocao aqui; so a decisao de perseguir OOS ou nao.
```

## Invariantes

```text
- Reusa exatamente os params e a serie causal do FC-II-005 (nada re-tunado).
- Regime BTC usa retorno trailing (causal, conhecido no rebalance).
- Descritivo, in-sample; sem gate economico de promocao; sem acao real.
```

## Fora de escopo

```text
- Ajustar params do TSM em resposta a este corte (seria curve-fit).
- OOS/estrategia/promocao (task separada, se o edge for amplo).
- Outras familias.
```
