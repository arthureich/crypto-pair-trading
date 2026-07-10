# TASK-FC-II-001 - Definicao e pre-registro: Position Sizing por Risco (inverse-vol + vol-targeting) como OVERLAY sobre o Funding Carry K=5

## Status

ACCEPTED (locked) - travado em 2026-07-10, antes de qualquer codigo. Ver
`project_control/DECISIONS.md` ADR-0027 (fase "Funding Iteration 2"). Fase
de DESENVOLVIMENTO autorizada agora (computar no dev set + paper-forward).
O GATE de PROMOTE/NAO_PROMOVE permanece BLOQUEADO ate OOS genuinamente
novo/nao-visto (>=500 rebalances resolvidos apos 2026-05-31, preferindo
track forward acumulado a uma unica janela).

## Workstream

Funding Iteration 2 (FC-II), primeira melhoria. Objetivo: melhorar o
retorno AJUSTADO A RISCO do funding carry K=5 sem alterar a hipotese
fundamental (comprar funding barato / vender funding caro) nem o sinal.

## Por que sizing e a PRIMEIRA melhoria (menor risco de overfit)

Position sizing por risco NAO e uma nova alegacao de alpha -- e gestao de
risco. Nao preve nada, nao seleciona pernas, nao usa a magnitude do
funding para apostar mais. Por isso tem a menor superficie de overfit
entre as ideias da FC-II, e e onde comeca (ADR-0027).

## Nota de escopo HONESTA (o que sizing faz e o que NAO faz)

```text
Escalar o livro inteiro por um alvo de volatilidade e INVARIANTE em
profit factor (PF e uma razao lucro-bruto/perda-bruta, invariante a
escala uniforme). Portanto esta task NAO mira "elevar PF para 1,20" --
mira metricas AJUSTADAS A RISCO: Sharpe e max drawdown. A parte que pode
mexer no PF e so a re-ponderacao inverse-vol DENTRO de cada lado (reordena
o peso relativo das pernas); o vol-targeting global mexe em Sharpe/DD, nao
em PF. Qualquer expectativa de "pump" de PG por sizing e incorreta e fica
registrada como tal.
```

## Metodo (LOCKED, uma unica especificacao -- sem varredura de parametros)

```text
Overlay sobre o K=5 INALTERADO (mesmas pernas long/short que o sinal ja
escolhe a cada rebalanceamento). Dois passos, ambos causais:

1. INVERSE-VOL WEIGHTING dentro de cada lado:
   - vol_leg[t] = desvio-padrao causal do retorno horario do symbol,
     shift(1).rolling(VOL_LOOKBACK_HOURS) -- mesma convencao causal ja
     usada em realized_vol de TASK-ALT-003/ML-001.
   - peso bruto da perna = 1 / vol_leg[t] (pernas mais calmas pesam mais).
   - renormalizar por lado para que CADA lado some 50% do notional
     (neutralidade dolar preservada, identico ao 1/(2K) quando as vols
     sao iguais).
   - se vol_leg indefinido (warm-up) ou <=0, a perna cai para peso
     igual dentro do lado naquele intervalo (fail-safe, nao fabrica).

2. VOL-TARGETING do livro inteiro:
   - vol_book[t] = desvio-padrao causal do retorno por-intervalo do livro
     equal-weight, shift(1).rolling(VOL_TARGET_WINDOW_HOURS).
   - alvo = a PROPRIA vol historica do livro equal-weight na mesma janela
     (auto-referente -> escala media ~1; NAO ha knob de alavancagem
     externo). scale[t] = alvo / vol_book[t], limitado a [SCALE_MIN,
     SCALE_MAX] para nao explodir em regimes de vol quase-zero.
   - o PnL do intervalo e multiplicado por scale[t].

Parametros FIXOS (declarados aqui, nao varridos apos ver resultado):
  VOL_LOOKBACK_HOURS      = 168   (1 semana)
  VOL_TARGET_WINDOW_HOURS = 2160  (90 dias, mesma janela causal do projeto)
  SCALE_MIN, SCALE_MAX    = 0,5 e 2,0  (trava anti-explosao, nao um knob
                                        de tuning -- fixado por seguranca)
```

## Kelly fica de fora (deliberado)

```text
Kelly (fracionado ou nao) exige uma ESTIMATIVA DE EDGE. O edge deste sinal
nao esta validado (1,0904 e sub-gate e pode ser ruido). Dimensionar por um
edge nao-validado e a receita classica de ruina. Kelly fica FORA desta
task; se algum dia o edge for confirmado em OOS, Kelly fracionado pode ser
uma task FC-II separada, pre-registrada.
```

## Criterios de sucesso (pre-registrados, no OOS novo/nao-visto)

```text
PROMOTE somente se, no track forward/OOS (>=500 rebalances resolvidos apos
2026-05-31), a estrategia com sizing:
  (a) Sharpe LIQUIDO >= Sharpe do baseline equal-weight K=5 no MESMO
      periodo + margem pre-registrada (>= +0,15 de Sharpe absoluto), E
  (b) max drawdown NAO maior que o do baseline no mesmo periodo, E
  (c) atua em >= 500 rebalances (nao vence reduzindo exposicao a ~zero).
PF nao e criterio aqui (invariante a escala; ver nota de escopo).
Qualquer criterio que falhe => NAO_PROMOVE, sem re-tuning de parametro.
```

## Invariantes obrigatorios

```text
- Sinal primario, selecao de pernas e modelo de custo do K=5: INALTERADOS.
  Sizing e um overlay separado (como o filtro de meta-labeling).
- Toda vol e causal: shift(1) antes de qualquer rolling.
- Especificacao unica e parametros congelados ANTES de qualquer computo.
  Esta task valida EXATAMENTE uma spec de sizing -- nada de varrer
  VOL_LOOKBACK/target e promover o melhor (regra 2 do ADR-0027).
- Fail-safe (nao fail-open): vol indefinida/<=0 -> peso igual no lado;
  vol_book ~0 -> scale limitado por SCALE_MIN/MAX. Nunca fabrica peso.
- Desenvolvimento no dev set NAO gera veredito. Gate bloqueado ate OOS.
```

## Fora de escopo

```text
- Sizing pela magnitude do funding (seria aposta de alpha, nao risco).
- Kelly / expected-Sharpe sizing (exige edge estimado; ver acima).
- Alavancagem alem do vol-target auto-referente.
- Alterar K, o sinal, a selecao ou o custo.
- As demais familias FC-II (regime, ranking ML, ensemble, RL, online):
  cada uma e task separada e pre-registrada, e varias estao demovidas por
  evidencia contraria ja existente (ADR-0027).
- Varredura de parametros de sizing para "melhorar" o numero no dev set.
```
