# Signal Diagnostics - Gross Edge

Data: 2026-07-03T13:00:21.081778+00:00

## Objetivo

Diagnosticar os trades ja calculados no Sprint 8 canonico para entender onde existe, ou nao existe, edge bruto antes de custo. Este relatorio nao muda parametros, nao reroda backtest e nao abre Sprint 10.

## Fonte

- Input: `/home/arthur/Downloads/crypto-pair-trading/data/research/binance_public/cost_pilot/sprint8_canonical_backtest_results.json`
- Trades resolvidos analisados: 62878
- Pares analisados: 41

## Resultado Agregado

| Metrica | Valor |
| --- | --- |
| Gross PnL total (bps) | -48248.0270 |
| Gross PnL medio/trade (bps) | -0.7673 |
| Gross profit factor | 0.9866 |
| Net PnL total (bps) | -861874.1876 |
| Custo medio/trade (bps) | 12.9398 |
| Hit rate bruto | 60.62% |
| Bars held medio | 3.9510 |

## Outcomes

| Bucket | Trades | Gross/trade | Gross PF | PROFIT% | STOP% | VERTICAL% | Avg |z| | Avg hold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PROFIT | 43347 | 69.6857 | 7.0800 | 100.00% | 0.00% | 0.00% | 2.9561 | 3.6842 |
| STOP | 6509 | -260.5495 | 0.0000 | 0.00% | 100.00% | 0.00% | 2.8550 | 2.0475 |
| VERTICAL | 13022 | -105.4367 | 0.0282 | 0.00% | 0.00% | 100.00% | 2.9796 | 5.7906 |

## Edge Bruto Por |entry_zscore|

| Bucket | Trades | Gross/trade | Gross PF | PROFIT% | STOP% | VERTICAL% | Avg |z| | Avg hold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0-2.5 | 29244 | 1.5514 | 1.0331 | 69.17% | 10.58% | 20.25% | 2.2204 | 3.8024 |
| 2.5-3.0 | 14319 | 1.0614 | 1.0196 | 68.09% | 10.96% | 20.95% | 2.7221 | 3.8802 |
| 3.0+ | 19315 | -5.6337 | 0.9254 | 69.22% | 9.56% | 21.22% | 4.2252 | 4.2285 |

## Edge Bruto Por Tempo Em Trade

| Bucket | Trades | Gross/trade | Gross PF | PROFIT% | STOP% | VERTICAL% | Avg |z| | Avg hold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1h | 8412 | -12.6876 | 0.8576 | 58.54% | 41.39% | 0.07% | 2.8188 | 1.0000 |
| 2-4h | 32115 | 41.4152 | 2.2647 | 80.44% | 7.71% | 11.85% | 2.9073 | 2.9691 |
| 5-12h | 22167 | -54.3276 | 0.3066 | 56.34% | 2.48% | 41.19% | 3.0549 | 6.4090 |
| 13-24h | 184 | -365.6920 | 0.0028 | 55.98% | 1.09% | 42.93% | 3.9274 | 14.1141 |
| 25h+ | 0 | NA | NA | NA | NA | NA | NA | NA |

## Lado Do Spread

| Bucket | Trades | Gross/trade | Gross PF | PROFIT% | STOP% | VERTICAL% | Avg |z| | Avg hold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LONG_SPREAD | 28945 | 0.7236 | 1.0135 | 68.80% | 9.28% | 21.93% | 2.9014 | 4.0219 |
| SHORT_SPREAD | 33933 | -2.0391 | 0.9663 | 69.06% | 11.27% | 19.67% | 2.9924 | 3.8905 |

## Top 10 Pares Por Gross Medio

