# TASK-SIG-002 - Testar reversao rapida com cap vertical causal

## Dono

Backtest Agent

## Revisor

Quant Research Agent + QA / Chaos Testing Agent + PM Agent

## Workstream

Signal Iteration 1 - Diagnostico antes da Sprint 10

## Depende de

TASK-SIG-001

## Contexto obrigatorio

```text
reports/signal_diagnostics.md
data/research/binance_public/cost_pilot/signal_diagnostics_sprint8_canonical.json
reports/backtest_statistical.md
src/backtest/statistical_backtest.py
src/research/triple_barrier.py
```

TASK-SIG-001 mostrou que o edge bruto agregado e negativo antes de custo,
que `|z| >= 3.0` piora contra a faixa `2.0-2.5`, e que o unico recorte
forte aparece em reversoes resolvidas entre 2h e 4h. Esse recorte e
ex-post; portanto esta tarefa deve testar uma regra causal conhecida no
momento da entrada/saida, nao filtrar trades retrospectivamente.

## Arquivos permitidos

```text
src/backtest/statistical_backtest.py
scripts/run_signal_fast_reversion_experiment.py
tests/test_signal_fast_reversion_experiment.py
reports/signal_fast_reversion_experiment.md
data/research/binance_public/cost_pilot/signal_fast_reversion_*.json
data/research/binance_public/cost_pilot/signal_fast_reversion_*.csv
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
1. Rerodar o backtest estatistico, nao filtrar o resultado anterior.
2. Baseline reproduz o Sprint 8 canonico antes de comparar variantes.
3. Variante principal: `max_vertical_bars=4` com os demais parametros iguais
   ao canonico, para testar uma saida temporal causal de reversao rapida.
4. Nao usar `bars_held`, `outcome`, `gross_pnl_bps` ou `net_pnl_bps` como
   feature de entrada.
5. Se testar OU half-life curto, registrar/recalcular o half-life por entrada
   em janela trailing causal antes de aplicar o gate; nao usar half-life
   full-sample.
6. Reportar gross e net PnL, profit factor, hit rate, drawdown, trade_count
   e pares aprovados por variante.
7. Explicar se a melhoria vem de menos perdas grandes, menos VERTICAL, menor
   tempo em trade ou apenas de reducao artificial de trades.
8. Decidir se existe candidato real para uma TASK-SIG-003 ou se a iteracao
   de sinal deve parar.
```

## Testes obrigatorios

```text
pytest tests/test_signal_fast_reversion_experiment.py
pytest tests/test_statistical_backtest.py
ruff check src tests scripts
git diff --check
```

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` com:

```text
- variantes testadas;
- comparacao contra baseline;
- revisoes formais;
- decisao PASSA/NAO PASSA para continuar iterando sinal;
- confirmacao de que Sprint 10 continua nao aberta.
```

## Status

IN_PROGRESS

## Progresso

20%
