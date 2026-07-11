# TASK-FC-II-007 - Definicao e pre-registro: Stress de custo realista do TSM vol-targeted

## Status

ACCEPTED (locked) - travado 2026-07-11 antes de qualquer resultado. Sob
ADR-0027. Analise de SENSIBILIDADE (nao tuning) do TASK-FC-II-005; in-sample,
descritiva. Decide se o lead do TSM sobrevive a custo realista antes de
gastar esforco de OOS.

## Motivacao

O TSM vol-targeted (FC-II-005) deu Sharpe 1,04 in-sample com 6bps/leg, e a
robustez (FC-II-006) foi ampla. Mas a licao #1 do projeto e que **custo mata
coisas** (Sprint 8->9), e horizonte/rebalance curto = turnover. 6bps/leg e o
constante conservador do projeto, mas um livro L/S de 20 alts-perp inclui
nomes menos liquidos (taker + slippage reais podem ser maiores). Antes de OOS,
mapear a curva de degradacao por custo e o breakeven.

## Metodologia (sensibilidade, NAO tuning)

```text
Reusa run_tsm_trend_backtest com os params LOCKED do FC-II-005 (28d/7d/5d),
variando SO cost_bps_per_leg numa grade fixa:
  {0, 3, 6, 10, 15, 20, 30, 50} bps/leg.
Reporta, para cada custo: Sharpe anualizado, net PnL, e o net PnL do baseline
buy-and-hold (invariante a custo, referencia).
Reporta o CUSTO DE BREAKEVEN de net PnL: cost_bps* = gross_net_pnl(0) * 1e4 /
turnover_total (onde a estrategia deixa de ser lucrativa).
NAO se escolhe um custo para "passar" -- reporta-se a curva inteira e o
breakeven. E stress, nao selecao.
```

## Criterio (descritivo -- decide se persegue OOS)

```text
Banda de custo REALISTA pre-declarada para alt-perps L/S: 10-15 bps/leg
(taker ~5bps + slippage em nomes menos liquidos, ida+volta amortizada).
- SOBREVIVE (merece OOS): Sharpe > baseline E net PnL > 0 a 15 bps/leg.
- MARGINAL: sobrevive so ate ~10 bps.
- MORRE: breakeven < ~6 bps (o proprio constante conservador ja o mata).
Nenhum veredito de promocao; so a decisao de perseguir OOS.
```

## Invariantes

```text
- Params do sinal LOCKED (so o custo varia). Nada re-tunado para melhorar.
- Curva inteira + breakeven reportados (sem cherry-pick de custo).
- In-sample, descritivo; sem gate de promocao; sem acao real.
```

## Fora de escopo

```text
- Ajustar params do TSM para reduzir turnover/custo (seria curve-fit; task
  separada se justificado).
- OOS/estrategia/promocao (task separada se sobreviver).
```
