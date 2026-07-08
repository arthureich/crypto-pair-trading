# TASK-ALT-007 - Definicao e pre-registro: Diagnostico de Conteudo Informacional, Familia H (Order Flow / Book Depth)

## Status

DONE (definicao). Aprovado explicitamente pelo usuario nesta sessao
antes de qualquer codigo ser escrito. Ver `project_control/DECISIONS.md`
ADR-0025.

## Workstream

Research Phase II - Alternative Information, Familia H (Order
Flow/L2), a ultima familia candidata original (ADR-0019) que ainda nao
havia sido executada -- estava deliberadamente adiada por custo/gap de
dado, ate a reconnaissance desta task encontrar uma fonte viavel.

## Por que Familia H deixa de ser "cara" agora (reconnaissance real,
## nao suposicao herdada de sessoes anteriores)

Sessoes anteriores (Sprint 7/9/10) usaram `bookTicker` (top-of-book
tick-a-tick) como fonte de L2: 17,98GB para UM UNICO MES (Junho/2023,
15 symbols), e o Sprint 7 (TASK-007-10) confirmou um GAP DE COBERTURA
real -- `bookTicker` nao existe para nenhum symbol de 2024-04 em
diante. Essa combinacao (caro + com buraco) e o motivo pelo qual
Familia H ficou deliberadamente adiada em toda a Research Phase II
ate agora.

Nesta task, uma reconnaissance real (probes de leitura contra
`data.binance.vision`, sem download comitado) encontrou uma familia
DIFERENTE: `bookDepth` -- profundidade agregada por faixa percentual de
distancia do mid-price (-5%, -4%, -3%, -2%, -1%, -0,2%, +0,2%, +1%,
+2%, +3%, +4%, +5%), amostrada por evento (nao a cada tick, mas quando
o livro muda o suficiente -- ~2.660 amostras/dia para BTCUSDT).
Confirmado:

```text
- Cobertura CONTINUA desde antes de 2023-06-01 (o symbol mais recente,
  SUIUSDT, desde 2023-05-03) ate pelo menos 2026-06 (verificado por
  HEAD request direto), sem o gap do bookTicker.
- Tamanho real por dia por symbol: ~432KB a ~515KB comprimido (amostra
  de 4 symbols, liquidos e menos liquidos).
- Estimativa para os 3 anos inteiros, 20 symbols: ~10,2GB -- MENOR que
  os 17,98GB que o bookTicker custou para UM UNICO MES.
- Mesmo formato de `.CHECKSUM` (SHA256 hex) ja usado e verificado por
  `verify_checksum_file` em `historical_dataset.py` -- reusado sem
  modificacao.
```

Isto NAO e L2 tick-a-tick puro (nao da para reconstruir o livro exato
book-by-book), mas e uma representacao agregada e genuina da forma do
livro -- suficiente para medir pressao/imbalance/profundidade, sem o
custo/risco de memoria do tick-a-tick.

## Natureza desta task: DIAGNOSTICO, nao estrategia

Mesmo padrao de `TASK-ALT-001/002`: sem gate de PASSA/NAO_PASSA de
performance economica. O resultado e "tem informacao" ou "nao tem
informacao," per criterios fixados abaixo. Se alguma feature mostrar
informacao, desenhar uma estrategia em torno dela e uma task separada,
com seu proprio pre-registro.

## Metodologia de diagnostico (reusa integralmente ADR-0019, nao
## redesenhada)

```text
Correlacao de Spearman + consistencia de sinal em 3 subperiodos
cronologicos NAO-SOBREPOSTOS de ~12 meses (2023-06/2024-05,
2024-06/2025-05, 2025-06/2026-05) -- mesma particao ja usada em
TASK-ALT-001/002.

Criterio de "tem informacao" (identico, nao ajustado por familia):
  |rho_amostra_completa| >= 0,03
  E sinal de rho consistente nos 3 subperiodos E na amostra completa

Horizonte de retorno futuro (target): forward_return[t,t+24h] =
log_price[t+24] - log_price[t] -- mesmo horizonte de TASK-ALT-001/002,
reusado por consistencia entre familias, NAO re-escolhido para esta
familia especificamente (mesmo que a intuicao de microestrutura
sugerisse um horizonte mais curto -- isso fica registrado como
limitacao explicita, nao como ajuste feito para esta task).
```

## Resample de eventos irregulares para 1h (alinhar com o dataset
## horario ja existente)

```text
Para cada symbol e cada percentual, usar o ULTIMO snapshot observado
dentro de cada hora UTC -- mesma convencao "close" ja usada para Open
Interest (TASK-ALT-002) e para o proprio log_price.
```

