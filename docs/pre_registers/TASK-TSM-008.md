# TASK-TSM-008 - Definicao e pre-registro: TSM combinado ERC + volatility targeting

## Status

ACCEPTED (locked) - travado 2026-07-13 antes de qualquer implementacao. Sob
ADR-0031. Sintese das DUAS melhorias que passaram limpo no dev (ERC/TSM-003 e
vol-targeting/TSM-007). Dev != promocao (OOS-gated). Params dos componentes
FIXOS (herdados de TSM-003 e TSM-007, sem re-tune); sem secundario ex-post.

## Motivacao (por que NAO e data-snooping)

Duas melhorias INDEPENDENTES ja passaram a bateria de robustez sozinhas:
- ERC (TSM-003): realoca risco CROSS-SECTIONAL (entre pernas) via equal risk
  contribution -- Sharpe 0,970->1,039.
- Vol-targeting (TSM-007): escala a exposicao TEMPORAL (no tempo) pela vol
  realizada do proprio livro -- Sharpe 0,970->1,107.
Sao MECANISMOS ORTOGONAIS (secao transversal vs serie temporal). Combina-los e
a sintese natural e principled -- nao uma busca cega: cada um foi validado
antes de ver este teste. Bounded search: esta e UMA variante combinada
pre-declarada, elegivel a OOS.

## Hipotese economica (clara)

Como ERC (diversifica risco entre pernas) e vol-targeting (estabiliza risco no
tempo) atacam fontes de risco diferentes, aplicados juntos devem melhorar as
metricas ajustadas ao risco MAIS que qualquer um isolado -- OU, se forem
redundantes, o combinado ~= o melhor isolado (e ai a parcimonia manda ficar com
o isolado).

## Metodologia

```text
Pipeline combinado (reusa modulos ja testados, SEM novo alfa):
  1. ERC book: run_tsm_trend_backtest(bars, TsmTrendConfig(include_funding=True,
     portfolio_erc=True)) -> stream de retorno net por rebalance.
  2. Combinado: apply_vol_target(erc_net) (overlay TSM-007, W=12, CAP=3.0,
     alvo=media expanding; causal).
Comparacao (4 variantes, na mesma janela dev 2023-06..2026-05):
  - base (nem ERC nem vol-target)
  - ERC-only
  - vol-target-only (apply_vol_target(base))
  - COMBINADO (ERC + vol-target)  <- celula primaria
Metricas: Sharpe anualizado, max drawdown, net; bateria (subperiodo, custo,
funding, regime BTC).
```

## Celula primaria (LOCKED, exatamente 1)

```text
COMBINADO = ERC + vol-targeting, params herdados (nao re-tunados). 1 variante.
Sem grade; sem escolha de W/CAP/janela por desempenho aqui.
```

## Criterio de decisao (dev)

```text
CANDIDATO A OOS (combinado preferido) somente se: Sharpe(combinado) > Sharpe do
MELHOR componente isolado (vol-target ~1,107) E maxDD nao pior, CONSISTENTE nos
3 subperiodos E ambos regimes BTC. 
Se combinado ~= melhor isolado (sem ganho material alem do melhor componente):
NAO promover o combinado -- por PARCIMONIA fica-se com o melhor isolado
(vol-target), e o combinado e documentado como "sem ganho incremental".
Se combinado < melhor isolado: REJEITADO. Sem promocao; OOS-gated.
```

## Bateria de robustez (TODAS; padrao ADR-0031)

```text
subperiodo / custo / funding / regime BTC / drawdown / simplicidade-vs-ganho
(combinar 2 overlays e mais complexo -> o ganho tem que justificar) /
falso-positivo (ganho consistente, nao concentrado).
```

## Invariantes / Fora de escopo

```text
- Componentes com params fixos (herdados); sem re-tune; sem secundario ex-post.
- Base TSM intacta; combinado composto de flags/overlays ja testados.
- Causal (ERC covariancia shift(1); vol-target shift(1)); dev != promocao;
  OOS-gated.
- FORA: re-otimizar W/CAP/janela de covariancia; empilhar mais overlays;
  Kelly; skew/surface (paid); acao real.
```
