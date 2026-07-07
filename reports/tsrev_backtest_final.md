# TSREV Backtest Final Result (Research Family C)

Status: real result for the pre-registered grid in `docs/pre_registers/TASK-TSREV-001.md`. Only the primary cell (Family A, 24h, out-of-sample) decides the gate.

**GATE (primary, decisive): NAO_PASSA**

Out-of-sample period: 2025-06-01 through end of dataset.
Buy-and-hold benchmark max drawdown (OOS): 11003.94 bps.

## Primary cell: Family A (Time-Series Reversal), 24h

| Period | Trades | Win rate | Net PnL (bps) | Net PF | Max DD (bps) | Gate |
|---|---:|---:|---:|---:|---:|---|
| Out-of-sample (decisive) | 3941 | 52.68% | 7690.14 | 1.01 | 65719.66 | NAO_PASSA |
| In-sample (context only) | 7039 | 52.71% | -48496.48 | 0.95 | 105393.02 | NAO_PASSA |
| Full sample (context only) | 10980 | 52.70% | -40806.34 | 0.97 | 140335.34 | NAO_PASSA |

## Secondary cells: Family A (Time-Series Reversal), other horizons

Descriptive only -- cannot decide the gate, cannot override the primary result above, per the pre-registered rule.

| Horizon | Trades (OOS) | Win rate (OOS) | Net PnL bps (OOS) | Net PF (OOS) |
|---|---:|---:|---:|---:|
| 6h | 11120 | 49.14% | -144485.11 | 0.83 |
| 12h | 6732 | 49.85% | -109354.24 | 0.85 |
| 48h | 2216 | 54.15% | 36341.74 | 1.09 |

## Secondary cells: Family B (Cross-Sectional Reversal), full sample

Descriptive only. Full sample (no OOS split -- purely exploratory).

| Horizon | Rebalances | Net PnL (bps) | Net PF |
|---|---:|---:|---:|
| 6h | 4262 | -45588.87 | 0.69 |
| 12h | 2130 | -17822.88 | 0.81 |
| 24h | 1064 | -9035.01 | 0.87 |
| 48h | 531 | 2492.81 | 1.06 |

## Conclusão

**Gate NAO PASSA na celula primaria (Familia A, 24h, out-of-sample), falhando
em 2 dos 4 criterios simultaneamente:**

```text
net_profit_factor 1,0143  vs limiar > 1,05     -> FALHA (perto)
net_pnl_bps       +7.690,14  vs > 0            -> PASSA
max_drawdown_bps  65.719,66 vs baseline 11.003,94 -> FALHA (muito, ~6x o benchmark)
resolved_trades   3.941     vs >= 200           -> PASSA
```

O criterio de drawdown e o mais decisivo dos dois que falham: a estrategia
teria arriscado ~6x mais que simplesmente manter os 20 ativos em
buy-and-hold equal-weight no mesmo periodo, para um retorno liquido de
apenas 7.690bps em 12 meses. Isso e um perfil de risco/retorno inaceitavel
independente do profit factor.

**A divergencia in-sample vs out-of-sample e o achado mais informativo
deste relatorio, e valida a decisao metodologica de exigir um periodo
out-of-sample:**

```text
Win rate:  in-sample 52,71%  vs  out-of-sample 52,68%  (praticamente identico)
Net PnL:   in-sample -48.496,48bps  vs  out-of-sample +7.690,14bps  (sinal invertido)
```

O win rate -- a evidencia mais direta de que existe reversao bruta -- e
estavel e consistentemente acima de 50% nos dois periodos. O que muda e a
distribuicao de magnitude dos ganhos/perdas: no periodo de desenvolvimento
(2023-06 a 2025-05), perdas maiores dominaram; no periodo out-of-sample
mais recente (2025-06 a 2026-05), o resultado melhorou para
liquido-positivo, mas nao o suficiente para cruzar o gate. Se este projeto
tivesse decidido o gate no full-sample ou no in-sample (sem separar um
periodo out-of-sample), a conclusao teria sido "claramente negativo" --
menos informativa que o resultado real, que mostra uma reversao bruta real
e temporalmente estavel, atropelada por custo e por um perfil de risco
pior que o mercado.

**Uma celula secundaria (Familia A, 48h) cruza DOIS dos quatro criterios
que a primaria nao cruzou** -- net profit factor 1,09 (> 1,05) e net PnL
+36.341,74bps (> 0) -- **mas ainda falha no MESMO criterio de drawdown**
(71.610,74bps de max drawdown vs o mesmo benchmark buy-and-hold de
11.003,94bps -- ainda ~6,5x maior). Ou seja, 48h nao passa o gate composto
integralmente, so fica mais perto. Isto NAO reabre nem substitui a decisao
da celula primaria de qualquer forma -- e exatamente a situacao que a
regra de decisao pre-registrada foi desenhada para prevenir: apos ver 8
celulas, uma delas (inclusive uma que nao foi a escolhida a priori) parece
relativamente melhor. Promover 48h agora, depois de ver este resultado,
seria o mesmo erro metodologico que a TASK-SIG-003 evitou ao nao promover
buckets de half-life vistos ex-post. O padrao encontrado -- horizontes
mais longos (48h em ambas as familias, A e B) consistentemente performam
melhor que os mais curtos (6h, 12h), mas SEMPRE com drawdown pior que o
buy-and-hold -- e uma observacao descritiva legitima e um bom candidato a
UM FUTURO pre-registro independente (por exemplo, testando se algum
mecanismo de controle de risco reduz o drawdown sem destruir o profit
factor), nao uma conclusao desta pesquisa.

**Decisao:** aceitar NAO PASSA como resultado final da hipotese primaria
pre-registrada (Time-Series Reversal, 24h). Nenhum parametro muda depois
de ver este resultado. Isto encerra a Research Family C (TSREV) por ora --
decisao de abrir um novo pre-registro independente testando horizontes
mais longos (o padrao "48h > 24h > 12h > 6h" observado em ambas as
familias) pertence ao usuario.
