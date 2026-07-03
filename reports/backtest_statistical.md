# Sprint 8 Canonico -- Backtest Estatistico com Triple Barrier Direcional

Data: 2026-07-03
Sprint: 8 Canonico (`tasks/sprint_08_canonical/`, ver `project_control/DECISIONS.md` ADR-0008/ADR-0009)
Agentes: Quant Research Agent (`triple_barrier.py`), Backtest Agent (`statistical_backtest.py`, execucao real), QA / Chaos Testing Agent, PM Agent (orquestracao, correcao de bugs, gate)

## 1. Por que este relatorio existe

O plano mestre de 28 sprints fornecido pelo usuario especifica, para o Sprint
8 canonico, um backtest **estatistico e barato** (nivel de candle, custo
conservador fixo) antes do trabalho caro com dado real de execucao. Este
projeto havia implementado, na sua Sprint 8 real, algo diferente (walk-forward
cost-aware com evidencia real de custo de Junho/2023) -- ver ADR-0008 para a
reconciliacao dessa divergencia de numeracao. A ADR-0009 decidiu construir o
Sprint 8 canonico retroativamente, como trabalho adicional e distinto, sem
reverter ou sobrescrever o trabalho ja fechado da Sprint 8 real ou da Sprint 9.

Este relatorio documenta esse backtest canonico: metodologia, bugs
encontrados e corrigidos em revisao formal, resultado real nos 41 pares, e
decisao de gate.

## 2. Universo

Todos os **41 pares estatisticos** aceitos pelo research gate da Sprint 7
(`data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.json`,
campo `accepted_pairs`, `statistical_status == "ACCEPT"`) -- **nao** os 31
pares cost-gated nem os 13 pares backtest-approved usados pela Sprint 8/9 nao
canonicas. A ADR-0009 explica essa escolha: o objetivo do Sprint 8 canonico e
um gate barato sobre o universo estatistico completo, antes de qualquer
filtro de custo real.

Dados: barras horarias reais, ja normalizadas e verificadas por checksum na
Sprint 7 (TASK-007-09), de Junho/2023 a Maio/2026 (26.304 barras por simbolo,
20 simbolos, 526.080 linhas totais). Nenhum dado mock ou sintetico foi usado
na execucao real.

## 3. Metodologia

### 3.1 Geracao de sinal (causal)

Reusa exatamente a tecnica ja revisada e usada na Sprint 8 nao-canonica
(`src/research/sprint8.py::generate_pair_signal_intents`): filtro de Kalman
sequencial para spread e beta dinamicos, z-score rolante causal (janela de
168 horas, `min_periods=168`, estatisticas trailing deslocadas em 1 barra), e
um refit causal de Ornstein-Uhlenbeck em janela trailing (168 horas) a cada
barra candidata -- **nao** um unico fit sobre a amostra inteira, o que
reintroduziria o look-ahead ja corrigido na Sprint 8 real. Entrada exige:
`|z| >= 2.0`, Kalman estavel, beta > 0, OU mean-reverting com half-life <=
240 horas.

### 3.2 Saida (triple barrier direcional)

Implementado em `src/research/triple_barrier.py`. Para cada entrada:

- **PROFIT**: z-score cruza de volta para `profit_zscore = 0.0` (reversao a
  media).
- **STOP**: z-score se move `stop_zscore_buffer = 1.0` alem do z de entrada,
  na direcao adversa.
- **VERTICAL**: nenhuma das duas anteriores ocorre dentro do orcamento de
  tempo (`half_life * 4`, capado em 240 barras/horas).
- **NO_DATA**: a serie historica acaba antes de confirmar que o orcamento de
  tempo foi atingido, e nem PROFIT nem STOP ocorreram -- descartado da
  metrica agregada (fail-closed, nao vira "vitoria" nem "derrota" fabricada).

A barreira vertical usa **tempo decorrido real** (via `open_time`), nao
contagem de posicao no array -- importante porque o alinhamento de pares
(`_pair_frame`) descarta silenciosamente qualquer hora ausente em uma das
pernas, entao contagem de barras e tempo decorrido podem divergir sempre que
houver lacunas nos dados reais.

PnL bruto por trade reusa a formula ja revisada na Sprint 8/9: combinacao
ponderada por beta do movimento do spread entre entrada e saida
(`direction * (delta log_price_a - beta * delta log_price_b)` em bps, com
`direction = -1` para SHORT_SPREAD e `+1` para LONG_SPREAD).

### 3.3 Custo (conservador, FIXO -- nao e medicao)

Por especificacao do roadmap, o Sprint 8 canonico usa um custo **estimado e
fixo**, deliberadamente distinto da evidencia real de custo tick-a-tick usada
no Sprint 9 (ADR-0007):