| Bucket | Trades | Gross/trade | Gross PF | PROFIT% | STOP% | VERTICAL% | Avg |z| | Avg hold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ETCUSDT/LTCUSDT | 1441 | 10.7607 | 1.2374 | 66.13% | 8.61% | 25.26% | 2.9878 | 3.2117 |
| AVAXUSDT/DOTUSDT | 1589 | 9.0222 | 1.1598 | 70.36% | 10.26% | 19.38% | 2.8367 | 4.4978 |
| ARBUSDT/OPUSDT | 1578 | 8.6791 | 1.1593 | 69.77% | 10.20% | 20.03% | 2.8835 | 4.7902 |
| ADAUSDT/DOTUSDT | 1569 | 8.5631 | 1.1654 | 71.57% | 9.37% | 19.06% | 2.8575 | 4.5736 |
| ARBUSDT/ATOMUSDT | 1570 | 8.4800 | 1.1319 | 71.15% | 12.17% | 16.69% | 2.8914 | 4.4847 |
| ARBUSDT/ETCUSDT | 1536 | 8.4682 | 1.1433 | 69.86% | 10.61% | 19.53% | 2.9649 | 3.9655 |
| DOGEUSDT/ETCUSDT | 1568 | 7.2633 | 1.1163 | 69.64% | 10.52% | 19.83% | 3.0723 | 3.8106 |
| DOGEUSDT/DOTUSDT | 1619 | 7.2366 | 1.1089 | 71.03% | 11.98% | 16.99% | 2.9896 | 4.4064 |
| ATOMUSDT/DOTUSDT | 1629 | 4.9307 | 1.1006 | 69.43% | 10.93% | 19.64% | 2.8341 | 4.5427 |
| ARBUSDT/DOTUSDT | 1603 | 4.3474 | 1.0685 | 71.05% | 11.98% | 16.97% | 2.9290 | 4.5471 |

## Bottom 10 Pares Por Gross Medio

| Bucket | Trades | Gross/trade | Gross PF | PROFIT% | STOP% | VERTICAL% | Avg |z| | Avg hold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AVAXUSDT/ETCUSDT | 1598 | -4.8162 | 0.9302 | 70.21% | 10.45% | 19.34% | 2.9073 | 4.0638 |
| ETCUSDT/OPUSDT | 1580 | -7.0179 | 0.8946 | 64.81% | 13.61% | 21.58% | 2.9612 | 4.6677 |
| AVAXUSDT/ETHUSDT | 1449 | -7.0466 | 0.8807 | 65.49% | 8.28% | 26.22% | 2.9581 | 2.5735 |
| ADAUSDT/ATOMUSDT | 1559 | -7.0785 | 0.8941 | 68.57% | 10.97% | 20.46% | 2.8736 | 4.6562 |
| ETHUSDT/SOLUSDT | 1537 | -7.3188 | 0.8387 | 66.36% | 8.26% | 25.37% | 3.0342 | 3.5706 |
| ETHUSDT/OPUSDT | 1607 | -10.9267 | 0.8108 | 66.46% | 10.83% | 22.71% | 2.9314 | 5.3074 |
| ADAUSDT/ARBUSDT | 1581 | -12.6761 | 0.8261 | 67.93% | 13.35% | 18.72% | 2.9194 | 4.7786 |
| DOTUSDT/OPUSDT | 1542 | -14.7668 | 0.7999 | 69.97% | 12.71% | 17.32% | 2.9193 | 4.9183 |
| ADAUSDT/XRPUSDT | 1567 | -15.5125 | 0.8062 | 67.90% | 12.70% | 19.40% | 2.9074 | 5.0364 |
| ETHUSDT/LINKUSDT | 1528 | -17.1330 | 0.6723 | 63.42% | 10.86% | 25.72% | 2.9560 | 4.6283 |

## Diagnostico

- O edge bruto agregado e nao-positivo antes de custos.
- PROFIT ocorre pelo menos tao frequentemente quanto STOP; foco deve ser payoff medio.
- |z| >= 3.0 nao melhora o gross medio contra a faixa 2.0-2.5.
- O edge bruto aparece em reversoes de 2-4h e desaparece em holds de 5h+.
- Holds de 13-24h sao poucos, mas extremamente negativos em gross PnL medio.
- Lado com melhor gross medio: LONG_SPREAD (0.7236 bps/trade); pior: SHORT_SPREAD (-2.0391 bps/trade).

## Proxima Tarefa Recomendada

- Priorizar mudanca no criterio de entrada antes de otimizar custo.
- Nao priorizar aumento simples de |z|; validar filtro de regime/velocidade.
- TASK-SIG-002 deve testar cap vertical <=4h como experimento causal, sem tocar em execucao.
- Gate por OU half-life curto e hipotese secundaria: exige registrar ou recalcular half-life por entrada antes de concluir.

## Limites

- Trades podem estar sobrepostos no tempo, como documentado no backtest canonico.
- Custo aqui so contextualiza o net PnL ja calculado; a decisao desta tarefa olha principalmente para gross PnL.
- Este diagnostico nao valida paper/live trading e nao altera Execution/Risk/Ledger.
