# TASK-TSM-015 - Definicao e pre-registro: STRESS DE LIQUIDEZ do TSM base (tiers de liquidez + varredura de custo)

## Status

ACCEPTED (locked) - travado 2026-07-17 ANTES de computar qualquer metrica por
tier. Sob ADR-0031. Prioridade #3 do programa de validacao do usuario ("universos
adicionais: alta/baixa liquidez, small caps"), focada no eixo DISCRIMINANTE que
ainda nao testamos: LIQUIDEZ. Todos os resultados ate agora vivem em majors/alts
liquidos onde o custo de 6 bps e valido; liquidez baixa e onde edges de trend
tipicamente quebram (spread largo, book fino, custo real maior).

## Objetivo / hipotese economica

O TSM base e cost-insensitive nos majors (FC-II-007: breakeven ~142 bps/perna).
A pergunta: o edge SOBREVIVE no extremo de MENOR liquidez dos ativos com
historico, a custo REALISTA? Se sim -> robustez de liquidez reforcada. Se quebra
a custo realista -> LIMITE in-domain honesto (o edge precisa de liquidez), tao
valioso quanto um positivo.

## Fonte de dados (LOCKED - so cache; NENHUM download novo)

```text
Uniao dos symbols JA CACHEADOS (offline, zero download):
  normalized/tsm_multiverse_202306_202605_bars.csv.gz (44 symbols) +
  normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz (20 symbols).
Coverage gate 0.95 (mesmo do multiverse). Proxy de liquidez ja nas barras:
`quote_volume` (volume em dolar) por barra horaria.
```

## Segmentacao por liquidez (LOCKED a priori)

```text
- Proxy de liquidez do symbol = MEDIANA do quote_volume diario (soma horaria por
  dia -> mediana na janela inteira). Usa a janela toda APENAS para CLASSIFICAR o
  instrumento em tier (nao e sinal negociavel; os sinais do TSM continuam
  causais). 
- Ranquear os symbols cobertos por esse proxy e dividir em TERCIS:
  HIGH (tercil superior), MID (tercil do meio), LOW (tercil inferior).
  Divisao por tercil declarada A PRIORI (nao ajustada a resultado).
- Cada tier roda como um universo long/short unit-gross independente.
```

## Metodologia (LOCKED)

```text
Estrategia: TSM base (FC-II-008, include_funding=True, ZERO re-tune) por tier.
VARREDURA DE CUSTO (a priori): 6 (base), 12, 20, 30 bps/perna -- porque liquidez
baixa merece custo REALISTA mais alto. Por (tier x custo): Sharpe (anualiz.
sqrt(24*365/120)), maxDD, net, turnover; buy-and-hold equal-weight por tier.
Tudo OFFLINE das barras cacheadas; sinais causais (mesma logica do TSM base).
```

## Criterio de decisao

```text
O tier LOW e "ROBUSTO A LIQUIDEZ" se o TSM base tem Sharpe > 0 E > buy-and-hold
a custo REALISTA para iliquidos (>= 20 bps/perna), E a queda de Sharpe HIGH->LOW
e modesta (nao um colapso). 
- Se o LOW sobrevive a >=20 bps -> reforca a robustez (edge nao depende so de
  majors).
- Se o LOW quebra a custo realista (Sharpe<=0 ou < buy-hold, ou colapso HIGH->LOW)
  -> LIMITE in-domain honesto: o edge precisa de liquidez. Documentado, nao
  escondido; sem mudanca de parametro (e uma condicao de aplicabilidade, nao um
  bug a "consertar").
DESCRITIVO / validacao: sem promocao live.
```

## Invariantes / Fora de escopo (ressalvas HONESTAS travadas)

```text
- SURVIVORSHIP (ressalva central): perps genuinamente iliquidos/microcap NAO tem
  3a de historico e estao AUSENTES do cache -> este teste so cobre o EXTREMO
  MENOS liquido dos SOBREVIVENTES. E um LIMITE INFERIOR (proxy otimista) da
  questao de liquidez, nao a cauda real de microcaps.
- quote_volume de klines e um proxy GROSSEIRO (sem spread/profundidade de book).
- Params FIXOS FC-II-008; ZERO re-tune; tiers e custos DECLARADOS A PRIORI.
- Offline (so cache); causal; crypto in-domain (TradFi fora, ja em TSM-012).
- Nao e promocao live (custos/execucao reais de iliquidos diferem).
- FORA: escolher tiers/custos apos ver Sharpe; modelar spread/impacto real;
  baixar symbols novos; re-otimizar horizontes por tier.
```
