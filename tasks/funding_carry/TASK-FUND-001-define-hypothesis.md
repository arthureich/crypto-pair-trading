# TASK-FUND-001 - Definir e pre-registrar a hipotese de funding-rate carry

## Dono

Quant Research Agent

## Revisor

Backtest Agent + PM Agent

## Workstream

Funding Carry Signal Iteration (aberta por ADR-0013, `project_control/DECISIONS.md`)

## Contexto obrigatorio

```text
project_control/DECISIONS.md (ADR-0010, ADR-0011, ADR-0012, ADR-0013)
project_control/PROJECT_STATE.md
reports/backtest_statistical.md
reports/passive_execution_variant.md
docs/historical_dataset.md (secao "Known Risks")
src/research/historical_dataset.py (_merge_funding_asof)
src/research/pair_selection.py (_evaluate_symbol, _funding_bps_per_day)
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv.gz
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.json
```

O sinal Kalman/OU de reversao a media foi encerrado (ADR-0010, ADR-0012)
sob duas hipoteses independentes: nao tem edge estatistico bruto
exploravel (Signal Iteration 1), e mesmo quando tem, a execucao realista
(agressiva ou passiva) nao consegue captura-lo de forma liquida-positiva
(Sprint 9/10). O usuario decidiu pivotar para uma familia de sinal
estruturalmente diferente: funding-rate carry. Esta tarefa **define e
pre-registra** a hipotese antes de qualquer codigo de backtest ser escrito
-- a mesma disciplina que pegou o grid nao-vinculante da TASK-SIG-003 Run 1
antes de aceitar um resultado.

Esta tarefa NAO escreve codigo de sinal nem roda backtest. Entrega e um
documento de especificacao, revisado formalmente, antes de TASK-FUND-002
comecar.

## Achado de auditoria (motivador, ja verificado nesta sessao)

```text
- funding_rate_asof e dado real de settlement da Binance (nao proxy nem
  estimativa), unido causalmente aos bares via
  pd.merge_asof(..., direction="backward") em
  historical_dataset.py::_merge_funding_asof (junta por close_time <=
  funding_time mais recente) -- nunca usa uma taxa de funding futura.
- Cobertura 100% para os 20 simbolos do universo estatistico da Sprint 7,
  horario, 2023-06-01 a 2026-05-31 (26.304 barras/simbolo), incluindo
  mark_close/index_close/premium_close (o premium index mark-vs-index, que
  e o insumo mecanico real da formula de funding da Binance).
- Nao existe dado de spot no projeto -- tudo e USD-M perpetual. Uma
  estrategia de "basis" aqui usa o premium index (mark vs index), nao
  spot-vs-perp.
- Nao e necessario nenhum novo download: o dataset ja normalizado da
  Sprint 7 e suficiente para o backtest estatistico completo.
- funding_rate_asof ja e usado hoje (pair_selection.py, statistical_backtest.py)
  apenas como CUSTO de uma estrategia de reversao a media -- nunca como
  fonte de alpha. Esta tarefa e a primeira a trata-lo como sinal.
```

## Hipotese pre-registrada

### Universo

Os mesmos 20 simbolos do research gate estatistico da Sprint 7
(`sprint7_binance_usdm_202306_202605_research_gate.json`), mesma janela
(2023-06-01 a 2026-05-31), mesmas barras horarias ja normalizadas e
checksum-verificadas. Nenhum novo download.

### Sinal e regra de rebalanceamento

```text
1. Rebalancear em cada evento real de funding settlement da Binance
   (~3x/dia, via funding_time/funding_interval_hours ja normalizados).
2. Em cada tempo de decisao t (a barra cujo close_time corresponde ao
   settlement), usar SOMENTE funding_rate_asof causal ja conhecido
   naquele t (a ultima taxa liquidada, nunca uma taxa futura).
3. Ranquear os 20 simbolos por funding_rate_asof em t.
4. Posicao: SHORT nos K simbolos de funding mais positivo (mais caro
   ficar comprado -> short recebe funding); LONG nos K simbolos de
   funding mais negativo/baixo (mais barato ficar comprado / short paga
   funding -> long recebe ou paga menos).
5. Peso igual (equal notional) dentro de cada lado; book dollar-neutro
   (notional total long = notional total short).
6. Manter exatamente um intervalo de funding (rebalanceamento completo a
   cada evento, sem holding parcial entre rebalanceamentos).
```

### Construcao do retorno

```text
PnL por rebalanceamento = 
    funding recebido/pago no book (funding_rate_asof aplicado a cada leg)
  + retorno de preco do book long-short no intervalo (ruido remanescente,
    nao hedgeado por beta -- apenas dollar-neutro cross-sectional)
  - custo de transacao (ver Custo)
```

### Custo (fase 1: estatistico, conservador fixo)

Reusa exatamente o padrao de custo ja construido e revisado no Sprint 8
canonico (`src/backtest/statistical_backtest.py`, secao 3.3 de
`reports/backtest_statistical.md`): uma constante fixa conservadora de
fees/slippage por perna round-trip, explicitamente rotulada como suposicao,
nao medicao. Nao reusa a logica de triple barrier (nao se aplica a uma
estrategia de rebalanceamento periodico, nao de entrada/saida por z-score).

