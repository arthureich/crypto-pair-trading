# TASK-FC-II-008 - Definicao e pre-registro: TSM vol-targeted COM funding P&L dos perpetuos

## Status

ACCEPTED (locked) - travado 2026-07-11 antes de qualquer resultado. Sob
ADR-0027. Fecha a lacuna honesta do FC-II-005/007: o backtest do TSM usava
SO retorno de preco, mas e um livro de PERPETUOS segurado 5 dias, que incorre
funding P&L (~15 settlements/hold) nao modelado. In-sample, descritivo,
sem veredito.

## Motivacao

O TSM vol-targeted sobreviveu a todo stress in-sample (subperiodo/perna/
regime/custo). Antes de qualquer OOS, o P&L precisa incluir funding: um perp
long paga funding quando funding>0 (custo tipico); um short recebe. Para um
livro L/S isso pode AJUDAR (as shorts coletam funding no regime tipico de
funding positivo) ou atrapalhar -- mas tem que ser medido, nao assumido.

## Metodologia (adiciona funding ao FC-II-005; params do sinal INALTERADOS)

```text
Reusa run_tsm_trend_backtest com os params LOCKED do FC-II-005 (28d/7d/5d),
adicionando a componente de funding P&L (flag include_funding):

Convencao de sinal (a MESMA de funding_carry.leg_pnl_fracs): P&L de funding
de uma posicao de peso SINALIZADO w, por settlement, = -w * funding_rate
(long w>0 paga quando funding>0; short w<0 recebe). Verificado por revisao
adversarial (HANDOFFS).

Funding sobre o hold [t, t+hold): soma dos rates por settlement no intervalo.
Computado de forma causal-consistente como o retorno forward: funding horario
= funding_rate_asof / funding_interval_hours (espalha o rate de 8h pelas suas
8 horas); funding_over_hold = soma horaria acumulada entre rebalances
consecutivos (cumsum diferenciado nas linhas de rebalance) -- identico em
estrutura ao forward_return, e parte do P&L REALIZADO do hold (nao look-ahead).

P&L de funding por perna = -w_i * funding_over_hold_i; somado ao gross e
alocado a perna long/short conforme o sinal de w (sleeves seguem somando ao
gross). Custo/turnover inalterados.

Re-roda: (1) metricas de dev (Sharpe/maxDD/net) com funding on vs off; (2) o
stress de custo (breakeven) com funding on.
```

## Criterio (descritivo -- decide se o lead segue vivo)

```text
- SOBREVIVE: com funding incluido, Sharpe ainda > baseline E net PnL > 0 E
  o breakeven de custo continua acima da banda realista (10-15 bps/leg).
- ENFRAQUECE mas vive: Sharpe cai mas segue > baseline a custo realista.
- MORRE: funding vira o P&L negativo ou o breakeven cai abaixo do custo
  realista -> o lead nao sobrevive ao custo de carregar os perps.
Sem veredito de promocao; so a decisao de seguir para OOS ou nao.
```

## Invariantes

```text
- Params do SINAL do TSM LOCKED (so adiciona funding P&L). include_funding
  default False preserva o comportamento do FC-II-005 (testado por igualdade).
- Convencao de funding reusa leg_pnl_fracs (fonte unica); nada reimplementado.
- funding_over_hold e o P&L realizado do hold (forward), analogo ao
  forward_return -- nao introduz look-ahead.
- In-sample, descritivo; sem gate de promocao; sem acao real.
```

## Fora de escopo

```text
- Ajustar params do TSM em resposta ao funding (curve-fit).
- Borrow/impacto de mercado/slippage por tamanho (refinamentos posteriores).
- OOS/estrategia/promocao (task separada se sobreviver).
```