```
cost_bps = funding_carry_bps_per_day (real, Sprint 7) * (bars_held / 24)
         + 2 * conservative_fee_slippage_bps_per_leg_roundtrip
```

- `funding_carry_bps_per_day`: valor real por par, ja calculado na Sprint 7 a
  partir do funding rate historico de cada simbolo.
- `conservative_fee_slippage_bps_per_leg_roundtrip = 6.0 bps`: **suposicao
  explicita, nao medicao.** A taxa taker da Binance USD-M Futures gira em
  torno de 4-5bps por lado sem tier VIP; um round-trip real de apenas taxas
  (entrada + saida) de uma perna ja se aproxima ou excede esse valor antes de
  qualquer slippage. Ou seja, 6.0bps e uma estimativa conservadora **no
  sentido de ser barata demais**, nao no sentido de superestimar custo -- se
  o resultado abaixo ja rejeita a maioria dos pares mesmo com esse piso
  baixo, custo real so pioraria o resultado, nunca o contrario.

### 3.4 Metricas

Por par e agregadas (pool de todos os trades resolvidos de todos os pares):
Sharpe, Sortino, max drawdown, profit factor, hit rate, avg win/loss,
turnover, tempo medio em trade (bars_held).

**Ressalva sobre as metricas** (documentada tambem no docstring do modulo):
cada barra que cruza o limiar de entrada gera sua propria entrada
independente, sem controle de posicao aberta -- trades se sobrepoem no
tempo. `trade_count`/`turnover`/`hit_rate`/`profit_factor`/Sharpe/Sortino
descrevem portanto exposicao concorrente irrestrita, nao o que uma unica
instancia de estrategia deployada teria realizado. Sharpe/Sortino aqui sao
razoes simples media/desvio-padrao por trade (nao anualizadas), e o Sortino
usa desvio-padrao dos trades perdedores, nao a definicao classica de desvio
downside contra uma MAR -- tratar como heuristica interna de ranking, nao
como estatistica comparavel entre estrategias.

### 3.5 Gate

**Profit factor liquido >= 1.10** para o par continuar aprovado, por
especificacao do roadmap.

## 4. Revisao formal e bugs corrigidos

Duas rodadas de revisao independente (4 agentes na primeira passada, 2 agentes
de re-revisao apos as correcoes) encontraram e confirmaram a correcao de 4
bugs P1 reais antes desta execucao:

1. **`triple_barrier.py`** (Backtest Agent): dados insuficientes apos a
   entrada eram rotulados `VERTICAL` com `bars_held` truncado em vez de
   `NO_DATA`, inflando artificialmente o numero de trades "resolvidos" perto
   do fim da janela historica.
