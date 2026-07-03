# Signal Intrahour Sanity Check (TASK-SIG-004)

Data: 2026-07-03T18:58:54.870302+00:00

## Natureza desta checagem

Signal Iteration 1 esta ENCERRADA como hipotese rejeitada (ADR-0010). Isto NAO e uma nova iteracao nem reabre SIG-001/002/003 -- e uma unica checagem de sanidade, de escopo pequeno, sobre um achado especifico: no bucket mais apertado do Run 2 da TASK-SIG-003 (max_half_life_hours=0,375, ~22,5 min, barras de 1h), o gross profit factor passou de 1,0 pela primeira vez em toda a iteracao (1,156), mas com apenas 74 trades em 3 pares -- amostra pequena demais para confiar. Esta checagem re-roda o MESMO pipeline causal com barras de 5 minutos, para ver se o achado se replica com amostra adequada.

## Escopo (deliberadamente pequeno)

- Simbolos: ADAUSDT, ARBUSDT, AVAXUSDT, BTCUSDT, DOGEUSDT, DOTUSDT, ETCUSDT, ETHUSDT (8, nao os 20 completos).
- Pares: ADAUSDT/ETCUSDT, ADAUSDT/ETHUSDT, ARBUSDT/ETCUSDT, ARBUSDT/ETHUSDT, AVAXUSDT/ETHUSDT, BTCUSDT/ETHUSDT, DOGEUSDT/ETHUSDT, DOTUSDT/ETHUSDT, ETCUSDT/ETHUSDT (9, os que tiveram QUALQUER trade no bucket 0,375h do Run 2 -- nao so os 3 que passaram o gate por par, para evitar a sobrevivencia que a TASK-SIG-002 ja corrigiu uma vez).
- Janela: 2025-12 a 2026-06 (6 meses, nao os 3 anos completos).
- Granularidade: 5m (barras de 5 minutos).

## Achado motivador (1h, TASK-SIG-003 Run 2, bucket 0,375h)

- Trades: 74
- Gross profit factor: 1.1559
- Net profit factor: 0.8327

## Resultado (5 minutos, mesmo pipeline causal)

`bar_duration_hours=1/12` foi propagado para OU, custo de funding e triple barrier. `max_vertical_bars=2880` preserva o mesmo cap real de 240h do backtest canonico de 1h, agora em barras de 5 minutos.

| Config | Trades | Gross bps | Gross PF | Net bps | Net PF | Hit rate |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline (sem filtro de half-life) | 23051 | 38129.9718 | 1.1343 | -239672.3391 | 0.4223 | 42.73% |
| Tight (max_half_life_hours=0.375) | 23051 | 38129.9718 | 1.1343 | -239672.3391 | 0.4223 | 42.73% |

## O achado se replica?

Descriptive comparison only -- read alongside reports/signal_intrahour_sanity_check.md, not as a pass/fail gate.
- Trades no bucket tight (5min): 23051 (vs. 74 em 1h)
- Gross PF (5min): 1.1343 (vs. 1.1559 em 1h)
- Net PF (5min): 0.4223 (vs. 0.8327 em 1h)

## Limites (leia antes de interpretar)

- Funding reusa o `funding_carry_bps_per_day` da Sprint 7 (janela de 3 anos), NAO re-derivado para esta janela de 6 meses -- aproximacao razoavel para uma checagem exploratoria, nao uma medicao de precisao.
- Sem novo modelo de custo, sem nova regra de decisao pre-registrada: esta secao e descritiva, nao um gate PASSA/NAO PASSA.
- `historical_dataset.py::normalize_kline_frame` rotula a coluna `interval` da saida como `1h` independente do intervalo real baixado -- bug de metadado conhecido, nao corrigido aqui (fora do escopo desta task). O hardcode relacionado tambem pode afetar `return_1h`/`EXTREME_RETURN` em dados 5m; esses campos nao sao consumidos por `statistical_backtest.py`, que usa `log_price` e `open_time`.
- Nao abre Sprint 10, nao reabre Signal Iteration 1.
