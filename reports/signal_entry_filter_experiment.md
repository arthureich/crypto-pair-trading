# Signal Entry-Filter Falsification Experiment (TASK-SIG-003)

Data: 2026-07-03

Este e o relatorio final consolidado de TASK-SIG-003, cobrindo DUAS execucoes
pre-registradas. A primeira grade (Run 1) foi identificada por revisao formal
(Quant Research Agent) como nao-vinculante -- nao exercitava de fato a
hipotese. Uma segunda grade (Run 2), pre-registrada independentemente e
mordendo de verdade, foi executada em seguida. Ambos os artefatos brutos
estao preservados para auditoria:

```text
data/research/binance_public/cost_pilot/signal_entry_filter_experiment_run1.json
data/research/binance_public/cost_pilot/signal_entry_filter_pair_results_run1.csv
data/research/binance_public/cost_pilot/signal_entry_filter_experiment_run2.json
data/research/binance_public/cost_pilot/signal_entry_filter_pair_results_run2.csv
```

## Objetivo

Ultima tentativa de resgatar o sinal de reversao a media: teste de
falsificacao ex-ante do lado da ENTRADA. Varrer o gate causal
`max_half_life_hours` (meia-vida OU trailing, conhecida no momento da
entrada, nunca full-sample) numa grade fixa e pre-registrada, para ver se
algum filtro de entrada seleciona uma subpopulacao com edge liquido real.
Nao filtra trades ex-post por `bars_held`/`outcome`/PnL realizado.

## Regra De Decisao Pre-Registrada (identica nas duas execucoes)

- CONTINUE_SIGNAL_ITERATION apenas se algum threshold da grade tiver **net
  profit factor >= 1.10 E trade_count >= 200**.
- Caso contrario, STOP_SIGNAL_ITERATION.
- Ressalva de comparacoes multiplas: mesmo um CONTINUE isolado e evidencia
  fraca (a grade tem varios thresholds); exigiria confirmacao out-of-sample
  antes de qualquer credito.
- Anti-p-hacking: a grade inteira e reportada, nunca so o melhor bucket.

Em ambas as execucoes, `max_half_life_hours=240` reproduziu o Sprint 8
canonico exatamente (todos os deltas de metrica 0.0, delta de pares
aprovados 0) antes de qualquer comparacao ser aceita.

## Run 1 -- grade `[240, 120, 72, 48, 24, 12]` horas (NAO-VINCULANTE)

| max_half_life_h | Trades | Gross bps/trade | Net PF | Hit rate | Approved pairs |
| --- | --- | --- | --- | --- | --- |
| 240 | 62878 | -0.7673 | 0.7817 | 56.41% | 0 |
| 120 | 62878 | -0.7673 | 0.7817 | 56.41% | 0 |
| 72 | 62874 | -0.7739 | 0.7816 | 56.41% | 0 |
| 48 | 62870 | -0.7758 | 0.7816 | 56.41% | 0 |
| 24 | 62861 | -0.7560 | 0.7818 | 56.41% | 0 |
| 12 | 62838 | -0.7816 | 0.7813 | 56.41% | 0 |

**Auditoria de grade vinculante**: de 240h para 12h, a grade excluiu apenas
40 de 62.878 trades (0,0636%) -- muito abaixo do piso de 5% para considerar
a grade vinculante. **Conclusao do Run 1 isolado, corretamente escopada**:
esta grade especifica nunca atingiu um threshold que realmente filtrasse
entradas; a distribuicao de meia-vida trailing das entradas ja esta quase
inteiramente abaixo de 12h. Isto NAO e evidencia contra filtro de entrada em
geral -- e evidencia de que a grade precisava descer muito mais para morder.
(Achado original da revisao formal do Quant Research Agent.)

## Run 2 -- grade `[240, 12, 6, 3, 1.5, 0.75, 0.375]` horas (VINCULANTE)

Pre-registrada apos o Run 1, descendo bem abaixo do piso anterior.

