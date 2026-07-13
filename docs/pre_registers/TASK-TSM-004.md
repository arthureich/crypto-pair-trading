# TASK-TSM-004 - Definicao e pre-registro: Linha 4 (meta-labeling / ML como FILTRO de operacoes) sobre o TSM

## Status

ACCEPTED (locked) - travado 2026-07-12 antes de qualquer implementacao. Sob
ADR-0031 (Programa de Melhoria do TSM), Linha 4. Dev != promocao (OOS-gated).
Modelo, features, threshold e CV CONGELADOS antes de qualquer fit; sem
re-tune; sem promover secundario ex-post.

## Revisao de literatura (grounding)

- Meta-labeling (Lopez de Prado, 2018; Hudson & Thames "Does Meta-Labeling
  Add to Signal Efficacy?"): um modelo SECUNDARIO decide QUANDO seguir as
  apostas de um modelo primario (aqui o TSM define a direcao), filtrando
  falsos positivos -> melhora precisao/F1 e metricas ajustadas ao risco.
  Aplicavel a trend following (primario = trend; secundario = trade/no-trade).
- Precedente INTERNO decisivo (cautela divulgada): TASK-ML-001 aplicou
  meta-labeling ao funding carry com harness cuidadoso (purged+embargoed CV)
  e produziu MIRAGEM in-sample (PF medio "melhor" 4,99 = inflacao de razao;
  3 de 5 folds pioravam). Licao: em edge fino e dado cripto sobreposto, ML
  fabrica "passes" ilusorios. Portanto esta task MINIMIZA graus de liberdade.

## Hipotese economica (clara)

O TSM aposta em todas as pernas com trend, inclusive as de baixa conviccao
que fazem whipsaw. Um filtro secundario que preve P(perna lucrativa no hold)
e descarta as de baixa probabilidade deveria remover falsos positivos ->
melhor Sharpe/PF e menor drawdown. (E o mesmo espirito da Linha 1, mas
aprendido por ML por perna, nao um gate de regime agregado.)

## Metodologia (minimal-DoF; reusa purged_cv.py)

```text
Painel de pernas: para cada rebalance t e cada symbol no book do TSM base,
uma amostra com features causais conhecidas em t e label binario:
  label = 1 se a contribuicao da perna no hold e > 0
        = (sign(trailing_i[t]) * forward_return_i[t]) > 0
  (i.e., o trend acertou a direcao naquela perna naquele hold.)

Features (FROZEN, causais, from first principles -- 6, sem busca):
  1. strength_i = |trailing_i|/vol_i (conviccao risco-ajustada da perna)
  2. vol_i (nivel de risco da perna)
  3. trailing_i (retorno de formacao com sinal)
  4. aggregate_strength (media cross-sectional de strength -- contexto do book)
  5. btc_trailing (retorno trailing 28d do BTC -- regime de mercado)
  6. xs_rank(strength_i) (rank cross-sectional da conviccao no rebalance)
Todas conhecidas ao decidir a posicao em t; target e o unico dado posterior.

Modelo (FROZEN, exatamente 1 -- sem grade): sklearn GradientBoostingClassifier
com hiperparametros default fixos (n_estimators=100, max_depth=3), features
padronizadas quando aplicavel. UMA classe de modelo, para evitar a inflacao
de mirage do grid de 24 celulas da ML-001.

Threshold (FROZEN, knob-free): manter a perna se P(label=1) >= 0,5 (regra
natural, sem escolha de threshold por desempenho). Pernas mantidas sao
re-normalizadas a unit-gross (isola SELECAO de sizing).

Validacao: purged + embargoed walk-forward CV (purged_walk_forward_splits),
embargo = 1 hold (120h). Predicoes OUT-OF-FOLD formam o keep-mask; o backtest
do TSM base e re-rodado com o mask (novo parametro keep_mask, default None ->
base intacta). Comparar TSM filtrado vs base na bateria de robustez.
Relatorio no estilo ML-001: tabela POR FOLD (nao so a media), pois a media
esconde mirage.
```

## Celula primaria (LOCKED, exatamente 1)

```text
Filtro meta-label GB default, threshold 0,5, re-normalizado unit-gross,
avaliado por purged walk-forward CV out-of-fold. 1 variante; sem grade de
modelos/thresholds/features.
```

## Bateria de robustez (TODAS; ADR-0031 regra 5) + guarda anti-mirage

```text
1-8 identicas as tasks anteriores (subperiodo/custo/funding/regime BTC/
drawdown/simplicidade/economia/falso-positivo).
GUARDA EXTRA (licao ML-001): reportar metrica POR FOLD; se a melhoria vier de
poucos folds com PnL minusculo (inflacao de razao) ou nao for consistente na
maioria dos folds -> MIRAGEM -> rejeitar. ML e a Linha de MAIOR complexidade
e menor prior; a barra de "simplicidade vs ganho" e a mais alta.
```

## Criterio de decisao (dev)

```text
CANDIDATO A OOS somente se: melhora Sharpe E nao piora maxDD vs base, de forma
CONSISTENTE na maioria dos folds E nos 3 subperiodos E ambos regimes BTC, sem
assinatura de mirage (ganho difuso, nao 1-2 folds), E o ganho justifica a
complexidade de um modelo ML. Caso contrario: REJEITADO/CAUTELAR, encerrado
com resultado documentado, seguir para a Linha 5 (ensemble). Sem promocao;
gate BLOQUEADO ate OOS novo (como ML-001).
```

## Invariantes

```text
- Modelo/features/threshold/CV congelados antes do fit; sem re-tune; sem
  secundario ex-post.
- Base TSM intacta (keep_mask default None).
- Causal (features conhecidas em t; label = unico dado posterior; CV purgado
  + embargo do horizonte de hold).
- Dev != promocao; gate BLOQUEADO ate OOS novo.
- so pesquisa/paper, nada real.
```

## Fora de escopo

```text
- Grade de modelos/hiperparametros/thresholds (viola minimal-DoF).
- ML gerando direcao/sinal (meta-labeling e SO filtro; direcao vem do TSM).
- Deep learning / features exoticas.
- Promocao / OOS (gate separado quando houver dado novo).
```