## Features candidatas desta task (5, formalizadas explicitamente ANTES
## do diagnostico rodar)

```text
Notacao: notional_bid_Xpct[t] = notional na faixa percentual -X (lado
comprador, precos abaixo do mid); notional_ask_Xpct[t] = notional na
faixa +X (lado vendedor, precos acima do mid). Ambos apos o resample
horario (ultimo valor na hora).

1. book_imbalance_1pct[t]: imbalance de profundidade perto do topo --
     book_imbalance_1pct[t] = (notional_bid_1pct[t] - notional_ask_1pct[t])
                               / (notional_bid_1pct[t] + notional_ask_1pct[t])

2. book_imbalance_5pct[t]: imbalance de profundidade mais larga --
     book_imbalance_5pct[t] = (notional_bid_5pct[t] - notional_ask_5pct[t])
                               / (notional_bid_5pct[t] + notional_ask_5pct[t])

3. depth_concentration[t]: quanto da liquidez esta perto do topo vs
   espalhada --
     depth_concentration[t] = (notional_bid_1pct[t] + notional_ask_1pct[t])
                               / (notional_bid_5pct[t] + notional_ask_5pct[t])

4. depth_change_24h[t]: choque de liquidez perto do topo nas ultimas 24h --
     total_near_depth[t] = notional_bid_1pct[t] + notional_ask_1pct[t]
     depth_change_24h[t] = total_near_depth[t] - total_near_depth[t-24]

5. imbalance_price_divergence[t]: imbalance subindo enquanto preco NAO
   acompanha, ou vice-versa -- mesma formalizacao de
   funding_price_divergence/oi_price_divergence, trocando a variavel
   de origem por book_imbalance_1pct --
     price_return_24h[t] = log_price[t] - log_price[t-24]
     z_imbalance[t] = book_imbalance_1pct[t] normalizado
         (shift(1).rolling(2160h) mean/std do proprio book_imbalance_1pct)
     z_price_return[t] = price_return_24h[t] normalizado
         (mesma normalizacao ja usada em TASK-ALT-001/002)
     imbalance_price_divergence[t] = z_imbalance[t] - z_price_return[t]

Todas as 5 sao causais por construcao (usam apenas o snapshot mais
recente conhecido em t; feature 4 e 5 usam shift(1) antes de qualquer
rolling).
```

## Universo e amostra

```text
20 symbols do dataset ja normalizado (mesmo universo de toda a
pesquisa desta sessao). Painel empilhado (pooled), mesmo padrao de
TASK-ALT-001/002.
```

## Escopo do novo download

```text
20 symbols x ~1.096 dias (2023-06-01 a 2026-05-31) = ~21.920 arquivos
diarios pequenos (~450-520KB cada, ~10,2GB total estimado) + seus
.CHECKSUM. Download memory-safe: um symbol por vez, resample para 1h e
descarte do frame de eventos brutos antes de passar ao proximo symbol
-- mesmo padrao ja usado e testado em TASK-ALT-002.
```

## Invariantes obrigatorios

```text
- Toda feature usa apenas o snapshot mais recente conhecido em t (o
  resample horario ja garante isso -- nao ha look-ahead dentro da
  hora).
- Features 4 e 5 usam shift(1) antes de qualquer rolling.
- O TARGET (retorno futuro) e o UNICO lugar onde dados posteriores a t
  sao usados.
- Nenhum gate de performance economica, custo, ou execucao nesta task.
- Os 3 subperiodos sao os MESMOS ja fixados em TASK-ALT-001/002 -- nao
  reparticionados.
- Download verificado por checksum SHA256 antes de qualquer uso dos
  dados -- fail closed em qualquer mismatch.
```

## Fora de escopo

```text
- Desenhar qualquer regra de entrada/saida/position sizing em torno de
  uma feature que mostrar informacao -- task separada.
- Qualquer outra feature de book depth alem das 5 formalizadas.
- Qualquer outro horizonte de retorno futuro alem de 24h nesta task
  (um horizonte mais curto, mais alinhado a teoria de microestrutura,
  fica registrado como candidato de FUTURA task separada, nao testado
  aqui).
- Reconstrucao de L2 tick-a-tick a partir de bookTicker (fonte
  diferente, com gap conhecido, nao usada nesta task).
- Reparticionar os subperiodos ou ajustar o limiar de 0,03.
- Mutual information ou qualquer estimador nao-linear.
- Novo download alem do necessario para `bookDepth` (nenhum outro
  family, ex.: aggTrades/trades, e baixado nesta task).
```
