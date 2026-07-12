# TASK-ALT-008 - Definicao e pre-registro: fechar a varredura de familias em dado publico -- Familia B (forma da volatilidade por range) e Familia C (iliquidez de Amihud)

## Status

ACCEPTED (locked) - travado 2026-07-11 antes de qualquer resultado. Sob
ADR-0028. Diagnostico de conteudo informacional (estilo Fase II), sem
gate economico. Fecha as duas familias que o ledger marcava so como
"~Concluida", cada uma testada ate aqui por UMA lente, nao a direcional.

## Motivacao e dado

O relatorio externo lista premio de iliquidez (Amihud) e estimadores de
volatilidade por range entre as familias de fator. No projeto elas estao
"~Concluida" por um motivo honesto e especifico:

- Familia B (Volatilidade) foi avaliada como sinal de RISCO (vol realizada
  preve vol futura / regime -- Familia J), nunca como sinal DIRECIONAL de
  retorno via estimadores de range limpos. O OHLC das barras em disco
  suporta Parkinson / Rogers-Satchell e a posicao-de-fechamento intrabar
  (onde dentro do range high-low a barra fechou) -- um proxy de pressao
  estilo candlestick, nunca testado aqui.
- Familia C (Liquidez) foi fechada via `depth_concentration` do livro
  (dado da Familia H), nunca via a Amihud canonica derivada de barra
  (|retorno| / volume-em-dolar), turnover, ou tamanho medio de trade -- os
  construtos de premio de liquidez que o relatorio cita.

Sao os ultimos diagnosticos direcionais genuinamente NAO rodados em dado
GRATIS. Custo zero, sem download. Prior BAIXO (coerente com todo o resto
em dado publico) -- por isso e um diagnostico limitado, nao um build de
estrategia.

## Metodologia (reusa ADR-0019 / info_content.py)

```text
Target: forward_return_h[t] = log_price[t+h] - log_price[t], para
  h in {24h (padrao Fase II), 4h (curto -- microestrutura/liquidez,
  lição da TASK-FC-II-003)}.
Grid pequeno pre-comprometido: 6 features x 2 horizontes = 12 celulas.
3 subperiodos (2023-06/2024-05, 2024-06/2025-05, 2025-06/2026-05) e limiar
|rho| >= 0,03 identicos a Fase II; sinal consistente nos 3 subperiodos e a
defesa pre-comprometida contra multiple-testing.
Se alguma feature passar, aplicar o MESMO teste economico descritivo da
TASK-FC-II-003 (spread bruto por decil vs custo) antes de qualquer
pre-registro de estrategia -- informacao != edge.
```

## Features candidatas (LOCKED, 6, causais, so barra)

```text
Familia B (forma da volatilidade):
1. parkinson_range_z[t] = z-score causal de
   (1/(4 ln 2)) * (ln(high[t]/low[t]))^2   (magnitude do range)
2. rogers_satchell_z[t] = z-score causal do estimador RS por barra
   ln(high/close)*ln(high/open) + ln(low/close)*ln(low/open)
   (vol robusta a drift; magnitude)
3. close_location_in_range[t] = (close[t]-low[t]) / (high[t]-low[t]) - 0.5
   (pressao direcional intrabar; -0.5..+0.5; UNICA feature B direcional)

Familia C (liquidez/iliquidez):
4. amihud_illiq_z[t] = z-score causal de |return_1h[t]| / quote_volume[t]
   (iliquidez de Amihud: quanto o preco anda por dolar negociado)
5. turnover_z[t] = z-score causal de quote_volume[t]
   (volume/atencao vs sua propria media movel)
6. trade_size_z[t] = z-score causal de quote_volume[t]/number_of_trades[t]
   (tamanho medio de trade; footprint institucional)

Todas causais: valores conhecidos ao FECHAR a barra t; todo z-score usa
shift(1) antes do rolling (janela 2160h, identica a FC-II-004). O TARGET e
o unico dado posterior a t. close_location_in_range nao e z-scored (ja e
limitado e centrado).
```

## Universo e amostra

```text
20 symbols; barras sprint7 (2023-06..2026-05); painel empilhado por
(symbol, open_time). Bars ja normalizados em disco; sem novo download.
```

## Invariantes

```text
- Features causais (z-scores shift(1) antes de rolling; close-location
  usa apenas OHLC da propria barra t).
- Target e o unico dado posterior a t.
- Subperiodos e limiar 0,03 nao reparticionados/re-tunados.
- Sem gate economico no diagnostico; sem estrategia/execucao/acao real.
- Grid de 12 celulas fixo antes do resultado; qualquer hit passa pelo
  teste economico descritivo antes de virar candidato a estrategia
  (task separada, pre-registrada, com OOS).
- Sem novo download.
```

## Fora de escopo

```text
- Estrategia sobre um hit (task separada com OOS).
- Familias de dado EXTERNO (opcoes/VRP, on-chain, fluxo cross-venue): sao
  decisao de investimento do usuario; um brief de viabilidade
  (fontes/custo, sem baixar nada) sera escrito a parte -- ponto de PARADA.
- Horizontes alem de {24h,4h}; mutual information / nao-linear; ensemble
  multivariado; VWAP/volume-profile (alto risco de overfit / dado extra).
```
