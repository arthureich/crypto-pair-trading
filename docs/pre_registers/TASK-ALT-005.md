# TASK-ALT-005 - Definicao e pre-registro: Funding Price Divergence em novo OOS

## Status

DONE. Decisao final: **`NAO_PROMOVE`**. Download real de 2026-06
executado (100 arquivos mensais, 20 symbols x 5 familias, checksum
SHA256 verificado), gate de dados PASS (13.920 observacoes validas),
rho no novo OOS = **-0,118324** -- sinal invertido em relacao aos 3
subperiodos originais (todos positivos, ~0,023-0,028), magnitude ~4x
maior. A pista de `TASK-ALT-001` NAO se replicou em dado genuinamente
novo. Ver `reports/alt_info_funding_divergence_new_oos.md` e o addendum
de 2026-07-07 em `project_control/DECISIONS.md` ADR-0023.

## Workstream

Research Phase II - Alternative Information / Family G follow-up. Esta
task valida, em dado genuinamente novo, a unica pista remanescente de
`TASK-ALT-001`: `funding_price_divergence`.

## Contexto obrigatorio

`TASK-ALT-001` classificou todas as features de funding como
`SEM_INFORMACAO` pelo criterio pre-registrado. A excecao notavel foi
`funding_price_divergence`, que ficou abaixo do limiar de magnitude
(`rho=0,0248`, limiar `0,03`), mas manteve sinal positivo nos 3
subperiodos independentes:

```text
2023-06/2024-05: rho=0,0276
2024-06/2025-05: rho=0,0230
2025-06/2026-05: rho=0,0239
```

Isto e uma pista legitima, mas NAO autoriza rebaixar o limiar, redesenhar
a feature no mesmo periodo, nem transformar a feature em estrategia. O
periodo 2023-06 a 2026-05 esta contaminado para esta pergunta: foi onde a
pista nasceu.

Probe operacional feito em 2026-07-07: os `.CHECKSUM` mensais de
2026-06 existem para os 20 symbols do universo e para as 5 familias
necessarias (`klines`, `markPriceKlines`, `indexPriceKlines`,
`premiumIndexKlines`, `fundingRate`): 100/100 sidecars encontrados. Nenhum
ZIP foi baixado neste probe; isto prova apenas disponibilidade inicial,
nao qualidade nem resultado.

## Agente

Backtest Agent.

## Sprint / fase atual

Research Phase II - Alternative Information, `TASK-ALT-005`.

## Task

Implementar e rodar um diagnostico novo-OOS para a feature exata
`funding_price_divergence`, usando dados posteriores a 2026-05-31 e o
historico anterior apenas como contexto causal para janelas de 90 dias.

## Arquivos permitidos

```text
docs/pre_registers/TASK-ALT-005.md
scripts/diagnostic_alt_funding_divergence_new_oos.py
tests/test_alt_funding_divergence_new_oos.py
reports/alt_info_funding_divergence_new_oos.md
data/research/binance_public/normalized/*202606*_bars.csv
data/research/binance_public/normalized/*202606*_bars.csv.gz
data/research/binance_public/cost_pilot/alt_info_funding_divergence_new_oos_results.json
project_control/CURRENT_SPRINT.md
project_control/TASK_BOARD.md
project_control/PROJECT_STATE.md
project_control/HANDOFFS.md
project_control/TEST_MATRIX.md
project_control/RISKS.md
project_control/DAILY_LOG.md
project_control/DECISIONS.md
```

Se o runner de extensao precisar reutilizar `src/research/historical_dataset.py`
sem alterar o arquivo, isto esta autorizado. Alterar esse modulo exige
review de Market Data Agent e testes especificos.

## Arquivos proibidos

```text
src/execution/**
src/ledger/**
src/live/**
src/recovery/**
src/ml/**
src/market_data/**  (salvo review explicito se houver bug de downloader)
src/backtest/execution_simulator.py
src/backtest/replay_engine.py
docs/event_contracts.md
docs/risk_limits.md
docs/state_machine.md
```

Nenhum arquivo de live engine, ledger, recovery, execution risk, ML ou
order routing pode ser alterado por esta task.

## Janela de dados

```text
Contexto causal: dataset Sprint 7 existente, 2023-06-01 a 2026-05-31.
Novo OOS decisivo: barras a partir de 2026-06-01.
Fonte: Binance Public Data mensal, USD-M futures, complete months only.
```

Regras:

```text
- Usar apenas meses completos. Nao usar julho parcial enquanto a regra de
  complete-month estiver vigente.
- Se apenas 2026-06 for baixado, as ultimas 24h de junho naturalmente
  ficam sem target de 24h e devem ser descartadas, nao preenchidas.
- Historico anterior pode ser usado para calcular medias/desvios causais
  de 90 dias, mas nenhuma linha anterior a 2026-06-01 entra no resultado
  decisorio.
- Nao baixar `bookTicker` nem qualquer dado L2 nesta task.
```

## Feature exata

Mesma definicao de `TASK-ALT-001`, sem mudanca de janela, normalizacao ou
horizonte:

```text
funding_reversal[t] = funding_rate_asof[t] - funding_rate_asof[t-24]
price_return_24h[t] = log_price[t] - log_price[t-24]
z_funding_reversal[t] = zscore_90d_causal(funding_reversal[t])
z_price_return[t] = zscore_90d_causal(price_return_24h[t])
funding_price_divergence[t] = z_funding_reversal[t] - z_price_return[t]
target[t] = log_price[t+24h] - log_price[t]
```

