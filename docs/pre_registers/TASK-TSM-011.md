# TASK-TSM-011 - Definicao e pre-registro: generalizacao CROSS-EXCHANGE do TSM base (Bybit)

## Status

ACCEPTED (locked) - travado 2026-07-17 antes de baixar/analisar dado. Sob
ADR-0031. VALIDACAO de generalizacao (prioridade #1 do usuario: cross-exchange).
Config FIXA (FC-II-008), ZERO re-tune, mesmo codigo do TSM base. Nao e promocao
live; e evidencia de robustez cross-venue.

## Motivacao

O edge do TSM base ja generalizou entre universos de ativos (TSM-009/010).
Proximo eixo de robustez: outra EXCHANGE. Rodar o MESMO algoritmo, MESMOS 20
symbols, MESMOS params, na Bybit -- se o Sharpe segue positivo e batendo
buy-hold, o edge nao e artefato da microestrutura/execucao da Binance.

## Reconnaissance (feito, sem analise comitada)

- Bybit v5 publico (sem auth): `/market/kline` (interval=60) alcança 2023-06;
  `/market/funding/history` intervalo 8h (igual Binance); 633 perps USDT listados
  (inclui os 20). VIAVEL para 3 anos horario.
- OKX: `/market/history-candles` reachable (follow-up, TASK proprio se Bybit ok).
- Hyperliquid: candleSnapshot retornou vazio para janela 2024 (historico raso) ->
  FORA (sem 3a de historico horario).

## Hipotese

O TSM base (sign(retorno trailing 28d), inverse-vol, unit-gross, 5d, funding)
tem Sharpe POSITIVO e bate buy-and-hold tambem na Bybit, com metricas em ordem
de grandeza comparaveis a Binance -- edge geral de trend, nao especifico de venue.

## Metodologia

```text
Universe: os MESMOS 20 symbols da Binance dev (ADA APT ARB ATOM AVAX BCH BNB BTC
DOGE DOT ETC ETH LINK LTC OP SOL SUI TRX UNI XRP), enquanto listados na Bybit;
coverage gate 95% da janela 2023-06..2026-05.
Dado (Bybit v5 publico, custo ZERO): klines horarios (close -> log_price) +
funding history (backward as-of merge -> funding_rate_asof por hora;
funding_interval_hours = 8, confirmado). Normalizacao replica a convencao da
Binance (log_price, funding_rate_asof, funding_interval_hours) para o TSM
consumir sem alteracao. Download resiliente/paginado com retry; cache em CSV.
Estrategia: TSM BASE config FIXA (include_funding=True). Comparar Bybit vs
Binance: Sharpe, max drawdown, turnover, net PnL/PF-proxy, e Sharpe por
subperiodo (3 janelas fixas). Notas estruturais (funding, liquidez, contratos).
```

## Celula primaria (LOCKED)

```text
TSM base FIXO na Bybit, mesmos 20 symbols. Sem re-tune; sem escolha de symbols
por desempenho (universe = os 20 da Binance que a Bybit lista + coverage gate).
```

## Criterio de decisao

```text
GENERALIZA CROSS-EXCHANGE se na Bybit o TSM base tem Sharpe > 0 E > buy-and-hold,
consistente nos 3 subperiodos, em ordem de grandeza comparavel a Binance
(Sharpe ~ 0,8-1,0). Diferencas materiais (ex.: Bybit muito pior) sao
DOCUMENTADAS e caracterizadas (liquidez/funding/execucao), nao escondidas.
Nao promove live. Resultado negativo tambem e registrado.
```

## Invariantes / Fora de escopo

```text
- Config FIXA (FC-II-008); ZERO re-tune; symbols por regra objetiva.
- Causal (mesma logica testada); custo ZERO (Bybit public).
- Dev-window de outra exchange (nao OOS temporal -> nao promove live).
- FORA: otimizar params para Bybit; execucao/slippage especificos; OKX
  (follow-up TASK-TSM-012 se Bybit ok); overlays (base e o foco robusto).
```
