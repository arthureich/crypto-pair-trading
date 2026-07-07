# Cross-Sectional Mean Reversion Backtest Final Result (Research Family E, TASK-CS-002)

Status: real result for the pre-registered hypothesis in `docs/pre_registers/TASK-CS-002.md` -- 24h horizon, deliberately distinct from CS-001's 168h (a same-horizon mirror would fail the gate by mathematical construction, see ADR-0018). Gate is decided ONLY on the out-of-sample period.

**GATE (decisive): NAO_PASSA**

Out-of-sample period: 2025-06-01 through end of dataset (175200 hourly bars).
Buy-and-hold benchmark max drawdown (OOS): 11003.94 bps.

## Configuration

```text
{
  "cost_bps_roundtrip": 6.0,
  "formation_hours": 24,
  "min_trades_for_gate": 200,
  "profit_factor_gate": 1.1,
  "quintile_k": 4
}
```

## Result

| Period | Legs resolved | Win rate | Net PnL (bps) | Net PF | Max DD (bps) | Gate |
|---|---:|---:|---:|---:|---:|---|
| Out-of-sample (decisive) | 2912 | 49.35% | -2985.35 | 0.94 | 3396.38 | NAO_PASSA |
| In-sample (context only) | 5840 | 50.14% | -294.52 | 1.00 | 5711.47 | NAO_PASSA |
| Full sample (context only) | 8752 | 49.87% | -3279.87 | 0.98 | 6305.71 | NAO_PASSA |

## Conclusao

**Gate NAO PASSA, consistente em todos os periodos.** Net profit factor
0,94 e net PnL -2.985,35bps sobre 2.912 pernas resolvidas na janela OOS
decisiva -- assim como CS-001, este NAO e um quase-empate: PF fica
abaixo do empate em todos os tres cortes (0,94 OOS, 1,00 in-sample, 0,98
full-sample). A hipotese nunca cruza o gate em nenhum periodo.

**O efeito bruto pre-custo tambem e negativo** (-801,35bps OOS) -- mesmo
padrao de CS-001: nao ha edge direcional detectavel para o custo
consumir. Win rate fica em 49,35% (OOS) e 50,14% (in-sample),
essencialmente ruido de moeda-honesta, igual ao observado em CS-001
(49,40%/51,96%). O criterio de drawdown, isoladamente, teria passado
(3.396,38bps vs baseline 11.003,94bps) -- a falha e em PF/PnL, nao em
risco, o mesmo padrao de CS-001.

**A divulgacao previa registrada no pre-registro se confirma.** TSREV
Familia B (24h, z-score, decil k=2, full-sample, apenas descritivo) ja
havia mostrado profit factor 0,87 e net PnL -9.035,01bps -- direcionalmente
consistente com este resultado, ainda que a metodologia (retorno bruto
vs normalizado, k=4 vs k=2, OOS-only vs full-sample) seja distinta o
suficiente para nao ser o mesmo teste. As duas evidencias, agora
independentes e ambas negativas, reforcam mutuamente a leitura de que
reversao cross-sectional de curto prazo (24h) neste universo especifico
de 20 perpetuos USD-M liquidos nao sobrevive a custo realista, seja com
ranking por retorno bruto ou por retorno normalizado por volatilidade.

**Decisao final, per o roteiro pre-registrado (ADR-0018) e a
recomendacao do usuario:** com CS-001 (momentum semanal) e CS-002
(reversao 24h) ambos fechando NAO PASSA -- e nem o efeito bruto
pre-custo presente em nenhum dos dois -- a linha de pesquisa baseada
EXCLUSIVAMENTE em fatores classicos de preco (candles) fecha nesta
sessao. Isso inclui, cumulativamente, cinco familias de pesquisa
internas e replicadas (A: Kalman/OU mean-reversion; B: Funding Carry;
TSMOM: Donchian breakout; C: TSREV; E: Cross-Sectional Momentum e Mean
Reversion), todas com o mesmo veredito NAO PASSA sob custo realista
neste universo/periodo. CS-003 (Residual Momentum), CS-004 (PCA
Statistical Arbitrage) e CS-005 (Ensemble) permanecem backlog
formalmente nao cancelado, mas per a recomendacao do usuario o proximo
passo natural e abrir uma categoria de informacao genuinamente nova
(Market Microstructure / Alternative Data: open interest, order flow,
liquidacoes, funding como feature) -- decisao e pre-registro que
pertencem ao usuario, nao automatico.
