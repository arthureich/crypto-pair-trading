# TASK-SIG-001 - Diagnosticar edge bruto do sinal

## Dono

Quant Research Agent

## Revisor

Backtest Agent + QA / Chaos Testing Agent + PM Agent

## Workstream

Signal Iteration 1 - Diagnostico antes da Sprint 10

## Contexto obrigatorio

```text
project_control/PROJECT_STATE.md
project_control/CURRENT_SPRINT.md
project_control/HANDOFFS.md
reports/backtest_statistical.md
reports/backtest_executable_v1.md
data/research/binance_public/cost_pilot/sprint8_canonical_backtest_results.json
```

O usuario escolheu explicitamente "Iterar o sinal primeiro" depois de dois
backtests independentes mostrarem 0 pares com edge liquido. Esta tarefa nao
altera o sinal, nao reexecuta o backtest, e nao avanca para Sprint 10. Ela
diagnostica os 62.878 trades ja calculados no Sprint 8 canonico para
descobrir se existe algum recorte com edge bruto antes de custo.

## Arquivos permitidos

```text
src/research/signal_diagnostics.py
scripts/run_signal_diagnostics.py
tests/test_signal_diagnostics.py
reports/signal_diagnostics.md
data/research/binance_public/cost_pilot/signal_diagnostics_*.json
data/research/binance_public/cost_pilot/signal_diagnostics_*.csv
project_control/
tasks/signal_iteration/
```

## Arquivos proibidos

```text
src/ledger/
src/execution/
src/live/
src/recovery/
src/models/
src/backtest/fill_model.py
src/backtest/execution_simulator.py
src/backtest/replay_engine.py
data/research/binance_public/cost_pilot/raw/
qualquer endpoint de exchange/trading
```

## Criterio de pronto

```text
1. Carregar os trades ja calculados do Sprint 8 canonico sem rerodar o
   backtest e sem carregar arquivos raw.
2. Reportar distribuicao de outcomes PROFIT/STOP/VERTICAL.
3. Reportar edge bruto por faixa de |entry_zscore|: [2.0,2.5), [2.5,3.0),
   [3.0,+inf).
4. Reportar edge bruto por tempo em trade: 1h, 2-4h, 5-12h, 13-24h, 25h+.
5. Reportar top/bottom pares por gross PnL medio e gross profit factor.
6. Separar conclusao diagnostica de proposta de alteracao. Nenhum parametro
   de sinal muda nesta tarefa.
7. Registrar recomendacao concreta para a proxima tarefa de iteracao do
   sinal, com limites claros e testes esperados.
```

## Testes obrigatorios

```text
pytest tests/test_signal_diagnostics.py
ruff check src tests scripts
git diff --check
```

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` com:

```text
- artefatos gerados;
- achados principais;
- revisoes formais;
- recomendacao para TASK-SIG-002;
- confirmacao de que Sprint 10 nao foi aberta.
```

## Status

DONE

## Progresso

100%

## Resultado

```text
Diagnostico real gerado em reports/signal_diagnostics.md e
data/research/binance_public/cost_pilot/signal_diagnostics_sprint8_canonical.*

Achados principais:
- gross PnL agregado continua negativo antes de custo (-0.7673 bps/trade);
- PROFIT e muito mais frequente que STOP, entao o problema nao e stop-count;
- |z| >= 3.0 piora o gross medio contra 2.0-2.5;
- reversoes resolvidas em 2-4h tem gross medio positivo forte;
- holds de 5h+ destroem o edge bruto;
- proxima tarefa deve testar regra causal de cap vertical <=4h, nao filtrar
  retrospectivamente trades com bars_held <=4.
```

## Revisao formal

```text
Quant Research Agent: PASSA, com ressalva de que bars_held/outcome sao
ex-post e nao podem virar features de entrada.

Backtest Agent: MUDANCAS SOLICITADAS -> PASSA apos correcoes. Correcoes:
bucket 25h+ aparece mesmo com zero trades; half-life curto foi rebaixado para
hipotese secundaria, nao conclusao deste diagnostico.

QA / Chaos Testing Agent: MUDANCAS SOLICITADAS -> PASSA apos correcoes.
Correcoes: status/side/outcome invalidos falham, bars_held<=0 falha,
|entry_zscore|<2 falha, nenhum trade resolvido falha explicitamente.
```

## Verificacao

```text
pytest tests/test_signal_diagnostics.py -> 13 passed
pytest tests -q -> 283 passed
ruff check src tests scripts -> All checks passed
git diff --check -> clean
```
