# TASK-BASIS-001 - Pre-registro: cash-and-carry delta-neutral (spot x futuro datado), BTC & ETH

## Status

ACCEPTED (locked) - travado 2026-07-19 ANTES de baixar/analisar qualquer dado de
basis. Sob ADR-0034 (NOVA familia, independente da TSM congelada). NAO e um modelo
preditivo de preco; NAO reusa/re-otimiza a TSM. Somente pesquisa/paper, NENHUM
dinheiro real.

## Hipotese economica

O futuro datado costuma negociar com PREMIO sobre o spot; comprar spot + vender o
MESMO nocional em futuro datado do mesmo ativo = posicao ~delta-zero cujo lucro
vem da CONVERGENCIA do basis ate o vencimento, nao de prever direcao. Mecanismo:
demanda especulativa por alavancagem comprada + capital de arbitragem limitado
mantem o basis positivo (nao e lucro sem risco). Ataca diretamente o que reprovou
a TSM: risco DIRECIONAL, drawdowns de 31-58%, longos periodos underwater, lucro
concentrado.

## Fonte de dados (LOCKED - Binance publico, gratis, offline; recon 2026-07-19)

```text
- Perna SPOT: data/spot/monthly/klines/{BTCUSDT,ETHUSDT}/1h (spot VERDADEIRO).
- Perna FUTURO: data/futures/um/monthly/klines/{BASE}_{YYMMDD}/1h -- contratos
  trimestrais USD-M (vencimentos ultima sexta de mar/jun/set/dez). Confirmado
  disponivel (ex.: BTCUSDT_240628). O contrato datado NAO tem indexPriceKlines
  (404) -> usa-se o SPOT verdadeiro como referencia de convergencia.
- Basis = preco_futuro - preco_spot; converge a ~0 no vencimento.
- Modulo de dados SEPARADO (nao mexe em historical_dataset.py, do qual a TSM
  congelada depende). Cross-exchange (Bybit/OKX) e passo posterior do criterio.
```

## Celula primaria (LOCKED)

```text
Para cada (ativo em {BTC,ETH}, contrato trimestral com >= N dias de historico),
a cada barra de entrada:
  perna longa spot (nocional 1) + perna curta futuro (nocional 1) -> delta ~0;
  segurar ate o vencimento; realizar a convergencia do basis.
Sem escolher o ativo/contrato pelo melhor carry historico. Sem alt beyond BTC/ETH.
Causal: decisao usa so precos ate a barra de entrada; a convergencia ao
vencimento e o unico termo forward.
```

## Metodologia / metricas (LOCKED)

```text
retorno_liquido = basis_capturada - fees(2 pernas) - spread - slippage
                  - financiamento - custodia
Custos conservadores a priori (reusa constantes do ExecutionCostModel onde
aplicavel): taker nas 2 pernas, half-spread, slippage por participacao. Futuro
datado NAO tem funding (so perp) -> financiamento=0 nesta celula; custodia~0 para
spot mantido (nota). Por oportunidade (ativo x contrato x entrada), calcular:
  - APR bruto e liquido na ENTRADA (basis anualizado pelos dias ate o vencimento);
  - retorno realmente TRAVADO ate o vencimento (realizado);
  - margem necessaria (perna curta) e risco de liquidacao sob movimento extremo;
  - basis ADVERSA (mark-to-market) antes do vencimento (pior MTM intra-trade);
  - capital preso; retorno sobre CAPITAL TOTAL e sobre MARGEM;
  - risco de executar uma perna sem preencher a outra (leg risk);
  - risco de exchange / stablecoin / custodia (qualitativo, documentado).
Metrica central NAO e so Sharpe: e RETORNO LIQUIDO por CAPITAL IMOBILIZADO.
```

## Criterio de aprovacao (LOCKED - do usuario)

```text
APROVA se, ANTES de ver resultados, todos valem:
  1. retorno liquido POSITIVO em Binance, Bybit E OKX (sem depender de 1 exchange);
  2. positivo apos custos CONSERVADORES;
  3. drawdown de equity CLARAMENTE inferior ao da TSM (compostos 31-58%);
  4. baixa exposicao direcional OBSERVADA (delta ~0);
  5. retorno NAO concentrado em poucos meses;
  6. NENHUM resultado que dependa de alavancagem elevada;
  7. capacidade suficiente nos majors;
  8. retorno sobre capital imobilizado que JUSTIFIQUE o risco (DD pequeno com
     yield irrisorio apos custos NAO passa).
Qualquer resultado negativo tambem e documentado (nao escondido).
```

## Ordem de pesquisa (LOCKED)

```text
1. Spot x futuro datado cash-and-carry BTC/ETH   <- ESTA task (celula primaria)
2. Calendar spread entre futuros
3. Spot x perp funding-neutral carry
4. Cross-exchange basis (so apos dominar risco de 2 exchanges)
5. Opcoes/VRP (so com dados adequados + orcamento de tail risk)
```

## Riscos (documentados; "delta-neutral" != "sem risco")

```text
leg risk (1 perna preenche, a outra nao); liquidacao da margem do futuro em
movimento extremo; suspensao de saques / insolvencia da exchange; ADL; divergencia
contrato-indice; fees consumindo o spread; custodia do spot; basis ampliando ANTES
de convergir (perda MTM). O criterio de aprovacao ja exige robustez a varios deles.
```

## Invariantes / Fora de escopo

```text
- BTC/ETH apenas (SOL so depois); sem 20 alts; sem escolher ativo pelo carry
  historico; delta-neutral (nocionais iguais nas 2 pernas).
- Causal; custos conservadores; SEM dependencia de alavancagem alta; paper only,
  SEM dinheiro real; pre-registro antes de codigo; negativos documentados.
- Modulo de dados/backtest SEPARADO -- nao altera a TSM congelada nem
  historical_dataset.py.
- FORA: modelo preditivo de preco; alt-basket; otimizar por ativo/contrato
  ex-post; assumir preenchimento simultaneo perfeito das 2 pernas sem custo.
```
