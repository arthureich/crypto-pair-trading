# TASK-ALT-004 - Definicao e pre-registro: Regime Conditioning Feasibility Diagnostic sobre TSREV 24h

## Status

DONE (definicao e execucao). Quarta task da Research Phase II, aberta apos
`TASK-ALT-003` encontrar informacao robusta de regime/volatilidade, mas
sem alpha direcional. Ver `project_control/DECISIONS.md` ADR-0022.

## Workstream

Research Phase II - Alternative Information / Family J follow-up. Esta
task testa um uso operacional minimo do achado de regime: condicionar a
celula TSREV primaria (Family A, 24h) para bloquear entradas quando o
regime de volatilidade causal esta alto.

## Natureza desta task: feasibility diagnostic, nao validacao final

Esta task usa o periodo OOS antigo de TSREV (2025-06-01 a 2026-05-31),
que ja foi analisado em TASK-TSREV-002, TASK-PAYOFF-001 e TASK-ALT-003.
Portanto, mesmo que o filtro passe o gate abaixo, o resultado NAO e uma
confirmacao limpa nem autoriza paper/live. Um PASSA aqui significa apenas:
"vale pre-registrar e testar em novo OOS futuro." Um NAO_PASSA encerra
esta variante.

## Hipotese primaria

```text
Bloquear entradas TSREV 24h quando realized_vol_168h[t] esta acima do
percentil causal 67% da propria historia recente de 90 dias do symbol.
```

Intuicao: TASK-ALT-003 mostrou que volatilidade realizada carrega
informacao forte sobre movimento absoluto futuro. A celula TSREV 24h ja
falhou principalmente por drawdown excessivo. Logo, um filtro simples de
alto regime de volatilidade pode reduzir a cauda de risco. Isto e uma
hipotese de controle de risco, nao de lado direcional.

## Regra exata do filtro

Para cada symbol:

```text
hourly_return[t] = log_price[t] - log_price[t-1]
realized_vol_168h[t] = hourly_return.shift(1).rolling(168h).std()
vol_q67_90d[t] = realized_vol_168h.shift(1).rolling(2160h).quantile(0.67)

allow_entry[t] = realized_vol_168h[t] <= vol_q67_90d[t]
```

Se `realized_vol_168h[t]` ou `vol_q67_90d[t]` estiver ausente, a entrada
falha fechada (`allow_entry=false`). Nenhum sweep de percentil: 67% foi
escolhido como corte de tercil superior antes desta execucao.

## Estrategia condicionada

```text
Base: TSREV Family A, horizon_hours=24, zscore_threshold=1.0,
      cost_bps_roundtrip=6.0, pesos inverse-vol exatamente como
      src/research/tsrev.py.

Filtro: manter apenas trades cuja barra de entrada tenha allow_entry=true.
Pesos das trades remanescentes sao renormalizados por inverse-vol dentro
do conjunto filtrado, para manter comparabilidade com o sizing da TSREV
original e evitar que o filtro "passe" apenas por reduzir exposicao total.
```

## Periodo

```text
Feasibility OOS antigo: 2025-06-01 a 2026-05-31.
Contexto baseline: resultado original TSREV 24h OOS no mesmo periodo.
```

## Gate de feasibility

Todos os criterios abaixo devem passar simultaneamente no conjunto filtrado:

```text
net_profit_factor > 1.05
E net_pnl_bps > 0
E max_drawdown_bps <= buy_and_hold_max_drawdown_bps no mesmo periodo
E resolved_trade_count >= 200
```

Mesmo gate estrutural da TASK-TSREV-001. Adicionalmente, o relatorio deve
comparar o max drawdown filtrado com o baseline TSREV original, mas essa
comparacao e diagnostica; o gate literal continua sendo o buy-and-hold
baseline, como no pre-registro original.

## Invariantes obrigatorios

```text
- Nenhuma feature usa dados posteriores a t.
- `vol_q67_90d[t]` usa shift(1), excluindo o valor atual da propria
  distribuicao de corte.
- Entradas com regime ausente bloqueiam, nao passam.
- Nenhum parametro TSREV muda.
- Nenhum novo lado, symbol filter, horizonte, z-score threshold, custo,
  percentil ou janela sera testado nesta task.
- Nenhum uso em Signal Plane, Execution Plane, Ledger, Recovery, ML ou live
  e autorizado por esta task.
```

## Fora de escopo

```text
- Validacao final em novo OOS.
- SHORT-only, exclusao BTC/ETH, liquidez Q2 ou qualquer hipotese de
  TASK-PAYOFF-002.
- Funding price divergence.
- Order Flow/L2, Liquidation Dynamics, ML/meta-labeling.
- Paper/live trading.
```
