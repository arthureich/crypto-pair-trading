# TASK-SIG-004 - Checagem exploratoria de reversao intrahora (escopo pequeno)

## Dono

Backtest Agent

## Revisor

Quant Research Agent + QA / Chaos Testing Agent + PM Agent

## Workstream

Signal Iteration 1 -- pos-encerramento (ADR-0010)

## Depende de

TASK-SIG-003 (encerrada; ver ADR-0010)

## Natureza desta tarefa (importante)

Esta NAO e uma continuacao da Signal Iteration 1, que foi ENCERRADA como
hipotese rejeitada por decisao explicita do usuario (ADR-0010). Esta e uma
UNICA checagem de sanidade, de escopo pequeno, autorizada explicitamente
pelo usuario como excecao limitada: "faria aquele estudo exploratorio rapido
em 5-15 minutos... mas com escopo pequeno e sem iniciar um novo ciclo de
otimizacao." Se nao mostrar evidencia consistente, nao ha TASK-SIG-005; a
familia de sinal fica encerrada e o esforco vai para a proxima hipotese do
roadmap.

## Contexto obrigatorio

```text
project_control/DECISIONS.md (ADR-0010)
reports/signal_entry_filter_experiment.md (achado motivador: gross PF sobe
  para 1.156 no bucket max_half_life_hours=0.375 do Run 2, mas so 74 trades
  em 3 pares -- amostra pequena demais para confirmar)
data/research/binance_public/cost_pilot/signal_entry_filter_experiment_run2.json
src/backtest/statistical_backtest.py
src/research/triple_barrier.py
src/research/historical_dataset.py (loader generico, ja suporta interval="5m" etc.)
```

## Hipotese

Barras de 1 hora nao conseguem estimar/resolver de forma confiavel reversoes
com meia-vida menor que a propria barra (~22 min no achado motivador).
Barras de 5 minutos deveriam (a) estimar melhor half-lives curtos e (b)
gerar mais observacoes independentes desse regime, permitindo testar se o
gross edge observado (PF 1.156, n=74) se replica com amostra adequada.

## Escopo (deliberadamente pequeno)

```text
Simbolos: apenas os 8 envolvidos nos 9 pares que tiveram QUALQUER trade no
  bucket max_half_life_hours=0.375 do Run 2 da SIG-003 (nao os 41 pares/20
  simbolos completos): ADAUSDT, ARBUSDT, AVAXUSDT, BTCUSDT, DOGEUSDT,
  DOTUSDT, ETCUSDT, ETHUSDT.
Pares: os 9 pares que tiveram trade nesse bucket (nao so os 3 que passaram
  o gate de par -- usar os 3 isolados seria sobrevivencia, exatamente o
  erro que TASK-SIG-002 encontrou e corrigiu).
Janela: 6 meses mais recentes dentro do dataset ja existente
  (2025-12 a 2026-05), nao os 3 anos completos.
Granularidade: 5 minutos (Binance klines "5m").
```

## Correcao de pre-requisito (pequena, no core, com revisao)

`src/backtest/statistical_backtest.py` assume implicitamente que 1 barra =
1 hora em dois lugares: `resolve_trade_pnl`'s `holding_days =
label.bars_held / HOURS_PER_DAY`, e a chamada a `estimate_ou(...)` sem
`dt` explicito (default `dt=1.0`, correto so quando a barra e de fato 1h).
Para barras de 5 minutos isso e um bug real (custo de funding calculado
como se cada barra fosse 1 hora; half-life calculado em "por-barra" em vez
de em horas). Adicionar `bar_duration_hours: float = 1.0` a
`StatisticalBacktestConfig` (default preserva 100% do comportamento
existente), passar para `estimate_ou(..., dt=cfg.bar_duration_hours)` e usar
em `holding_days = label.bars_held * config.bar_duration_hours / HOURS_PER_DAY`.
Regressao obrigatoria provando que o default nao muda nenhum resultado
existente E que o calculo escala corretamente para `bar_duration_hours != 1`.

## Arquivos permitidos

```text
src/backtest/statistical_backtest.py (so o parametro bar_duration_hours)
tests/test_statistical_backtest.py (regressao do parametro)
src/research/triple_barrier.py (excecao pos-review: apenas `bar_duration_hours`
  e calculo correto de barreira vertical sub-hora; sem alterar regra de entrada)
