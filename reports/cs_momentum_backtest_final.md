# Cross-Sectional Momentum Backtest Final Result (Research Family E, TASK-CS-001)

Status: real result for the pre-registered hypothesis in `docs/pre_registers/TASK-CS-001.md` -- a faithful replication of weekly cross-sectional crypto momentum (Liu & Tsyvinski 2021 style), not an internally-invented signal. Gate is decided ONLY on the out-of-sample period.

**GATE (decisive): NAO_PASSA**

Out-of-sample period: 2025-06-01 through end of dataset (175200 hourly bars).
Buy-and-hold benchmark max drawdown (OOS): 11003.94 bps.

## Configuration

```text
{
  "cost_bps_roundtrip": 6.0,
  "formation_hours": 168,
  "min_trades_for_gate": 200,
  "profit_factor_gate": 1.1,
  "quintile_k": 4
}
```

## Result

| Period | Legs resolved | Win rate | Net PnL (bps) | Net PF | Max DD (bps) | Gate |
|---|---:|---:|---:|---:|---:|---|
| Out-of-sample (decisive) | 408 | 51.96% | -370.61 | 0.98 | 2154.52 | NAO_PASSA |
| In-sample (context only) | 832 | 49.40% | 3342.54 | 1.08 | 3153.01 | NAO_PASSA |
| Full sample (context only) | 1240 | 50.24% | 2971.93 | 1.05 | 4453.31 | NAO_PASSA |

## Conclusao

**Gate NAO PASSA, e nao por margem minima.** Net profit factor 0,98 (por
baixo do empate) e net PnL -370,61bps sobre 408 pernas resolvidas na
janela out-of-sample decisiva -- este e um resultado claramente negativo,
nao um quase-empate como o funding carry incremental (0,0096 de
diferenca) ou o TSREV primario (falhou por drawdown, nao por PF).

**Diferente de todas as familias anteriores, aqui o efeito BRUTO (antes
de custo) ja e essencialmente nulo no periodo OOS.** Gross PnL
-64,61bps sobre 408 pernas -- ou seja, o problema nao e "existe edge mas
o custo consome" (o padrao visto em TSMOM e Funding Carry fase 1); e
"nao ha edge direcional detectavel para consumir." O win rate reforca essa
leitura: 51,96% (OOS) e 49,40% (in-sample) -- ambos essencialmente em
torno de 50%, ruido de moeda-honesta. Isso contrasta com o TSREV
primario, que mostrou win rate estavel e genuinamente acima de 50% em
ambos os periodos (52,68% OOS vs 52,71% in-sample) -- TSREV tinha sinal
direcional real que nao sobreviveu a economia; esta replicacao de
momentum nao mostra sinal direcional real para comecar.

**O criterio de drawdown, isoladamente, teria passado.** Max drawdown
OOS (2.154,52bps) fica bem abaixo do benchmark buy-and-hold
(11.003,94bps) -- o gate falha nos criterios de PF e PnL, nao no
criterio de risco.

**O resultado nao depende do split OOS -- a hipotese nunca cruzou o
gate, nem no periodo de desenvolvimento.** Net PF in-sample (1,08) ja
fica abaixo do piso de 1,10 pre-registrado. Diferente do TSREV (onde o
sinal parecia genuino in-sample e so revelou sua fragilidade economica no
OOS), aqui a hipotese simplesmente nao performou o suficiente em nenhum
dos dois periodos.

**Limitacoes explicitas da fidelidade da replicacao (nao invalidam o
resultado, mas devem ser lidas junto dele):**

```text
1. Amplitude (breadth): este universo tem 20 symbols; a literatura
   academica de cross-sectional momentum tipicamente usa centenas de
   ativos. Um quintil de apenas 4 symbols por perna e uma amostra
   transversal muito mais estreita e ruidosa que a original.
2. Periodo/mercado: Liu & Tsyvinski (2021) documenta o efeito em dados
   de 2014-2018; este projeto testa 2023-2026 em USD-M perpetuos --
   mercado mais maduro, mais arbitrado, mais liquido. E plausivel que o
   efeito tenha decaido ou sido competido para fora nesse periodo mais
   recente -- consistente com a leitura de "eficiencia de mercado" ja
   registrada na Fase 1 de Payoff Engineering (BTC/ETH, os symbols mais
   liquidos deste mesmo universo, tambem foram os piores desempenhos ali).
3. Instrumento: o paper original nao e necessariamente sobre futuros
   perpetuos USD-M especificamente -- diferencas de estrutura de mercado
   (funding, alavancagem, quem participa) nao sao controladas aqui.
```

**Decisao final:** per a regra pre-registrada (TASK-CS-001), nenhum
sweep de horizonte, K, ou convencao de peso sera testado apos ver este
resultado. A linha "Cross-Sectional Momentum (replicacao semanal)" fecha
como NAO REPLICADA neste universo/periodo -- um resultado negativo valido
e citavel, nao um trabalho incompleto. Decisao sobre abrir CS-002
(Cross-Sectional Mean Reversion) ou reconsiderar a familia pertence ao
usuario, per o desenho sequencial ja acordado (ADR-0017).
