# TASK-ALT-012 - Definicao e pre-registro: estrategia de timing VRP (BTC/ETH), backtest dev + OOS

## Status

ACCEPTED (locked) - travado 2026-07-12 antes de qualquer implementacao. Sob
ADR-0032 (Familia F, Options). Primeira ESTRATEGIA da familia. Regra e params
FIXOS a priori; sem re-tune; sem promover secundario ex-post. Dev != promocao;
promocao so em OOS intocado (pos-2026-05-31), como todo o projeto.

## Motivacao

TASK-ALT-011 achou o 1o hit em dado externo: `vrp_z@7d` TEM_INFORMACAO (rho
+0,087, sign-consistent nos 3 subperiodos). O teste economico descritivo
mostrou spread bruto top-vs-bottom-decil ~197 bps/7d vs ~12 bps de custo. E um
LEAD -- mas o spread por decil NAO e uma estrategia: holds sobrepostos
amostrados diariamente superestimam; tail-driven; in-sample. Esta task testa se
o sinal SOBREVIVE como estrategia semanal real (rebalance nao-sobreposto, custo,
drawdown) e monta o veredito honesto.

## Hipotese economica (clara)

O premio de risco de variancia (VRP alto = medo/variancia cara precificada)
antecede retorno positivo (compensacao/rebote). Uma estrategia que fica LONG
BTC/ETH quando o VRP esta acima da media e SHORT/flat quando abaixo captura esse
premio, liquida de custo, com Sharpe/drawdown melhores que buy-and-hold.

## Metodologia

```text
Universo: BTC, ETH (unicos com DVOL liquido).
Sinal: vrp_z IDENTICO a ALT-011 -- VRP = (DVOL/100)^2 - RV_30d^2, z-score causal
  90d, shift(1). (teste de consistencia garante identidade com ALT-011.)
Regra de posicao (FROZEN, knob-free): por asset, posicao = sign(vrp_z)
  (LONG quando VRP acima da media movel, SHORT quando abaixo). Livro long/short
  unit-gross entre os 2 assets (cada perna ativa = 0,5 do gross).
Rebalance/hold: 7 DIAS (semanal, NAO-sobreposto -- casa com o horizonte
  validado; corrige o vies de amostragem sobreposta do teste economico).
Custo: 6 bps/perna (BTC/ETH liquidos; mesmo do TSM), sobre turnover.
Baseline: equal-weight BTC/ETH buy-and-hold (mesma grade semanal).
Metricas: Sharpe anualizado, max drawdown, net PnL, turnover, vs baseline.

Split dev/OOS:
  - DEV: 2023-06-01..2026-05-31 (janela do projeto) -> resultado de
    DESENVOLVIMENTO, sem veredito de promocao.
  - OOS GENUINO: pos-2026-05-31 (baixa DVOL de jun/2026 da API publica +
    barras jun/2026 ja em disco) -> contagem de rebalances OOS reais, como o
    TSM paper-forward. Curto (~4 semanas) -> MONITORAMENTO, nao veredito.
```

## Celula primaria (LOCKED, exatamente 1)

```text
Long/short sign(vrp_z), 2 assets, rebalance 7d, 6 bps/perna. Exatamente 1
variante primaria elegivel a OOS. Secundaria DESCRITIVA (nao decisional):
long-only (long high-VRP, flat low-VRP) -- reportada, nunca promovida.
Sem grade de thresholds/holds/custos escolhida por desempenho.
```

## Bateria de robustez (TODAS; padrao TSM/ADR-0031)

```text
1. Estabilidade nos 3 subperiodos.
2. Sensibilidade a custo (grade; breakeven).
3. Regimes de mercado (BTC up vs down).
4. Drawdown vs buy-and-hold.
5. Simplicidade vs ganho.
6. Justificativa economica (VRP -> retorno, coerente, nao ex-post).
7. Falso-positivo: ganho CONSISTENTE nos subperiodos; concentrado em 1 = alerta.
Nota de funding: posicoes SHORT de perp de 7d pagam/recebem funding; o backtest
usa retorno de preco (o custo de funding e uma ressalva qualitativa registrada,
nao no P&L primario -- follow-up se a estrategia sobreviver).
```

## Criterio de decisao

```text
CANDIDATO A OOS somente se (no DEV): Sharpe > buy-and-hold E net PnL > 0 E maxDD
<= buy-and-hold E ganho CONSISTENTE nos 3 subperiodos. Caso contrario:
REJEITADO, documentado, e o VRP fica como feature-candidata (nao estrategia
standalone). Nenhuma promocao no dev; gate BLOQUEADO ate OOS genuino acumular
(trilha forward, como TSM/funding). so pesquisa/paper, nada real.
```

## Invariantes / Fora de escopo

```text
- Regra/params fixos a priori; sem re-tune; sem secundario ex-post promovido.
- Sinal causal (vrp_z = ALT-011, shift(1)); target = unico dado posterior.
- Dev != promocao; OOS-gated.
- FORA: VRP-harvesting / venda de variancia (Angle A, livro de opcoes -- decisao
  do usuario); skew/superficie; grade de otimizacao; alavancagem; acao real.
```
