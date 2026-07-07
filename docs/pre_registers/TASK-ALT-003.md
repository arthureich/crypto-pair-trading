# TASK-ALT-003 - Definicao e pre-registro: Diagnostico de Conteudo Informacional, Familia J (Regime Detection)

## Status

DONE (definicao e execucao). Terceira task da Research Phase II, aberta apos
`TASK-ALT-001` (Funding Structure) e `TASK-ALT-002` (Open Interest)
fecharem sem informacao pelo criterio pre-registrado. Ver
`project_control/DECISIONS.md` ADR-0021.

## Workstream

Research Phase II - Alternative Information, Familia J (Regime Detection).
Esta familia e a excecao explicita ja aceita em ADR-0019: pode usar
features derivadas de OHLCV porque nao afirma descobrir alpha nem gera
trades. O objetivo e medir se variaveis de contexto/regime carregam
informacao sobre risco/volatilidade futura, para eventualmente
condicionar outras estrategias em uma task separada.

## Natureza desta task: DIAGNOSTICO de regime, nao estrategia

Sem regra de entrada, saida, sizing, hedge, filtro operacional, ML, XGBoost
ou backtest economico. O resultado e "tem informacao de regime" ou "nao
tem informacao de regime" para as features abaixo. Se alguma feature
mostrar informacao, qualquer uso operacional dela exige uma task futura,
com pre-registro proprio e sem reutilizar esta mesma execucao como gate de
estrategia.

## Alvo desta task: risco/volatilidade futura, nao retorno direcional

Para preservar a natureza de Regime Detection como camada de contexto, o
target desta task NAO e o retorno futuro assinado usado nas Familias G e F.
O target e:

```text
future_abs_return_24h[t] = abs(log_price[t+24h] - log_price[t])
```

Isso mede intensidade de movimento/risco realizado nas proximas 24h, nao
direcao de trade. Portanto um eventual resultado positivo nao autoriza
SignalIntent, nao define lado long/short e nao pode ser lido como alpha
direcional.

## Metodologia de diagnostico

Reusa a infraestrutura generica de ADR-0019/TASK-ALT-001:

```text
Metrica primaria: Spearman rho entre feature causal[t] e
future_abs_return_24h[t].

Estabilidade: mesmas 3 janelas cronologicas nao-sobrepostas ja fixadas:
  2023-06/2024-05
  2024-06/2025-05
  2025-06/2026-05

Criterio de "tem informacao de regime":
  |rho_amostra_completa| >= 0.03
  E sinal de rho consistente nos 3 subperiodos E na amostra completa

O limiar de 0.03, a metrica Spearman e as janelas nao sao re-decididos
para esta familia.
```

## Features candidatas desta task (6, formalizadas antes do diagnostico)

Todas as features sao derivadas do dataset horario ja normalizado e sao
causais por construcao:

```text
1. realized_vol_24h[t]:
   desvio padrao dos retornos horarios conhecidos antes de t:
     return_1h = log_price.diff(1)
     realized_vol_24h[t] = return_1h.shift(1).rolling(24h).std()

2. realized_vol_168h[t]:
   mesma metrica em janela de 7 dias:
     realized_vol_168h[t] = return_1h.shift(1).rolling(168h).std()

3. trend_intensity_168h[t]:
   intensidade absoluta de tendencia de 7 dias, normalizada por
   volatilidade realizada, sem sinal direcional:
     past_return_168h[t] = log_price[t] - log_price[t-168h]
     trend_intensity_168h[t] =
       abs(past_return_168h[t]) / (realized_vol_168h[t] * sqrt(168))

4. volume_shock_24h[t]:
   choque causal de volume negociado relativo ao proprio historico:
     quote_volume_24h[t] = quote_volume.shift(1).rolling(24h).sum()
     log_volume_24h[t] = log1p(quote_volume_24h[t])
     volume_shock_24h[t] =
       z-score causal de log_volume_24h com janela de 90 dias

5. market_dispersion_24h[t]:
   dispersao cross-sectional do retorno de 24h dos 20 symbols no tempo t:
     return_24h_symbol[t] = log_price_symbol[t] - log_price_symbol[t-24h]
     market_dispersion_24h[t] = std_cross_section(return_24h_symbol[t])

6. market_abs_return_24h[t]:
   movimento absoluto do mercado agregado no tempo t:
     market_return_24h[t] = mean_cross_section(return_24h_symbol[t])
     market_abs_return_24h[t] = abs(market_return_24h[t])
```

Duas features sao de contexto de mercado agregado (`market_dispersion_24h`
e `market_abs_return_24h`) e quatro sao de contexto por symbol. Nenhuma
delas carrega lado direcional.

## Universo e amostra

```text
20 symbols do dataset normalizado Sprint 7:
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz

Painel empilhado (pooled), mesmo padrao de TASK-ALT-001/TASK-ALT-002.
Nenhum novo download.
```

## Invariantes obrigatorios

```text
- Nenhuma feature usa dados posteriores a t.
- Rollings por symbol usam shift(1) antes da janela quando calculam
  estatistica baseada em retornos/volume historico.
- O unico dado futuro e o target future_abs_return_24h, usado apenas para
  medir conteudo informacional.
- Nenhum resultado desta task autoriza trade, filtro operacional, sizing,
  hedge, emergency exit ou alteracao do Execution Plane.
- Nenhum arquivo de ledger, execution live engine, recovery ou ML pode ser
  alterado nesta task.
```

## Fora de escopo

```text
- Retorno futuro assinado como target direcional.
- Criar estrategia, filtro de entrada, filtro de saida ou position sizing.
- Reaproveitar resultado como gate economico.
- Adicionar features alem das 6 pre-registradas.
- Mudar horizonte de 24h, limiar 0.03, subperiodos ou metrica primaria.
- Familias H (Order Flow/L2), I (Liquidation Dynamics) ou follow-up do
  near-miss funding_price_divergence.
```
