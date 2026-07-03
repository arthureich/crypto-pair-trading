# Signal Fast Reversion Experiment

Data: 2026-07-03T16:50:21.247078+00:00

## Objetivo

Testar uma regra causal de reversao rapida (`max_vertical_bars=4`) contra o baseline canonico. Este experimento reroda o backtest; ele nao filtra trades antigos por `bars_held`, `outcome`, gross ou net PnL.

## Baseline Reproduction

- Passou: True
- Deltas: `{'trade_count': 0.0, 'gross_pnl_bps': 0.0, 'cost_bps': 0.0, 'net_pnl_bps': 0.0, 'profit_factor': 0.0, 'hit_rate': 0.0}`
- Delta approved pairs: 0

## Nota De Implementacao

Durante a implementacao foi corrigido um bug no backtest estatistico: a janela enviada ao resolvedor de triple barrier precisava incluir uma barra adicional alem do orcamento vertical para confirmar VERTICAL. Sem essa barra, a variante curta podia transformar VERTICAL em NO_DATA artificialmente. A correcao tem regressao dedicada em `tests/test_statistical_backtest.py`.

## Portfolio

| Variant | Trades | Gross bps | Net bps | PF | Hit rate | Drawdown | Avg hold | Approved pairs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_canonical | 62878 | -48248.0270 | -861874.1876 | 0.7817 | 56.41% | 901350.1634 | 3.9510 | 0 |
| fast_vertical_4h | 62878 | -63675.2375 | -863918.0706 | 0.7655 | 52.07% | 896542.4642 | 3.0721 | 0 |

## Comparacao

| Metrica | Delta fast - baseline |
| --- | --- |
| Gross PnL bps | -15427.2105 |
| Net PnL bps | -2043.8831 |
| Profit factor | -0.0163 |
| Max drawdown bps | -4807.6993 |
| Avg bars held | -0.8789 |
| Trade count | 0 |
| Approved pair count | 0 |

## Decomposicao

| Metrica | baseline_canonical | fast_vertical_4h | Delta |
| --- | --- | --- | --- |
| PROFIT count | 43347 | 30756 | -12591 |
| STOP count | 6509 | 5958 | -551 |
| VERTICAL count | 13022 | 26164 | 13142 |
| Avg bars held | 3.9510 | 3.0721 | -0.8789 |
| Max drawdown bps | 901350.1634 | 896542.4642 | -4807.6993 |

## Decisao

- Decisao: `STOP_FAST_REVERSION_PATH`
- Candidate for next iteration: False
- Interpretacao: Fast vertical cap did not improve both gross and net PnL. Do not promote this signal change.

## Limites

- O backtest continua permitindo trades sobrepostos, como no Sprint 8 canonico.
- Custo continua sendo a suposicao fixa conservadora do backtest estatistico.
- Nada neste experimento abre Sprint 10, paper trading ou live trading.