Fase 2 (apenas se a fase 1 passar o gate): reusar
`fill_model.py`/`execution_simulator.py`/`replay_engine.py` (ExecutionStyle
MARKET_IOC e LIMIT_MAKER_TTL, ja signal-agnostic per ADR-0012) para
verificar realismo de execucao no unico mes com evidencia real de custo
tick-a-tick verificada (Junho/2023), mesma logica de duas fases (estatistico
depois executavel) ja aplicada ao sinal anterior.

### Configuracao pre-registrada (nao sujeita a otimizacao ex-post)

```text
PRIMARIA (decisao de gate depende so desta):
  K = 5 (short os 5 de funding mais alto, long os 5 de funding mais baixo,
         dos 20 simbolos)

SECUNDARIAS (reportadas de forma descritiva, nao decisorias):
  K = 3
  K = 8
```

### Criterio de gate (pre-registrado, binario, decidido antes de rodar)

```text
Gate PASSA se, na configuracao PRIMARIA (K=5), no periodo completo
2023-06/2026-05:
  net_profit_factor >= 1.10  (mesmo limiar do Sprint 8 canonico, para
                               consistencia metodologica entre familias de
                               sinal deste projeto)
  E numero de rebalanceamentos resolvidos >= 500 (piso de poder estatistico;
                               a janela completa tem ~3.285 eventos de
                               funding esperados, entao este piso e
                               trivialmente atingivel salvo problema de
                               dados -- serve como guarda-fail-closed, nao
                               como restricao real)

Se K=5 nao passar, o resultado e NAO PASSA -- nao ha re-tentativa com outro
K apos ver o resultado de K=5. K=3/K=8 sao reportados como sensibilidade
descritiva, nunca promovidos a "o resultado" se K=5 falhar.
```

### Invariantes obrigatorios (causalidade e fail-closed)

```text
- funding_rate_asof usado em t deve ter funding_time <= o close_time da
  barra de decisao (nunca uma taxa futura) -- verificado por teste
  dedicado antes de aceitar qualquer resultado.
- Simbolo sem funding_rate_asof disponivel em t e excluido do
  ranking/rebalanceamento naquele t, nao recebe funding assumido/zerado
  silenciosamente.
- Sem dado (gap) => intervalo pulado para aquele simbolo, nunca
  interpolado ou preenchido para frente.
- Nenhum parametro (K, threshold, janela) muda depois de ver o resultado
  de K=5.
```

## Fora de escopo (desta tarefa e de TASK-FUND-002)

```text
- Novo download de dados.
- Alavancagem, paper trading, live trading.
- ML, XGBoost, meta-labeling, P_fill/P_profit.
- Reformular a hipotese apos ver resultados intermediarios (qualquer
  mudanca de regra exige uma nova tarefa pre-registrada, como na Signal
  Iteration 1).
- Hedge por beta/Kalman entre as pernas (o book e apenas dollar-neutro
  cross-sectional nesta primeira formulacao).
```

## Arquivos permitidos

```text
tasks/funding_carry/
project_control/
```

## Arquivos proibidos

```text
src/ (nenhum codigo nesta tarefa)
scripts/
tests/
data/ (nenhum novo dado)
```

## Criterio de pronto

```text
1. Hipotese, universo, regra de rebalanceamento, construcao de retorno,
   modelo de custo (fase 1 e 2) e criterio de gate documentados e
   pre-registrados nesta tarefa (feito, ver secoes acima).
2. Verificado que funding_rate_asof e causal (merge_asof backward por
   close_time) -- confirmado por leitura direta de
   historical_dataset.py::_merge_funding_asof nesta sessao.
3. Configuracao primaria (K=5) e secundarias (K=3, K=8) fixadas antes de
   qualquer execucao.
4. Revisao formal do Backtest Agent + PM Agent registrada abaixo antes de
   TASK-FUND-002 ser marcada READY.
```

## Status

DONE

## Progresso

100%

## Revisao formal

```text
Backtest Agent: PASSA. Custo fase 1 reusa o padrao ja revisado do Sprint 8
canonico em vez de inventar um novo modelo; construcao de retorno
(funding + preco - custo) e explicita e nao mistura fases; ranking
cross-sectional dollar-neutro e uma abstracao simples e testavel.

PM Agent: PASSA. Gate pre-registrado e binario (K=5 decide, K=3/K=8 sao
descritivos), evitando o erro de grid nao-vinculante da TASK-SIG-003 Run 1.
Sem download novo, sem ML, sem promocao a paper/live -- consistente com
ADR-0013.
```

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` e `TASK_BOARD.md` marcando
`TASK-FUND-001` DONE e `TASK-FUND-002` (implementar `src/research/
funding_carry.py` + backtest estatistico + rodar real no dataset ja
existente) como proxima tarefa, sujeita a confirmacao explicita do usuario
antes de iniciar.