tests/test_triple_barrier_directional.py (regressao da excecao pos-review)
scripts/run_signal_intrahour_sanity_check.py (novo -- download + experimento)
tests/test_signal_intrahour_sanity_check.py (novo)
reports/signal_intrahour_sanity_check.md (novo)
data/research/binance_public/normalized/intrahour_sanity_*.csv,*.json (novo, dados 5m baixados)
data/research/binance_public/cost_pilot/signal_intrahour_*.json,*.csv (novo, saida do experimento)
project_control/
tasks/signal_iteration/
```

## Arquivos proibidos

```text
src/ledger/, src/execution/, src/live/, src/recovery/, src/models/
src/research/triple_barrier.py (proibido alterar exceto pela correcao
  limitada pos-review descrita acima)
src/backtest/fill_model.py, execution_simulator.py, replay_engine.py
data/research/binance_public/cost_pilot/raw/
qualquer redownload dos 41 pares/20 simbolos completos ou da janela de 3 anos
```

## Criterio de pronto

```text
1. Baixar e normalizar barras de 5m reais (checksum-verificado) para os 8
   simbolos, Dez/2025-Mai/2026, reusando historical_dataset.py sem alteracao.
2. Corrigir bar_duration_hours em statistical_backtest.py com regressao.
3. Rodar o mesmo pipeline causal (Kalman/OU/z-score/triple-barrier) nos 9
   pares, escalando zscore_window/ou_window/max_vertical_bars para manter a
   MESMA janela real de tempo usada no Sprint 8 canonico (168h trailing),
   agora em unidades de barras de 5 min.
4. Reportar, para os 9 pares agregados: gross PnL/trade, gross PF, net PF,
   trade_count, comparando explicitamente com o achado motivador (PF 1.156,
   n=74, barras de 1h).
5. NAO adicionar nova regra de decisao pre-registrada tipo SIG-003 -- e uma
   checagem de replicacao, nao um novo teste formal de aprovacao/rejeicao.
   Resultado e apenas: "replica com amostra adequada" ou "nao replica" /
   "amostra ainda insuficiente".
6. Sem filtro ex-post por bars_held/outcome/PnL realizado (mesmo invariante
   de todas as tasks anteriores).
```

## Testes obrigatorios

```text
pytest tests/test_statistical_backtest.py
pytest tests/test_signal_intrahour_sanity_check.py
pytest tests -q
ruff check src tests scripts
git diff --check
```

## Correcao pos-review

Revisao formal encontrou um bug de unidade da mesma familia do
`bar_duration_hours`: `TripleBarrierConfig.vertical_barrier_bars` arredondava
meias-vidas sub-hora para no minimo 1 hora porque `_resolve_barrier` multiplicava
o resultado por `HOUR_MS`. A correcao foi limitada ao necessario:

```text
TripleBarrierConfig.bar_duration_hours default 1.0 preserva o comportamento 1h.
vertical_barrier_bars = ceil((half_life_hours * multiplier) / bar_duration_hours).
_resolve_barrier continua usando open_time real, com duracao =
  vertical_barrier_bars * bar_duration_hours.
statistical_backtest.py passa bar_duration_hours ao TripleBarrierConfig.
run_signal_intrahour_sanity_check.py escala max_vertical_bars para 2880
  (mesmo cap real de 240h em barras de 5m).
```

Isto nao cria TASK-SIG-005 e nao reabre a Signal Iteration 1; e fechamento de
bug de unidade necessario para a propria checagem 5m ser auditavel.

## Handoff esperado

Atualizar `project_control/HANDOFFS.md`:

```text
- resultado da checagem (replica ou nao);
- decisao: nenhuma nova task se nao replicar; se replicar, decisao de
  proximos passos volta explicitamente para o usuario (nao auto-continuar);
- revisoes formais;
- confirmacao de que isto nao reabre a Signal Iteration 1 nem o Sprint 10.
```

## Resultado final

```text
Dados reais 5m checksum-verificados ja preservados: 419.328 barras normalizadas.
Escopo: 8 simbolos, 9 pares, 2025-12 a 2026-05.
Baseline 5m: 23.051 trades, gross PF 1,1343, net PF 0,4223.
Tight 5m (`max_half_life_hours=0,375`): identico ao baseline.
Achado motivador 1h: gross PF 1,1559, net PF 0,8327, n=74.
Conclusao: o achado bruto intrahora nao se replica como edge liquido; custo
fixo continua destruindo o sinal.
Decisao: nao abrir TASK-SIG-005; Signal Iteration 1 permanece fechada;
Sprint 10 continua NAO ABERTA automaticamente.
```

## Revisao final

```text
Quant Research Agent: PASSA. Ressalva interpretativa aceita: baseline 5m e
tight 5m identicos significam que o filtro tight nao discriminou novo
subconjunto; a conclusao correta e "nao ha edge liquido exploravel".

QA / Chaos Testing Agent: PASSA. Nenhum achado bloqueante, medio ou baixo
apos a correcao de unidade e atualizacao de governanca.
```

## Status

DONE

## Progresso

100%
