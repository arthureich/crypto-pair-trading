# TASK-TSM-010 - Definicao e pre-registro: generalizacao MULTI-UNIVERSO do TSM base (params fixos)

## Status

ACCEPTED (locked) - travado 2026-07-16 antes de baixar/analisar dado novo. Sob
ADR-0031. VALIDACAO de generalizacao (nao refinamento). O achado mais importante
do projeto ate aqui e que o TSM base generalizou para uma universe diferente sem
mudar parametro (TASK-TSM-009); esta task ESCALA essa evidencia para MULTIPLOS
universos tematicos. Config FIXA, ZERO re-tune, mesmo codigo.

## Motivacao

Breadth de validacao > +0,2 de Sharpe na mesma universe. O objetivo e poder
afirmar honestamente: "TSM base testado em N universos tematicos distintos,
params fixos, sem retuning, Sharpe positivo na maioria." Isso ataca overfitting
por replicacao out-of-sample no espaco de ATIVOS (complementar ao OOS temporal
do paper-forward).

## Hipotese

O edge do TSM BASE (sign(retorno trailing 28d), inverse-vol, unit-gross, 5d,
com funding) e uma propriedade GERAL de perps cripto liquidos -> em varios
universos tematicos (large caps, mid/alt, DeFi, gaming, old-guard/payments,
etc.) deve entregar Sharpe POSITIVO e bater o buy-and-hold na maioria.

## Metodologia

```text
Universos tematicos (Binance USDM perps, long history >= 2023-06; coverage gate
95% da janela 2023-06..2026-05). Baskets pre-declarados por TEMA (nao por
desempenho). Cada basket roda o TSM BASE (primario) + combinado (secundario,
referencia -- ja sabemos que os overlays sao universe-specific, TSM-009) +
buy-and-hold equal-weight.
Dado: pipeline historical_dataset, klines + fundingRate (unicas familias que o
TSM usa), download best-effort POR SIMBOLO (um simbolo que falhe/nao exista nao
derruba o basket; coverage gate filtra). Custo ZERO (Binance public).
Metricas por universo: Sharpe anualizado (base/combined/buy-hold), maxDD, net.
Headline: em quantos dos N universos o TSM base tem Sharpe > 0 E > buy-and-hold.
Limitacao HONESTA divulgada: AI e memecoins recentes (listados 2023-2024) NAO
tem historico de 3 anos -> nao testaveis nesta janela; a validacao cobre os
temas com historico longo.
```

## Celula primaria (LOCKED)

```text
TSM BASE (config FIXA FC-II-008) em cada universo tematico. Sem re-tune, sem
escolha de simbolos por desempenho (temas + coverage gate definem a inclusao).
Universos-alvo (>=5 simbolos cada apos o gate): large-cap, mid/alt-L1, DeFi,
gaming/metaverse, old-guard/payments, e o mid-tier de TSM-009 (referencia).
```

## Criterio de decisao

```text
GENERALIZA FORTE se o TSM base tem Sharpe > 0 E > buy-and-hold na GRANDE MAIORIA
(>= ~80%) dos universos testados -> forte evidencia de edge geral, param-fixo,
multi-universo. Universos onde falha sao registrados honestamente (nao
escondidos) e caracterizados (tema/periodo). NAO e promocao live; e evidencia
de breadth que aumenta a confianca no core.
```

## Invariantes / Fora de escopo

```text
- Config base FIXA (FC-II-008); ZERO re-tune; symbols so por tema + coverage.
- Best-effort por simbolo (falha de download != selecao por performance).
- Causal; custo ZERO (Binance public); dev-window de outras universes (nao OOS
  temporal -> nao promove live).
- FORA: otimizar params por universo; AI/meme sem historico; outras EXCHANGES
  (proxima prioridade do usuario, task propria); outras CLASSES de ativo (idem).
```
