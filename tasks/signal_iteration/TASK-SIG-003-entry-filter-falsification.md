# TASK-SIG-003 - Teste de falsificacao ex-ante do lado da ENTRADA

## Dono

Backtest Agent

## Revisor

Quant Research Agent + QA / Chaos Testing Agent + PM Agent

## Workstream

Signal Iteration 1 - Diagnostico antes da Sprint 10

## Depende de

TASK-SIG-002

## Contexto obrigatorio

```text
reports/signal_diagnostics.md
reports/signal_fast_reversion_experiment.md
data/research/binance_public/cost_pilot/signal_fast_reversion_experiment.json
reports/backtest_statistical.md
src/backtest/statistical_backtest.py
src/research/triple_barrier.py
src/research/ou.py
```

TASK-SIG-001 mostrou edge bruto agregado negativo antes de custo, `|z| >= 3.0`
pior que `2.0-2.5`, e reversoes resolvidas em 2-4h positivas (recorte ex-post).
TASK-SIG-002 testou a versao causal dessa pista pelo lado da SAIDA
(`max_vertical_bars=4`) e a hipotese foi rejeitada: capar a saida piora o gross
(decisao `STOP_FAST_REVERSION_PATH`).

Esta e a ULTIMA tentativa de resgatar o sinal, agora pelo lado da ENTRADA. Se
falhar, a iteracao de sinal encerra. A disciplina central desta tarefa e a
PRE-REGISTRACAO: a regra de decisao (o que conta como "tem edge" vs "nao tem")
esta fixada ABAIXO, antes de qualquer execucao, e nao pode ser afrouxada depois
de ver os numeros. Nada de escolher o melhor threshold ex-post e reportar so ele.

## Hipotese pre-registrada

Um filtro de ENTRADA causal e ex-ante sobre o OU half-life trailing (so entrar
quando o par, no momento da entrada, tem meia-vida curta = reversao rapida
esperada) seleciona uma subpopulacao de entradas com edge bruto materialmente
melhor que o baseline nao-filtrado. Este e o espelho ex-ante da ideia que
falhou pelo lado da saida na TASK-SIG-002: em vez de forcar a saida em 4h,
so entrar onde a dinamica de reversao ja e rapida no momento da entrada.

## Metodo

```text
1. Rerodar o backtest estatistico (nao filtrar resultado anterior), varrendo o
   gate de entrada `max_half_life_hours` em uma grade FIXA e pre-registrada:
   [240 (baseline canonico), 120, 72, 48, 24, 12] horas.
2. `max_half_life_hours` ja e um gate de ENTRADA causal: o half-life vem do
   refit OU em janela trailing terminando na barra de entrada (nunca
   full-sample). Apertar esse threshold e uma decisao conhecida na entrada.
3. Baseline (240h) deve reproduzir o Sprint 8 canonico exatamente antes de
   qualquer comparacao (abortar fail-closed se nao reproduzir).
4. Todos os demais parametros iguais ao canonico. So `max_half_life_hours` varia.
5. NAO usar `bars_held`, `outcome`, `gross_pnl_bps` ou `net_pnl_bps` como
   feature de entrada ou para selecionar/filtrar trades.
6. Reportar TODOS os thresholds da grade (nao so o melhor): por threshold,
   trade_count, gross PnL/trade, gross profit factor, net profit factor,
   hit rate, drawdown, pares aprovados, e decomposicao PROFIT/STOP/VERTICAL.
```

## Regra de decisao PRE-REGISTRADA (fixada antes de rodar)

```text
Metrica primaria: net profit factor da subpopulacao filtrada, com trade_count
como guarda de tamanho de amostra.

CONTINUE_SIGNAL_ITERATION (candidato, NAO aprovacao) se e somente se:
  existe ao menos UM threshold da grade com
    net_profit_factor >= 1.10  E  trade_count >= 200.

Caso contrario: STOP_SIGNAL_ITERATION. Conclui-se que o sinal de reversao a
media, neste universo e conjunto de features, nao tem edge bruto exploravel
por filtro de entrada, e a decisao macro (pivotar formulacao, mudar universo,
ou pausar) volta para o usuario.

Ressalva pre-registrada sobre multiplas comparacoes: como a grade tem 6
thresholds, ATE UM bucket passando e evidencia FRACA (poderia ser sorte de
amostra). Portanto, mesmo um CONTINUE nao e aprovacao -- e apenas gatilho para
um teste out-of-sample dedicado (ex: outro periodo/ano) antes de qualquer
credito. Isso deve estar escrito no relatorio, nao inferido.

Anti-p-hacking: o relatorio DEVE mostrar a grade inteira e aplicar esta regra
literalmente. Escolher o melhor threshold ex-post e apresenta-lo isolado como
"o resultado" e explicitamente proibido.
```

## Arquivos permitidos

```text
scripts/run_signal_entry_filter_experiment.py
tests/test_signal_entry_filter_experiment.py
reports/signal_entry_filter_experiment.md
data/research/binance_public/cost_pilot/signal_entry_filter_*.json
data/research/binance_public/cost_pilot/signal_entry_filter_*.csv
project_control/
tasks/signal_iteration/
```

## Arquivos proibidos

```text
src/backtest/statistical_backtest.py (nao alterar; so consumir -- max_half_life_hours ja e parametro)
src/research/triple_barrier.py
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

## Testes obrigatorios

```text
pytest tests/test_signal_entry_filter_experiment.py
pytest tests/test_statistical_backtest.py
pytest tests -q
ruff check src tests scripts
git diff --check
```

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` com:

```text
- grade de thresholds testada (completa, nao so o melhor);
- aplicacao literal da regra de decisao pre-registrada;
- decisao CONTINUE_SIGNAL_ITERATION ou STOP_SIGNAL_ITERATION;
- se CONTINUE, qual teste out-of-sample e exigido antes de qualquer credito;
- revisoes formais (Backtest + Quant + QA + PM);
- confirmacao de que Sprint 10 continua nao aberta.
```

## Status

DONE

## Progresso

100%

## Resultado

Run 1 (grade `[240,120,72,48,24,12]`h) foi identificada por revisao formal
(Quant Research Agent) como NAO-VINCULANTE (excluiu so 0,064% dos trades) --
nao exercitava de fato a hipotese. Run 2 (grade `[240,12,6,3,1.5,0.75,0.375]`h,
novo pre-registro independente) e VINCULANTE (excluiu 99,88% dos trades no
threshold mais apertado). Baseline (240h) reproduziu o Sprint 8 canonico
exatamente nas duas execucoes.

Decisao final: `STOP_SIGNAL_ITERATION`. Nenhum threshold do Run 2 cumpre a
regra pre-registrada (net PF >= 1.10 E trade_count >= 200 simultaneamente);
o threshold mais apertado (0,375h) chega perto no gross (PF 1,156) mas falha
no net (PF 0,833) e na amostra (74 trades). Observacao descritiva (nao
decisoria): ha concentracao real de edge bruto em entradas de meia-vida
muito curta, mas nao sobrevive ao custo fixo conservador na amostra
disponivel -- ver `reports/signal_entry_filter_experiment.md`.

Revisao formal: Quant Research Agent PASSA (apos corrigir o P1 de grade
nao-vinculante com o Run 2); QA/Chaos Testing Agent PASSA; PM Agent PASSA.
Verificacao: 304 testes, ruff limpo, git diff --check limpo.

Encerra a Signal Iteration 1 (TASK-SIG-001/002/003). Sprint 10 permanece NAO
ABERTA. Decisao macro sobre proximos passos volta para o usuario.
