# TASK-ALT-009 - Definicao e pre-registro: Familia G (On-Chain) na camada gratuita Coin Metrics community

## Status

ACCEPTED (locked) - travado 2026-07-12 antes de analisar qualquer download.
Sob ADR-0029. Diagnostico de conteudo informacional (estilo Fase II), sem
gate economico. Primeira familia de DADO EXTERNO testada -- e de custo ZERO
(API community keyless). O usuario escolheu esta trilha no brief de
viabilidade: provar sinal numa fatia gratis ANTES de pagar por feed maior.

## Motivacao e dado

On-chain e a #2 do relatorio externo. A camada community da Coin Metrics
expoe, keyless, a 1d, para os nossos 20 base-assets (reconnaissance de
catalogo, sem analise comitada):

- Fluxos de exchange (`FlowInExNtv`/`FlowOutExNtv`) -- sinal on-chain de
  maior prior na literatura -- so BTC e ETH (2/20).
- `CapMVRVCur` (MVRV) 12/20; `AdrActCnt` 13/20; `TxCnt` 13/20;
  `SplyCur` 12/20 -- painel diario multi-asset real.
- Metricas mais ricas (`TxTfrValAdjUSD`, `SplyActEver`, `CapRealUSD`) sao
  premium (HTTP 403) -- fora de escopo num teste de custo zero.

Fluxo cross-venue (a outra metade da trilha escolhida) exige chave
Coinalyze/Coinglass que o ambiente nao tem -> adiado para follow-up
key-gated (TASK-ALT-010), nao bloqueia esta metade keyless.

## Metodologia (reusa ADR-0019 / info_content.py, adaptada a frequencia diaria)

```text
Target: forward_return_h[D] = log_price_diario[D+h] - log_price_diario[D],
  h in {1d (resolucao diaria mais fina), 7d (swing semanal -- on-chain e
  lento)}. Grid pre-comprometido: 4 features x 2 horizontes = 8 celulas.
3 subperiodos (2023-06/2024-05, 2024-06/2025-05, 2025-06/2026-05) e limiar
|rho| >= 0,03 identicos a Fase II; sinal consistente nos 3 subperiodos e a
defesa pre-comprometida contra multiple-testing.
Preco diario: resample do bar horario sprint7 existente (ultimo por dia
UTC). Janela 2023-06-01..2026-05-31 (mesmos 3 subperiodos de tudo).
Se alguma feature passar, aplicar o teste economico descritivo antes de
qualquer pre-registro de estrategia -- informacao != edge.
```

## Features candidatas (LOCKED, 4, causais, diarias)

```text
1. mvrv_z[D] = z-score causal de CapMVRVCur
   (valuation; hipotese: MVRV alto -> retorno futuro negativo,
   mean-reversion de valuation.) Painel ~12 assets.
2. active_addr_growth_z[D] = z-score causal da variacao diaria de AdrActCnt
   (momentum de adocao/atencao.) Painel ~13 assets.
3. tx_count_growth_z[D] = z-score causal da variacao diaria de TxCnt
   (momentum de uso da rede.) Painel ~13 assets.
4. exchange_netflow_z[D] = z-score causal de
   (FlowInExNtv - FlowOutExNtv) / SplyCur
   (entrada em exchange = pressao de venda, baixista.) SO BTC/ETH --
   FLAG explicito: breadth cross-sectional baixo (2 assets); reportado
   como obs diarias pooled, NAO lido como resultado cross-sectional.

Causalidade: a metrica on-chain do dia D so e finalizada apos D fechar;
a decisao no inicio de D+1 pode usar a metrica de D. Aplico shift(1) diario
a TODAS as features (metrica do dia anterior), garantindo que a feature
antecede a janela do retorno. z-scores usam shift(1).rolling(90d) do
proprio asset. O TARGET e o unico dado posterior a D.
```

## Universo e amostra

```text
Ate 20 base-assets, coberto por metrica (12-13 para as broad; 2 para
fluxos de exchange). Painel diario empilhado por (asset, dia UTC).
Preco diario do sprint7 (ja em disco). Download on-chain: pequeno
(~13 assets x ~4 metricas x ~1095 dias) via API community keyless.
```

## Invariantes

```text
- Features causais (shift(1) diario antes de qualquer rolling).
- Target e o unico dado posterior a D.
- Subperiodos e limiar 0,03 nao reparticionados/re-tunados.
- Sem gate economico no diagnostico; sem estrategia/execucao/acao real.
- Grid de 8 celulas fixo antes de analisar o download; qualquer hit passa
  pelo teste economico descritivo antes de virar candidato a estrategia
  (task separada, pre-registrada, com OOS).
- Custo ZERO: so a camada community keyless; nenhuma metrica premium;
  nenhuma compra de feed.
```

## Fora de escopo

```text
- Fluxo cross-venue / dispersao de funding / OI agregado (exige chave
  gratuita Coinalyze/Coinglass): TASK-ALT-010, key-gated, quando a chave
  existir.
- Metricas premium da CM (TxTfrValAdjUSD, SplyActEver, CapRealUSD, SOPR).
- Options/VRP (decisao de instrumento separada -- brief de viabilidade).
- Estrategia sobre um hit (task separada com OOS).
- Horizontes alem de {1d,7d}; mutual information / nao-linear; ensemble
  multivariado.
```
