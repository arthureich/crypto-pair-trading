# TASK-ALT-010 - Definicao e pre-registro: fluxo cross-venue -- dispersao de funding entre exchanges (Coinalyze free tier)

## Status

ACCEPTED (locked) - travado 2026-07-12 antes de analisar qualquer download.
Sob ADR-0030. Diagnostico de conteudo informacional (estilo Fase II), sem
gate economico. Segunda metade da trilha gratuita escolhida pelo usuario
(a 1a, on-chain/ALT-009, fechou nula). Chave Coinalyze fornecida pelo
usuario, em `.env` (gitignored, nunca commitada).

## Motivacao e dado

Chave verificada e schema reconhecido (sem analise comitada):
- `/v1/future-markets` e `/v1/funding-rate-history` (retorna
  `[{symbol, history:[{t,o,h,l,c}]}]`; `c` = funding rate do intervalo).
  Codigos de venue: A=Binance, 6=Bybit, 3=OKX, 4=Huobi, 0=BitMEX.
- Cobertura dos nossos 20 base-assets, perpetuos USDT nas venues majors
  {Binance, Bybit, OKX, Huobi, BitMEX}: todo asset tem 4-5 dessas venues.

Prior DIVULGADO: funding single-venue (G/ALT-001), OI (F/ALT-002) e fluxo
agregado (E/FC-II-004) TODOS deram SEM_INFO. A aposta aqui e especifica:
que a DISCORDANCIA cross-venue (dispersao do funding entre exchanges)
carregue informacao que nenhuma venue isolada carregou -- prior MODERADO,
nao alto. Divulgado antes de rodar.

## Metodologia (reusa ADR-0019 / info_content.py, frequencia diaria)

```text
Target: forward_return_h[D] = log_price_diario[D+h] - log_price_diario[D],
  h in {1d, 3d} (funding e liquidado a cada 8h e a dispersao decai rapido
  -> horizontes CURTOS; raciocinio divulgado). Grid: 3 features x 2
  horizontes = 6 celulas.
3 subperiodos (2023-06/2024-05, 2024-06/2025-05, 2025-06/2026-05) e limiar
|rho| >= 0,03 identicos a Fase II; sinal consistente nos 3 subperiodos e a
defesa pre-comprometida contra multiple-testing.
Preco diario: resample do bar horario sprint7 (ultimo por dia UTC).
Janela 2023-06-01..2026-05-31.
Se alguma feature passar, teste economico descritivo antes de qualquer
pre-registro de estrategia -- informacao != edge.
```

## Features candidatas (LOCKED, 3, causais, diarias)

```text
Venue set (FIXO): {Binance, Bybit, OKX, Huobi, BitMEX}, perpetuos USDT.
Estatistica cross-venue por (asset, dia) exige >= 3 venues presentes
naquele dia, senao NaN (descartada).

1. xvenue_funding_disp_z[D] = z-score causal do DESVIO-PADRAO cross-venue
   do funding diario (sinal central de "venues discordam").
2. xvenue_funding_range_z[D] = z-score causal de (max - min) cross-venue.
3. xvenue_funding_mean_z[D] = z-score causal da MEDIA cross-venue do funding
   (carry agregado; DIVULGADO como quase-sobreposicao com o funding
   single-venue ja nulo -- incluida como referencia/controle, nao aposta
   nova).

Causalidade: shift(1) diario em todas as features (metrica do dia anterior);
z-scores usam shift(1).rolling(90d). O TARGET e o unico dado posterior a D.
```

## Universo e amostra

```text
20 base-assets, perpetuos USDT, 4-5 venues majors cada. Painel diario
empilhado por (asset, dia UTC). Preco diario do sprint7 (ja em disco).
Download via Coinalyze free tier (chave em .env); paginacao/batch por
grupos de simbolos; fail-closed em erro HTTP.
```

## Invariantes

```text
- Features causais (shift(1) diario antes de qualquer rolling).
- Target e o unico dado posterior a D.
- Subperiodos e limiar 0,03 nao reparticionados/re-tunados.
- Sem gate economico no diagnostico; sem estrategia/execucao/acao real.
- Grid de 6 celulas fixo antes de analisar o download; hit passa pelo teste
  economico descritivo antes de virar candidato a estrategia (task
  separada, pre-registrada, com OOS).
- Chave NUNCA commitada (.env gitignored); custo ZERO (free tier).
- Venue set e regra ">=3 venues" fixos antes do resultado.
```

## Fora de escopo

```text
- Estrategia sobre um hit (task separada com OOS; execucao cross-venue e
  build maior).
- Metricas Coinalyze pagas / alta-frequencia; OI agregado (poderia ser
  follow-up se a dispersao de funding pintar algo).
- Options/VRP (pivo de instrumento -- decisao separada).
- Horizontes alem de {1d,3d}; mutual information / nao-linear; ensemble.
```
