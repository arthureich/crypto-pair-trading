# TASK-ALT-006 - Definicao e pre-registro: TSREV restrito a regime de alta volatilidade (feasibility), execucao bloqueada aguardando novo OOS

## Status

DEFINIDO, EXECUCAO BLOQUEADA aguardando dados novos. Aprovado
explicitamente pelo usuario nesta sessao antes de qualquer codigo ser
escrito. Ver `project_control/DECISIONS.md` ADR-0024.

## Workstream

Research Phase II - Alternative Information, follow-up de Familia J
(Regime Detection). Segunda task de uso operacional da informacao de
regime, apos `TASK-ALT-004` (bloqueio binario de alta-vol) fechar
NAO_PASSA.

## Por que a execucao esta bloqueada (risco de data-mining explicito,
## nao bloqueio de disponibilidade de dado)

`TASK-ALT-004` testou bloquear entradas da TSREV Familia A 24h quando
`realized_vol_168h[t]` estava ACIMA do percentil causal 67% da propria
historia de 90 dias do symbol -- hipotese de que alta volatilidade
significa risco a evitar. Resultado real, no periodo OOS ja analisado
(2025-06/2026-05): o filtro **piorou** a economia (net PF 1,0143 ->
0,9822; net PnL +7.690,14 -> -6.110,64bps).

Decompondo esse resultado: as 1.187 trades EXCLUIDAS (alta-vol) tinham
net **+13.800,78bps** por conta propria -- mais que o lucro total
original da estrategia. As 2.758 trades MANTIDAS (baixa/media vol) sao
net **-6.110,64bps** isoladamente. O edge da TSREV esta inteiramente
concentrado no regime de alta volatilidade; fora dele, a estrategia
perde dinheiro.

Isso motiva a hipotese oposta: manter APENAS as entradas de alta-vol
(em vez de excluir). Mas essa hipotese foi construida DIRETAMENTE a
partir de ter visto o resultado de `TASK-ALT-004` no periodo
2025-06/2026-05 -- e um caso mais direto de risco de data-mining que
qualquer outro desta sessao (SHORT-only do Payoff Engineering,
`funding_price_divergence`). Testar "manter so alta-vol" no MESMO
periodo que revelou o padrao nao teria valor probatorio -- confirmaria
um padrao no mesmo dado que o gerou, nao uma hipotese independente.

Por isso, per decisao explicita do usuario, esta task e pre-registrada
AGORA (trava o desenho antes de qualquer dado novo) mas so pode ser
executada com dado genuinamente novo -- mesma disciplina de
`TASK-PAYOFF-002`.

## Hipotese primaria (unica, decisoria)

```text
TSREV Familia A 24h, restrita a entradas onde realized_vol_168h[t] esta
ACIMA do percentil causal 67% da propria historia de 90 dias do symbol
-- o filtro EXATAMENTE INVERSO de TASK-ALT-004 (mesma feature, mesmo
percentil, mesma janela causal), mudando apenas a direcao do corte.
```

## Feature de regime (identica a TASK-ALT-003/004, nao redesenhada)

```text
realized_vol_168h[t] = std causal dos retornos horarios log_price nas
                        ultimas 168h (shift(1) antes do rolling).
percentil_67[t] = percentil causal 67% de realized_vol_168h dentro da
                  propria janela de 90 dias (2160h) do symbol,
                  shift(1) antes do rolling.
allow_entry[t] = realized_vol_168h[t] > percentil_67[t]
                 (inverso exato de TASK-ALT-004, que usava <=)
```

Entradas sem regime calculavel (warmup insuficiente) falham fechadas --
`allow_entry=False`, mesma convencao de `TASK-ALT-004`.

## Regra de trade (identica a TSREV Familia A 24h / TASK-ALT-004, exceto
## a direcao do filtro)

```text
Mesmo sinal z=r/sigma, mesmo horizonte 24h, mesmo custo 6,0bps, mesma
renormalizacao inverse-vol apos o filtro (para nao "passar" apenas por
reduzir exposicao total -- mesma convencao de TASK-ALT-004).
```