`zscore_90d_causal` deve usar `shift(1).rolling(2160h)` para media e
desvio. Nenhuma barra futura pode influenciar a feature em `t`.

## Gate de dados

A execucao so pode produzir resultado decisorio se todos os criterios
abaixo forem satisfeitos:

```text
- 20/20 symbols presentes no novo OOS.
- 5/5 familias mensais por symbol com checksum SHA256 verificado.
- cobertura horaria >= 99% por symbol no novo OOS.
- nenhuma duplicata conflitante por (symbol, open_time).
- `full_sample_n >= 10_000` pares feature/target validos no novo OOS.
```

Se qualquer criterio falhar, o resultado deve ser `DATA_GATE_FAIL_CLOSED`.

## Gate informacional

Esta task nao tem gate economico. Ela so decide se a pista merece uma
proxima task de feasibility separada.

```text
PROMOVE_PARA_FEASIBILITY se:
  rho_new_oos >= 0,03
  E sinal positivo no novo OOS
  E, se houver mais de um mes completo avaliado, todos os meses completos
    avaliados tambem tiverem sinal positivo.

NAO_PROMOVE caso contrario.
```

Um `PROMOVE_PARA_FEASIBILITY` nao autoriza SignalIntent, paper/live,
execution filter, sizing, ML, ledger, recovery ou qualquer acao de ordem.
Ele apenas permite abrir uma futura task separada para desenhar uma regra
operacional, com novo pre-registro.

## Testes obrigatorios

```text
- teste de causalidade: alterar precos/funding futuros nao muda
  `funding_price_divergence[t]`.
- teste de boundary: linhas anteriores a 2026-06-01 podem alimentar
  rolling context, mas nao entram no resultado decisorio.
- teste de target: ultimas 24h sem `t+24h` sao descartadas, nao
  preenchidas.
- teste de data gate: falta de symbol, falta de familia/checksum, ou
  duplicata conflitante deve falhar fechado.
- teste de output: JSON e relatorio declaram explicitamente a janela
  avaliada e o status do gate.
```

Verificacao minima esperada:

```text
PYTHONPATH=. UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_alt_funding_divergence_new_oos.py tests/test_info_content.py
UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check scripts/diagnostic_alt_funding_divergence_new_oos.py tests/test_alt_funding_divergence_new_oos.py
```

Se o download real for executado, registrar tambem o comando, o numero de
arquivos baixados, bytes aproximados, checksums verificados, linhas
normalizadas, e o resultado `DATA_GATE_*` antes de qualquer interpretacao
de rho.

## Handoff esperado

```text
1. Relatorio em reports/alt_info_funding_divergence_new_oos.md.
2. JSON auditavel em data/research/binance_public/cost_pilot/.
3. Atualizacao de TASK_BOARD, CURRENT_SPRINT, PROJECT_STATE, HANDOFFS,
   TEST_MATRIX, RISKS e DAILY_LOG.
4. Declaracao explicita: PROMOVE_PARA_FEASIBILITY, NAO_PROMOVE ou
   DATA_GATE_FAIL_CLOSED.
5. Lista dos testes rodados e resultado.
```

## Fora de escopo

```text
- Rodar qualquer feature de funding alem de `funding_price_divergence`.
- Alterar o limiar 0,03 depois de ver o novo OOS.
- Testar horizontes diferentes de 24h.
- Strategy design, backtest economico, SignalIntent, paper/live.
- Order Flow/L2, Liquidation Dynamics, Open Interest, regime filters.
- ML, XGBoost, meta-labeling.
```

## Estado operacional atual

Implementado:

```text
scripts/diagnostic_alt_funding_divergence_new_oos.py
tests/test_alt_funding_divergence_new_oos.py
```

Verificacao ja rodada:

```text
PYTHONPATH=. UV_CACHE_DIR=.uv-cache uv run --offline --with pytest pytest tests/test_alt_funding_divergence_new_oos.py tests/test_info_content.py
Result: 18 passed, 1 warning (pytest config asyncio_mode desconhecido neste ambiente).

UV_CACHE_DIR=.uv-cache uv run --offline --with ruff ruff check scripts/diagnostic_alt_funding_divergence_new_oos.py tests/test_alt_funding_divergence_new_oos.py
Result: All checks passed.

git diff --check
Result: passed.
```

Execucao real completada em 2026-07-07:

```text
PYTHONPATH=. UV_CACHE_DIR=.uv-cache uv run --offline python scripts/diagnostic_alt_funding_divergence_new_oos.py \
  --start-month 2026-06 \
  --end-month-exclusive 2026-07 \
  --dataset-version sprint_alt_funding_divergence_202606 \
  --download-workers 4

Resultado:
100 arquivos mensais baixados (20 symbols x 5 familias), todos
checksum-verificados.
data_gate=PASS, full_sample_n=13920.
rho=-0,118324 (novo OOS, 2026-06 apenas).
Decisao: NAO_PROMOVE (sinal negativo, o pre-registro exige positivo
E >=0,03).
```

Ver `reports/alt_info_funding_divergence_new_oos.md` para a tabela
completa e o addendum de 2026-07-07 em
`project_control/DECISIONS.md` ADR-0023 para a interpretacao.