| max_half_life_h | Trades | Gross bps/trade | Gross PF | Net bps | Net PF | Hit rate | Max DD bps | PROFIT | STOP | VERTICAL | Approved | Passa regra |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 240 | 62878 | -0.7673 | 0.9866 | -861874.19 | 0.7817 | 56.41% | 901350.16 | 43347 | 6509 | 13022 | 0 | nao |
| 12 | 62838 | -0.7816 | 0.9864 | -862195.31 | 0.7813 | 56.41% | 901376.21 | 43308 | 6508 | 13022 | 0 | nao |
| 6 | 62697 | -0.6669 | 0.9883 | -852964.01 | 0.7824 | 56.41% | 891694.07 | 43170 | 6505 | 13022 | 0 | nao |
| 3 | 60596 | +0.3166 | 1.0057 | -763798.93 | 0.7917 | 56.47% | 801728.27 | 41389 | 6264 | 12943 | 0 | nao |
| 1.5 | 32780 | -0.4010 | 0.9918 | -430911.98 | 0.7591 | 54.96% | 447073.43 | 20782 | 3280 | 8718 | 1 | nao |
| 0.75 | 4849 | -0.2748 | 0.9934 | -61774.38 | 0.7319 | 52.26% | 65958.72 | 2726 | 388 | 1735 | 11 | nao |
| 0.375 | 74 | +5.4379 | 1.1559 | -510.92 | 0.8327 | 45.95% | 1307.31 | 30 | 6 | 38 | 3 | nao |

**Auditoria de grade vinculante**: de 240h para 0,375h, a grade excluiu
99,88% dos trades (62.878 -> 74) -- claramente vinculante. Esta grade
realmente exercitou a hipotese de entrada.

**Decisao (regra pre-registrada aplicada literalmente): `STOP_SIGNAL_ITERATION`.**
Nenhum threshold tem simultaneamente net PF >= 1,10 E trade_count >= 200. O
threshold mais apertado (0,375h) tem net PF 0,833 (ainda abaixo de 1,10) E
apenas 74 trades (abaixo de 200) -- falha os dois criterios da regra.

## Observacao Descritiva (NAO faz parte da decisao pre-registrada)

Esta secao e comentario honesto sobre um padrao visivel na grade do Run 2,
explicitamente rotulado como NAO-decisorio para nao violar a disciplina
anti-p-hacking da task: a regra de decisao acima e a unica que determina
CONTINUE/STOP, e ela ja disse STOP.

Dito isso, o padrao e real e vale registrar para trabalho futuro: o **gross
profit factor** (pre-custo) sobe de forma nao-monotonica mas visivelmente
conforme a meia-vida encolhe -- 0,987 em 240h, cruza 1,0 em 3h (1,006), e
atinge 1,156 em 0,375h, com gross bps/trade indo de -0,77 para +5,44. Ou
seja, ha uma concentracao real de edge BRUTO nas entradas de reversao mais
rapida. Duas razoes impedem tratar isso como um resultado: (1) o custo fixo
conservador (12bps/perna round-trip + funding) ainda supera esse gross edge
em todos os thresholds -- net PF nunca passa de 0,833; (2) no unico
threshold onde o gross edge aparece forte (0,375h), a amostra cai para 74
trades e apenas 3 pares -- pequena demais para distinguir sinal de ruido
estatistico, e a propria regra pre-registrada exige >= 200 trades por essa
razao.

Se o usuario ou uma sessao futura quiser perseguir isso, o proximo passo
correto NAO e afrouxar a regra pos-hoc -- e um NOVO pre-registro dedicado
(ex: threshold unico fixado ex-ante entre 0,5h-1h, com custo round-trip
reduzido testado explicitamente como sensibilidade, e um universo/janela
maior para acumular amostra suficiente antes de julgar).

## Decisao Final Consolidada

`STOP_SIGNAL_ITERATION` -- em ambas as execucoes formalmente pre-registradas
(a nao-vinculante e a vinculante), nenhum threshold cumpriu a regra de
decisao. A grade vinculante (Run 2) mostra que existe uma concentracao real
de edge bruto em entradas de reversao muito rapida, mas ela nao sobrevive ao
custo conservador na amostra disponivel. Isto encerra a Signal Iteration 1
(TASK-SIG-001/002/003) do jeito que a task pediu: a evidencia acumulada
(SIG-001: sem edge liquido agregado; SIG-002: cap de saida piora; SIG-003:
filtro de entrada nao vinculante ate morder, e quando morde nao ha amostra
suficiente para confirmar) nao sustenta continuar iterando este sinal com os
dados e universo atuais. Sprint 10 permanece NAO ABERTA. Decisao macro
(pivotar formulacao, mudar universo/janela, ou pausar) volta para o usuario.

## Limites

- O backtest continua permitindo trades sobrepostos, como no Sprint 8
  canonico -- nenhuma das metricas aqui representa uma unica posicao
  deployada.
- Custo continua sendo a suposicao fixa conservadora do backtest estatistico
  (nao medicao).
- Nada neste experimento abre Sprint 10, paper trading ou live trading.
- `max_half_life_hours` e o unico parametro variado; nenhum outro campo do
  `StatisticalBacktestConfig` mudou entre variantes.