## Divisao amostral (out-of-sample genuinamente novo)

```text
Contexto (nao decisorio): todo o periodo ja usado em TASK-TSREV-001/
                          TASK-ALT-004 (2023-06-01 a 2026-05-31) --
                          e exatamente o periodo que gerou esta
                          hipotese, NUNCA usado para decidir.
Teste decisivo (out-of-sample NOVO): 2026-06-01 em diante, meses
                          completos apenas -- mesma disciplina de
                          TASK-ALT-005/TASK-PAYOFF-002.
```

## Gatilho operacional de retomada (nao e criterio de gate)

```text
Nao iniciar a execucao antes que o periodo 2026-06-01 em diante
contenha >= 750 trades TOTAIS resolvidas da configuracao TSREV
primaria (Family A 24h, todos os niveis de vol, antes do filtro).

Estimativa: no periodo original, trades de alta-vol (per este filtro)
eram ~30,08% do total (1.187/3.946). Com ~750 trades totais, espera-se
~226 trades de alta-vol -- margem sobre o piso de 200 do gate abaixo,
dado que a proporcao real no periodo novo pode divergir da historica.
Ao ritmo historico (~328 trades/mes agregados), isto equivale a
aproximadamente 2,3 meses de dado novo (por volta de 2026-08).

TASK-ALT-005 (2026-07-07) ja baixou e normalizou o mes completo de
2026-06 (`sprint_alt_funding_divergence_202606_bars.csv.gz`, klines/
markPrice/indexPrice/premiumIndex/funding, 20 symbols, checksum
verificado) -- esse mes pode ser reusado sem novo download quando a
janela crescer; meses adicionais completos precisarao ser baixados via
o mesmo pipeline (`historical_dataset.py`) conforme completarem.
```

## Gate pre-registrado (todos simultaneos, avaliados so no novo OOS)

```text
net_profit_factor > 1.05      (mesmo piso da TASK-TSREV-001, reusado)
E net_pnl_bps > 0
E max_drawdown_bps <= max_drawdown_buy_and_hold_bps (recalculado no
  novo periodo, nunca reusando o baseline antigo)
E resolved_trade_count (apos o filtro allow_entry) >= 200
```

## Regra de decisao (explicita, literal)

```text
Este e um teste de FEASIBILITY, nao uma promocao a estrategia. Mesmo
um PASSA nao autoriza SignalIntent, paper/live, sizing dinamico
adicional, Execution, Ledger, Recovery, ML, ou qualquer acao de ordem
-- apenas permite abrir uma futura task de desenho operacional, com seu
proprio pre-registro.

Se o resultado for NAO_PASSA, esta linha de "concentrar em alta-vol"
fecha -- nenhum ajuste de percentil (67% -> outro valor) ou de janela
(168h -> outra) sera testado apos ver o resultado.
```

## Invariantes obrigatorios

```text
- realized_vol_168h e o percentil causal usam shift(1) antes de
  qualquer rolling -- identico a TASK-ALT-003/004.
- Nenhuma linha anterior a 2026-06-01 entra no resultado decisorio.
- Baseline de drawdown recalculado no novo periodo.
- Gate calculado uma unica vez, no primeiro periodo que atingir o
  gatilho operacional -- nao existe re-checagem incremental mes a mes
  tentando "acertar" o gate.
```

## Fora de escopo

```text
- Rodar esta task antes do gatilho de retomada (>=750 trades totais
  novos) ser atingido.
- Qualquer ajuste de percentil, janela de vol, ou horizonte apos ver
  o resultado.
- Sizing continuo por vol (ideia relacionada, mas e uma hipotese
  distinta -- exigiria seu proprio pre-registro, nao esta task).
- SHORT-only ou qualquer combinacao com a pista de TASK-PAYOFF-002
  (permanece bloqueada separadamente, seu proprio gatilho).
- Order Flow/L2, Liquidation Dynamics.
- ML, XGBoost, meta-labeling.
- Promocao a paper/live com base em qualquer resultado desta task.
```
