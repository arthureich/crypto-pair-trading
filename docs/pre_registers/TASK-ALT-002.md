# TASK-ALT-002 - Definicao e pre-registro: Diagnostico de Conteudo Informacional, Familia F (Open Interest)

## Status

DONE (definicao). Segunda task da Research Phase II, per o sequenciamento
ja acordado em ADR-0019 (G primeiro, F depois). Ver
`project_control/DECISIONS.md` ADR-0020.

## Workstream

Research Phase II - Alternative Information, Familia F (Open Interest).
Mesma natureza de TASK-ALT-001: DIAGNOSTICO de conteudo informacional,
nao estrategia -- sem gate economico, sem regra de trade.

## Fonte de dados (nova, pequena, ja confirmada disponivel)

```text
Familia `metrics` do bucket publico data.binance.vision (mesmo bucket
ja usado por src/research/historical_dataset.py, mas arquivos DIARIOS,
nao mensais -- a listagem mensal para esta familia esta vazia).
Colunas reais confirmadas (amostra real inspecionada, BTCUSDT
2025-06-01): create_time, symbol, sum_open_interest,
sum_open_interest_value, count_toptrader_long_short_ratio,
sum_toptrader_long_short_ratio, count_long_short_ratio,
sum_taker_long_short_vol_ratio -- granularidade de 5 minutos.
Cobertura confirmada (reconnaissance da task anterior) para todos os 20
symbols do universo, iniciando antes de 2023-06-01 para todos (o mais
recente, SUIUSDT, desde 2023-05-03).
Checksum sidecar (.CHECKSUM) confirmado no mesmo formato SHA256 hex já
usado e verificado pelo `verify_checksum_file` existente em
historical_dataset.py -- reusado sem modificacao.
```

## Escopo do novo download (autorizado pela sequencia ja acordada em
## ADR-0019 -- nao pede nova autorizacao)

```text
20 symbols x ~1096 dias (2023-06-01 a 2026-05-31) = ~21.920 arquivos
diarios pequenos (~12KB cada, ~260MB total) + seus .CHECKSUM. Nada
parecido com o problema de 17,98GB do bookTicker (Sprint 7). Download
memory-safe: um symbol por vez, resample para 1h e descarte do frame de
5min antes de passar ao proximo, para nunca acumular todo o dataset de
5min em memoria simultaneamente.
```

## Resample de 5min para 1h (para alinhar com o dataset horario ja
## existente)

```text
Para cada coluna de metrics, usar o ULTIMO valor observado dentro de
cada hora UTC (convencao "close," mesma logica de uma vela horaria
usar o ultimo preco observado) -- nao media, pois sum_open_interest e
uma variavel de ESTOQUE (nivel), nao de FLUXO.
```

## Natureza desta task: DIAGNOSTICO, nao estrategia

Mesmo padrao de TASK-ALT-001: sem gate de PASSA/NAO_PASSA de performance
economica. Resultado e "tem informacao" ou "nao tem informacao." Se
alguma feature mostrar informacao, desenhar uma estrategia em torno dela
e uma task separada (TASK-ALT-003 ou posterior), com seu proprio
pre-registro.

## Metodologia de diagnostico (reusa ADR-0019/TASK-ALT-001, nao
## re-decidida)

```text
Mesma infraestrutura generica (src/research/info_content.py): Spearman
rho + consistencia de sinal em 3 subperiodos cronologicos
nao-sobrepostos de ~12 meses (2023-06/2024-05, 2024-06/2025-05,
2025-06/2026-05) -- mesma particao ja usada em TASK-ALT-001, nao
reparticionada.

Criterio de "tem informacao" (identico a TASK-ALT-001, mesmo limiar,
nao ajustado por familia):
  |rho_amostra_completa| >= 0.03
  E sinal de rho consistente nos 3 subperiodos E na amostra completa

Horizonte de retorno futuro (target): forward_return[t,t+24h] =
log_price[t+24] - log_price[t] -- mesmo horizonte de TASK-ALT-001/
TASK-CS-002, reusado por consistencia.
```

## Features candidatas desta task (5, propostas pelo usuario em
## linguagem natural, formalizadas explicitamente ANTES do diagnostico
## rodar)

```text
1. oi_delta[t]: variacao do Open Interest nas ultimas 24h --
     oi_delta[t] = sum_open_interest[t] - sum_open_interest[t-24]

2. oi_volume_ratio[t]: Open Interest relativo ao volume negociado nas
   ultimas 24h (razao estoque/fluxo) --
     oi_volume_ratio[t] = sum_open_interest[t] / rolling_24h_quote_volume[t]
   (quote_volume ja existe no dataset normalizado -- nenhuma feature
   nova de preco/volume, so reuso de coluna ja existente combinada com
   o novo dado de OI)

3. oi_percentile[t]: percentil causal do OI atual relativo a sua
   propria historia recente de 90 dias --
     oi_percentile[t] = rank percentual causal de sum_open_interest[t]
     dentro de sum_open_interest.shift(1).rolling(2160h)

4. oi_acceleration[t]: variacao da variacao (2a diferenca) --
     oi_acceleration[t] = oi_delta[t] - oi_delta[t-24]

5. oi_price_divergence[t]: OI subindo (relativo a sua propria historia)
   enquanto preco NAO acompanha, ou vice-versa -- mesma formalizacao de
   funding_price_divergence (TASK-ALT-001), trocando funding por OI --
     price_return_24h[t] = log_price[t] - log_price[t-24]
     z_oi_delta[t] = oi_delta[t] normalizado
         (shift(1).rolling(2160h) mean/std do proprio oi_delta)
     z_price_return[t] = price_return_24h[t] normalizado
         (mesma normalizacao ja usada em TASK-ALT-001)
     oi_price_divergence[t] = z_oi_delta[t] - z_price_return[t]

Todas as 5 sao causais por construcao (shift(1) antes de qualquer
rolling, apenas dados conhecidos em t).
```

## Universo e amostra

```text
20 symbols do dataset ja normalizado (mesmo universo de toda a pesquisa
desta sessao). Painel empilhado (pooled), mesmo padrao de TASK-ALT-001.
```

## Invariantes obrigatorios

```text
- Toda feature usa shift(1) antes de qualquer rolling.
- O TARGET (retorno futuro) e o UNICO lugar onde dados posteriores a t
  sao usados.
- Nenhum gate de performance economica, custo, ou execucao nesta task.
- Os 3 subperiodos sao os MESMOS ja fixados em TASK-ALT-001 -- nao
  reparticionados.
- Download verificado por checksum SHA256 antes de qualquer uso dos
  dados (mesmo padrao de todo download anterior deste projeto -- fail
  closed em qualquer mismatch).
```

## Fora de escopo

```text
- Desenhar qualquer regra de entrada/saida/position sizing em torno de
  uma feature que mostrar informacao -- task separada.
- Qualquer outra feature de Open Interest alem das 5 formalizadas.
- Qualquer outro horizonte de retorno futuro alem de 24h.
- Reparticionar os subperiodos ou ajustar o limiar de 0,03.
- Mutual information ou qualquer estimador nao-linear.
- Familias H (Order Flow), I (Liquidation Dynamics, BLOCKED), J (Regime
  Detection) -- cada uma exige seu proprio pre-registro.
```
