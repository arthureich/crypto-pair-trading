# TASK-ALT-013 - Definicao e pre-registro: VRP como OVERLAY/feature no book de perp (blend VRP + TSM)

## Status

ACCEPTED (locked) - travado 2026-07-12 antes de qualquer implementacao. Sob
ADR-0032 (Familia F). Testa o melhor uso do sinal VRP indicado pela ALT-012:
FEATURE/overlay, nao trade standalone. Blend equal-risk SEM knob; sem re-tune;
dev != promocao (OOS-gated).

## Motivacao

ALT-011 achou o VRP como sinal real (info + economia bruta); ALT-012 mostrou
que como trade long/short standalone semanal ele NAO_PASSA (drawdown-heavy,
inconsistente). A conclusao registrada foi: VRP e melhor como FEATURE/overlay.
Esta task testa isso da forma mais limpa e consistente com o que ja existe:
adicionar o stream de retorno do VRP-timing (BTC/ETH) como uma perna
DIVERSIFICANTE ao TSM (o lead do projeto), via o mesmo diagnostico de blend
equal-risk da Linha 5 (TASK-TSM-005, trend+carry).

## Hipotese economica (clara)

Trend (TSM, 20 perps) e VRP (premio de variancia BTC/ETH) capturam premios
distintos e provavelmente pouco correlacionados. Mesmo o VRP-timing sendo
modesto sozinho (Sharpe ~0,49), se for pouco correlacionado com o TSM um blend
equal-risk pode melhorar o Sharpe/drawdown do TSM (diversificacao) -- exatamente
o mecanismo que funcionou no trend+carry.

## Metodologia

```text
Streams de P&L semanais (dev 2023-06..2026-05), reusa src/research/tsm_ensemble:
  - TSM: net por rebalance (run_tsm_trend_backtest, include_funding), -> weekly.
  - VRP: strat_net do VRP-timing PRIMARIO long/short sign(vrp_z) da ALT-012
    (run_vrp_timing_backtest, VrpTimingConfig default), -> weekly.
Blend equal-risk 50/50 (padronizado a unit-vol), via blend_diagnostic.
Metricas: Sharpe anualizado de TSM/VRP/blend; correlacao; max drawdown.
Robustez: mesma decomposicao por 3 subperiodos da Linha 5.
```

## Celula primaria (LOCKED, exatamente 1)

```text
Blend equal-risk 50/50 TSM + VRP-timing(primario long/short). Exatamente 1
variante. USA o VRP primario long/short da ALT-012 (NAO o long-only descritivo
-- evita cherry-pick ex-post). Sem grade de pesos.
```

## Criterio de decisao (dev)

```text
CANDIDATO A OOS somente se: Sharpe do blend > Sharpe do TSM sozinho, CONSISTENTE
nos 3 subperiodos, com correlacao baixa E maxDD do blend <= TSM. Caso contrario:
REJEITADO -- o VRP nao melhora o book nem como overlay; documentado, encerra a
exploracao gratis do VRP (restam skew/superficie e Angle A, decisoes do
usuario). Sem promocao; OOS-gated.
```

## Invariantes / Fora de escopo

```text
- Blend equal-risk sem knob; usa streams de backtests ja testados, inalterados;
  VRP primario (nao o long-only) para evitar selecao ex-post.
- Padronizacao usa vol dev (sizing in-sample; diagnostico dev, nao promocao).
- Dev != promocao; OOS-gated.
- FORA: otimizacao de alocacao; VRP long-only (pre-registro proprio se
  desejado); skew/superficie; Angle A (livro de opcoes); acao real.
```
