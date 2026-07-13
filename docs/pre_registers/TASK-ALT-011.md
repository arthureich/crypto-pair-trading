# TASK-ALT-011 - Definicao e pre-registro: Familia F (Options) -- DVOL/VRP como PREDITOR (free, Deribit)

## Status

ACCEPTED (locked) - travado 2026-07-12 antes de analisar qualquer download.
Sob ADR-0032. Diagnostico de conteudo informacional (estilo Fase II), sem
gate economico, SEM pivo de instrumento (Angle B). Custo ZERO (API publica
Deribit, sem chave). Usuario escolheu Angle B (preditor) no fork da familia.

## Revisao de literatura (grounding)

- "Risk Premia in the Bitcoin Market" (arXiv 2410.15195, 2024): VRP positivo e
  persistente; fatores option-implied (esp. vol-of-vol) preveem retorno
  excedente do BTC.
- Atanasova et al. (SSRN 6771170; "Illiquidity Premium and Crypto Option
  Returns"): premios de risco implicitos em opcoes BTC; retornos delta-hedged.
- Deribit/pratica: VRP ~+15 pontos de vol em contango; DVOL = "VIX cripto"
  (IV 30d anualizada). Evidencia a mais forte de todas as familias (#1).
- Dado FREE: API publica Deribit `get_volatility_index_data` (DVOL OHLC
  diario), sem auth; BTC e ETH desde 2023-06 (reconnaissance confirmou).

## Hipotese economica (clara)

Sinais option-implied (nivel de DVOL e o premio de risco de variancia
VRP = IV^2 - RV^2) carregam informacao DIRECIONAL sobre o retorno futuro de
BTC/ETH -- coerente com a literatura de que fatores implicitos preveem retorno
excedente. Se sim, viram feature(s) candidatas para a estrategia de PERP
existente (sem abrir livro de opcoes).

## Metodologia (reusa ADR-0019 / info_content.py, frequencia diaria)

```text
Target: forward_return_h[D] = log_price_diario[D+h] - log_price_diario[D],
  h in {7d, 30d} (sinal option-implied e lento; 30d casa com o tenor do DVOL;
  7d = swing). Grid: 4 features x 2 horizontes = 8 celulas.
3 subperiodos (2023-06/2024-05, 2024-06/2025-05, 2025-06/2026-05) e limiar
|rho| >= 0,03 identicos a Fase II; sinal consistente nos 3 subperiodos e a
defesa pre-comprometida contra multiple-testing.
Preco diario: resample do bar horario sprint7 (BTCUSDT, ETHUSDT). DVOL diario:
download da API publica Deribit. Janela 2023-06-01..2026-05-31.
```

## Features candidatas (LOCKED, 4, causais, diarias)

```text
Universo: BTC e ETH (unicos com DVOL liquido). Painel pooled 2 assets --
FLAG explicito: breadth cross-sectional baixo (2 assets), como o
exchange_netflow da ALT-009; reportado como obs diarias pooled, NAO
resultado cross-sectional.

RV = vol realizada anualizada de 30d (retornos diarios trailing, sqrt(365)).
DVOL em pontos de vol anualizada (%/100 para casar com RV).

1. dvol_z[D]        = z-score causal do nivel de DVOL.
2. vrp_z[D]         = z-score causal de (DVOL^2 - RV^2)  (premio de variancia).
3. dvol_change_z[D] = z-score causal da variacao diaria de DVOL (choque de vol).
4. iv_rv_ratio_z[D] = z-score causal de DVOL/RV (forma alternativa do VRP).

Causalidade: DVOL[D] e observavel de mercado conhecido em D; ainda assim
aplico shift(1) diario (como ALT-009) para conservadorismo/consistencia; todo
z-score usa shift(1).rolling(90d). O TARGET e o unico dado posterior a D.
```

## Invariantes

```text
- Features causais (shift(1) diario antes de qualquer rolling).
- Target e o unico dado posterior a D.
- Subperiodos e limiar 0,03 nao reparticionados/re-tunados.
- Sem gate economico no diagnostico; SEM pivo de instrumento; sem estrategia.
- Grid de 8 celulas fixo antes de analisar o download; hit passa pelo teste
  economico descritivo antes de virar feature de estrategia (task separada).
- Custo ZERO: so a API publica Deribit, sem chave; sem dado pago.
```

## Fora de escopo

```text
- VRP harvesting / venda de variancia (Angle A -- pivo de instrumento, decisao
  do usuario).
- Skew / risk-reversal 25-delta / superficie (exige a cadeia de opcoes, mais
  pesado) -- follow-up se o DVOL pintar algo.
- Dado de opcoes pago (Tardis/Amberdata).
- Horizontes alem de {7d,30d}; mutual information / nao-linear.
- Promocao / estrategia (task separada, pre-registrada, com OOS).
```
