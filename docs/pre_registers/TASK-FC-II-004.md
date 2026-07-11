# TASK-FC-II-004 - Definicao e pre-registro: Familia E (Fluxo) -- agressor taker + razoes long/short, ja em disco

## Status

ACCEPTED (locked) - travado 2026-07-11 antes de qualquer resultado. Sob
ADR-0027. Diagnostico de conteudo informacional (estilo Fase II), sem
gate economico. Adota o esquema de "familias de informacao": esta e a
Familia E (Fluxo/Order Flow agregado por barra).

## Motivacao e dado

Fluxo de agressor (taker buy/sell) e posicionamento (long/short ratios)
sao areas de alto prior na literatura e na pratica de fundos. E o dado
JA ESTA EM DISCO, nunca testado:
- Bars sprint7: `taker_buy_quote_volume`, `quote_volume`,
  `number_of_trades` (fracao de volume agressor-comprador).
- Arquivo `metrics` (baixado para OI, TASK-ALT-002): 
  `sum_taker_long_short_vol_ratio`, `sum_toptrader_long_short_ratio`,
  `count_long_short_ratio` -- so as features de OI foram usadas; as
  razoes long/short ficaram intocadas.
Custo zero, sem download.

## Metodologia (reusa ADR-0019 / info_content.py)

```text
Target: forward_return_h[t] = log_price[t+h] - log_price[t], para
  h in {24h (padrao Fase II), 4h (curto -- fluxo e microestrutura,
  lição da TASK-FC-II-003)}. Grid pequeno pre-comprometido: 5 features x
  2 horizontes = 10 celulas.
3 subperiodos e limiar 0,03 identicos a Fase II; sinal consistente nos 3
subperiodos e a defesa contra multiple-testing.
Se alguma feature passar, aplicar o MESMO teste economico descritivo da
TASK-FC-II-003 (spread bruto por intervalo vs custo) antes de qualquer
pre-registro de estrategia -- informacao != edge.
```

## Features candidatas (LOCKED, 5, causais)

```text
1. taker_buy_fraction[t] = taker_buy_quote_volume[t] / quote_volume[t]
   (fracao do volume da barra que foi agressor-comprador; conhecido ao
   fechar a barra t, causal.)
2. taker_buy_fraction_z[t] = z-score causal de (1)
   (shift(1).rolling(2160h) mean/std do proprio symbol.)
3. taker_lsv_ratio_z[t] = z-score causal de sum_taker_long_short_vol_ratio
4. toptrader_ls_ratio_z[t] = z-score causal de sum_toptrader_long_short_ratio
5. global_ls_ratio_z[t] = z-score causal de count_long_short_ratio

Todas causais: valores conhecidos em t; z-scores usam shift(1) antes do
rolling. O TARGET e o unico dado posterior a t. As razoes de metrics sao
alinhadas aos bars por (symbol, open_time), identico a TASK-ALT-002.
```

## Universo e amostra

```text
20 symbols; painel empilhado; join bars x metrics por (symbol, open_time).
```

## Invariantes

```text
- Features causais (z-scores shift(1) antes de rolling).
- Target e o unico dado posterior a t.
- Subperiodos e limiar 0,03 nao reparticionados/re-tunados.
- Sem gate economico no diagnostico; sem estrategia/execucao/acao real.
- Grid de 10 celulas fixo antes do resultado; qualquer hit passa pelo
  teste economico descritivo antes de virar candidato a estrategia
  (que seria task separada, pre-registrada, com OOS).
- Sem novo download.
```

## Fora de escopo

```text
- Estrategia sobre um hit (task separada com OOS).
- Range-vol (Parkinson/GK/YZ), Amihud, VWAP, volume profile -- familias
  separadas (C liquidez / B volatilidade), prior "risco/contexto"; ficam
  para tasks proprias se esta abrir apetite.
- Horizontes alem de {24h,4h}; mutual information / nao-linear; ensemble
  multivariado (task separada, alto risco de overfit).
```