2. **`triple_barrier.py`** (QA/Chaos Agent): a barreira vertical usava
   contagem de posicao no array, silenciosamente incorreta na presenca de
   lacunas nos dados (uma barra 100h depois seria tratada como "a proxima
   barra"). Corrigido para usar tempo decorrido real via `open_time`.
3. **`statistical_backtest.py`** (Quant Research Agent E QA/Chaos Agent,
   independentemente, o mesmo bug): `profit_factor_gate_pass` usava
   `math.isfinite()`, que rejeita `+inf` -- um par com 100% de trades
   vencedores (profit factor = infinito, o melhor resultado possivel) era
   marcado como **reprovado**. Corrigido para so excluir `NaN` (caso sem
   trades).
4. **`statistical_backtest.py`** (QA/Chaos Agent): um `funding_carry_bps_per_day`
   nao-finito podia envenenar `net_pnl_bps`/Sharpe/drawdown com `NaN`
   enquanto o gate ainda reportava PASS. Corrigido com fail-closed
   (`StatisticalBacktestError`) antes de qualquer calculo.

Ambas as correcoes foram re-revisadas de forma independente (agentes que nao
viram a primeira revisao) e confirmadas **PASSA**. Suite completa: 270 testes
passando, `ruff check src scripts tests` limpo. Ver `TASK_BOARD.md`
(TASK-008C-01, TASK-008C-02) para o historico completo.

## 5. Resultado real (41 pares, execucao unica, dados reais)

Comando: `scripts/run_sprint8_canonical_backtest.py` (config default:
`entry_zscore=2.0, zscore_window=168, ou_window=168, max_half_life_hours=240,
half_life_multiplier=4.0, max_vertical_bars=240,
conservative_fee_slippage_bps_per_leg_roundtrip=6.0`).

Saida completa: `data/research/binance_public/cost_pilot/sprint8_canonical_backtest_results.json`
(por trade) e `.../sprint8_canonical_backtest_pair_results.csv` (por par).

### 5.1 Agregado (pool de todos os 41 pares)

| Metrica | Valor |
|---|---:|
| Trades resolvidos | 62.878 |
| Gross PnL (bps) | -48.248,03 |
| Custo total (bps) | 813.626,16 |
| Net PnL (bps) | -861.874,19 |
| Hit rate | 56,41% |
| Profit factor | 0,782 |
| Sharpe (por trade) | -0,081 |
| Sortino (por trade) | -0,085 |
| Max drawdown (bps) | 901.350,16 |
| Avg win (bps) | 87,03 |
| Avg loss (bps) | -144,08 |
| Avg bars held | 3,95 horas |

Leitura honesta: o PnL **bruto** medio por trade ja e proximo de zero
(-48.248 bps / 62.878 trades ~ -0,77 bps/trade) -- ou seja, mesmo antes de
qualquer custo, o sinal de reversao a media nao tem edge bruto consistente
neste desenho (entrada em qualquer cruzamento de `|z|>=2`, saida em ~4 horas
em media). O custo fixo (~13-14 bps/trade em media, dominado pelo piso de
12bps de fee/slippage) e suficiente para tornar o resultado liquido
decisivamente negativo. Como a Secao 3.3 explica, 6bps/perna esta no lado
barato da faixa real de taxas da Binance -- custo real tenderia a piorar,
nao melhorar, este resultado.

### 5.2 Por par (ordenado por profit factor, todos falham o gate)

| Par | Trades | Profit Factor | Net PnL (bps) | Hit Rate | Avg Bars Held |
|---|---:|---:|---:|---:|---:|
| ETCUSDT/LTCUSDT | 1441 | 0,960 | -2.910,53 | 58,0% | 3,21 |
| ARBUSDT/ATOMUSDT | 1570 | 0,933 | -7.286,69 | 58,0% | 4,48 |
| AVAXUSDT/DOTUSDT | 1589 | 0,933 | -6.518,54 | 59,7% | 4,50 |
| ARBUSDT/ETCUSDT | 1536 | 0,930 | -6.947,53 | 59,0% | 3,97 |
| ARBUSDT/OPUSDT | 1578 | 0,925 | -7.130,18 | 59,1% | 4,79 |
| ADAUSDT/DOTUSDT | 1569 | 0,920 | -7.186,57 | 57,3% | 4,57 |
| DOGEUSDT/DOTUSDT | 1619 | 0,919 | -9.443,97 | 59,9% | 4,41 |
| DOGEUSDT/ETCUSDT | 1568 | 0,916 | -8.877,70 | 60,2% | 3,81 |
| ARBUSDT/DOTUSDT | 1603 | 0,873 | -14.089,36 | 57,2% | 4,55 |
| ATOMUSDT/DOTUSDT | 1629 | 0,849 | -13.365,93 | 57,9% | 4,54 |
| DOGEUSDT/ETHUSDT | 1455 | 0,847 | -13.053,83 | 56,4% | 2,46 |
| ATOMUSDT/ETCUSDT | 1588 | 0,837 | -15.445,18 | 56,1% | 3,84 |
| DOTUSDT/LINKUSDT | 1519 | 0,833 | -14.890,00 | 57,5% | 4,11 |
| AVAXUSDT/LINKUSDT | 1529 | 0,803 | -20.235,14 | 56,6% | 4,22 |
| AVAXUSDT/SOLUSDT | 1442 | 0,802 | -18.214,66 | 57,2% | 3,39 |
| ARBUSDT/AVAXUSDT | 1536 | 0,799 | -22.560,56 | 59,0% | 3,92 |
| ARBUSDT/ETHUSDT | 1387 (+1 NO_DATA) | 0,798 | -15.724,85 | 55,7% | 2,59 |
| ADAUSDT/AVAXUSDT | 1532 | 0,792 | -20.395,42 | 57,3% | 3,86 |
| ADAUSDT/ETCUSDT | 1547 | 0,790 | -21.351,91 | 59,7% | 3,79 |
| ETCUSDT/LINKUSDT | 1529 (+1 NO_DATA) | 0,790 | -20.273,79 | 57,9% | 3,96 |
| ADAUSDT/ETHUSDT | 1446 | 0,785 | -17.449,61 | 56,3% | 2,48 |
| ADAUSDT/SOLUSDT | 1504 | 0,783 | -21.490,52 | 57,6% | 3,34 |
| DOTUSDT/ETCUSDT | 1500 | 0,779 | -20.047,63 | 57,7% | 3,88 |
| ADAUSDT/LINKUSDT | 1503 | 0,778 | -22.085,97 | 57,8% | 4,05 |
| ETCUSDT/ETHUSDT | 1400 | 0,772 | -15.599,20 | 56,1% | 2,37 |
| ARBUSDT/LINKUSDT | 1466 (+1 NO_DATA) | 0,770 | -24.768,84 | 56,4% | 4,14 |
| ADAUSDT/DOGEUSDT | 1561 | 0,769 | -25.128,53 | 58,1% | 4,33 |
| AVAXUSDT/ETCUSDT | 1598 | 0,760 | -28.495,71 | 58,3% | 4,06 |
| ADAUSDT/ATOMUSDT | 1559 | 0,721 | -31.558,09 | 55,8% | 4,66 |
| ETCUSDT/OPUSDT | 1580 | 0,721 | -31.892,11 | 55,8% | 4,67 |
| ETHUSDT/UNIUSDT | 1584 | 0,714 | -24.117,21 | 53,5% | 4,76 |
| DOTUSDT/ETHUSDT | 1428 | 0,706 | -23.445,11 | 56,0% | 2,51 |
| AVAXUSDT/ETHUSDT | 1449 | 0,697 | -28.387,93 | 54,6% | 2,57 |
| BTCUSDT/SOLUSDT | 1619 | 0,680 | -17.741,69 | 52,6% | 3,37 |
| ADAUSDT/ARBUSDT | 1581 | 0,672 | -40.901,74 | 54,1% | 4,78 |
| ADAUSDT/XRPUSDT | 1567 | 0,664 | -45.085,08 | 56,5% | 5,04 |
| DOTUSDT/OPUSDT | 1542 | 0,648 | -43.170,40 | 55,9% | 4,92 |
| ETHUSDT/OPUSDT | 1607 | 0,624 | -38.648,79 | 51,0% | 5,31 |
| ETHUSDT/SOLUSDT | 1537 | 0,609 | -30.764,12 | 51,1% | 3,57 |
| BTCUSDT/ETHUSDT | 1553 | 0,587 | -19.181,11 | 49,1% | 2,61 |
| ETHUSDT/LINKUSDT | 1528 | 0,486 | -46.012,44 | 49,1% | 4,63 |

Tabela completa (incluindo Sharpe/Sortino/drawdown/turnover por par) no CSV
de saida. Apenas 5 dos 480 trades totais de todo o universo (0,008%) ficaram
sem resolucao (`NO_DATA`, descartados da metrica, nao inflados como
vitoria/derrota).

## 6. Decisao de gate

**NAO PASSA para nenhum dos 41 pares** (0/41 com profit factor liquido >=
1.10). Melhor resultado individual: ETCUSDT/LTCUSDT com profit factor 0,960
-- ainda abaixo do limiar. Portfolio agregado: profit factor 0,782.

Este resultado e **consistente** com o resultado da Sprint 9 (0/13 pares
backtest-approved net-positive sob custo real tick-a-tick, ver
`reports/backtest_executable_v1.md`) -- ambos os backtests, com metodologias
e universos diferentes, chegam a conclusao de que o sinal de reversao a
media construido nesta pesquisa nao sobrevive a custos de transacao
realistas, mesmo conservadoramente estimados.

## 7. Ressalva obrigatoria: este resultado NAO e diretamente comparavel ao da Sprint 9

- **Sprint 8 canonico (este relatorio)**: custo **estimado e fixo**
  (6.0bps/perna de fee+slippage assumido, nao medido, mais funding real do
  Sprint 7). Universo: 41 pares estatisticos (sem filtro de custo). Execucao:
  candle de 1h, sem simulacao de fill/latencia/livro de ordens.
- **Sprint 9 (`reports/backtest_executable_v1.md`)**: custo **real,
  medido**, a partir de dados tick-a-tick de bookTicker de Junho/2023
  (ADR-0007), com simulacao completa de fill parcial, latencia, TTL,
  ACK_UNKNOWN e leg-fill-mismatch. Universo: 13 pares que ja haviam sobrevivido
  ao filtro de custo real E ao backtest cost-aware da Sprint 8 real (nao
  canonica).

Os dois resultados apontam na mesma direcao (nenhum par sobrevive a custo
realista), mas **nao devem ser somados, promediados, ou citados um pelo
outro** -- sao experimentos com premissas de custo, universo e granularidade
diferentes por design. A convergencia dos dois resultados negativos e
evidencia mais forte do que qualquer um isoladamente, mas cada um deve ser
citado com sua propria metodologia explicita.

## 8. Proximos passos sugeridos (nao decididos aqui)

- O gross PnL por trade proximo de zero (Secao 5.1) sugere que o problema nao
  e apenas custo -- o sinal de entrada (`|z|>=2` com saida em ~4h) pode nao
  ter edge bruto suficiente mesmo sem custo. Investigar parametros de entrada
  mais seletivos (z-score mais alto, half-life mais restrito) ou uma
  formulacao de sinal diferente seria o proximo passo natural de pesquisa,
  fora do escopo desta tarefa de gate.
- ADR-0008 (debito tecnico de numeracao) pode ser fechado apos este relatorio
  -- ver atualizacao correspondente em `RISKS.md`.
