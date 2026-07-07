# TASK-PAYOFF-002 - Definicao e pre-registro: Payoff Engineering Fase 2 (validacao das hipoteses da Fase 1 em novo out-of-sample)

## Status

DEFINIDO, EXECUCAO PAUSADA aguardando dados. Aprovado explicitamente pelo
usuario nesta sessao antes de qualquer codigo ser escrito. Ver
`project_control/DECISIONS.md` ADR-0016.

## Workstream

Research Family D - Payoff Engineering, Fase 2. Continuacao direta da
Fase 1 (`TASK-PAYOFF-001`, `reports/tsrev_payoff_attribution.md`), que
encontrou 4 padroes descritivos nas trades out-of-sample da celula
primaria TSREV (Familia A, 24h): assimetria SHORT>>LONG, symbols
BTCUSDT/ETHUSDT piores, clustering temporal por mes, e um padrao
nao-monotonico de liquidez com o quartil intermediario (Q2) melhor que
os extremos.

## Por que a execucao esta pausada (bloqueio de dados, nao de decisao)

O dataset normalizado (`sprint7_binance_usdm_202306_202605_bars.csv.gz`)
termina em **2026-05-31**. O periodo out-of-sample da TASK-TSREV-001
(2025-06-01 a 2026-05-31) e exatamente onde os 4 padroes da Fase 1 foram
observados. Testar qualquer hipotese derivada desses padroes NESSE MESMO
periodo seria re-minerar os dados que geraram a hipotese -- nao uma
confirmacao valida (contaminacao amostral, nao vazamento temporal). Um
periodo out-of-sample genuinamente novo (dados a partir de 2026-06-01,
nunca usados em nenhuma decisao deste projeto) ainda nao existe. O
usuario decidiu explicitamente AGUARDAR acumulacao real de dados novos em
vez de (a) baixar dados ja disponiveis agora (amostra pequena, ~350-400
trades estimados em ~5 semanas) ou (b) usar um holdout interno do OOS ja
usado (metodologicamente mais fraco, contaminacao parcial).

## Gatilho de retomada (operacional, nao e criterio de gate)

```text
Nao iniciar a execucao desta task antes que o periodo 2026-06-01 em
diante contenha >= 500 trades resolvidos da configuracao EXATA da celula
primaria TSREV (TimeSeriesReversalConfig(horizon_hours=24), todos os
lados, todos os 20 simbolos) no novo dado real normalizado.

Estimativa: ao ritmo historico (~328 trades/mes agregados nos 20
simbolos), isto equivale a aproximadamente 1,5 meses de dado novo real
(meados de julho/2026 em diante). Esta e uma margem de seguranca sobre o
piso de 200 trades da celula primaria SHORT-only abaixo (ver Gate), dado
que o lado SHORT historicamente e ~46% do total (1.824/3.941 na Fase 1) --
500 trades totais tendem a produzir ~230 trades SHORT, ja acima do piso
de 200. Se a proporcao real observada no novo periodo divergir e o piso
de 200 SHORT nao for atingido com 500 trades totais, a execucao continua
aguardando (o piso do Gate abaixo e o criterio que efetivamente bloqueia,
nao o gatilho operacional de 500).
```

Este gatilho e apenas operacional (quando comecar a rodar) -- nao e o
criterio de aprovacao da hipotese, que esta definido no Gate abaixo.

## Hipotese primaria (unica, decisoria)

```text
SHORT-only: restringir a celula primaria TSREV (Familia A, 24h) para
tomar APENAS entradas SHORT (z_i,t > +1,0). Nenhuma entrada LONG e
avaliada nesta celula.
```

### Justificativa da escolha (registrada ANTES de ver qualquer dado novo)

Escolhida pelo prior da Fase 1, nao por um backtest de SHORT-only ja
rodado:

```text
- maior efeito absoluto entre os 4 padroes da Fase 1: SHORT
  net +37.938,31bps (WR 55,2%) vs LONG -30.248,16bps (WR 50,5%) sobre
  3.941 trades -- diferenca de ~68.000bps entre os lados do mesmo sinal.
- replica de forma INDEPENDENTE o mesmo achado do diagnostico
  cross-sectional Z-score anterior nesta sessao (fade de picos de alta
  mais consistente que aposta em repique apos queda) -- dois diagnosticos
  distintos, dados/janelas distintos, mesma direcao.
- e a hipotese mais simples e mais diretamente redutivel a uma regra de
  filtro (nao requer nova classificacao de regime nem novo dado).
```

Nenhum backtest de estrategia SHORT-only foi rodado antes desta escolha.

## Regra de decisao (explicita, literal)

```text
Somente a hipotese primaria (SHORT-only, celula TSREV Familia A 24h) pode
fundamentar a continuidade desta linha de pesquisa.

As 3 hipoteses secundarias abaixo sao exclusivamente descritivas e
exploratorias. Mesmo que uma delas performe melhor que a SHORT-only no
novo periodo, isso NAO substitui a decisao da hipotese primaria -- pode
apenas motivar um TASK-PAYOFF-003 futuro, com seu proprio pre-registro e
seu proprio periodo de dados novos.

Nenhuma celula (primaria ou secundaria) autoriza promocao a paper
trading, live trading, ou nova linha principal de desenvolvimento.
```

## Hipoteses secundarias (descritivas, nao-decisorias)

Todas rodadas sobre o MESMO novo periodo out-of-sample da primaria (nunca
sobre o periodo antigo 2025-06/2026-05, que so serve de contexto).

```text
D2 - Exclusao BTC/ETH: celula TSREV Familia A 24h completa (LONG+SHORT),
     excluindo os symbols BTCUSDT e ETHUSDT (18 symbols restantes).

D3 - Regime temporal: classificar cada barra causalmente pelo sinal do
     retorno equal-weight trailing de 30 dias (720h) do universo de 20
     symbols, defasado 1 barra (shift(1), sem look-ahead): regime
     "ALTA" se retorno trailing > 0, "BAIXA" caso contrario. Reportar
     performance da celula primaria completa (LONG+SHORT) separada por
     regime. Definicao fixada AGORA, antes de ver qualquer dado novo --
     nenhum outro criterio de regime (volatilidade, drawdown, etc.) sera
     testado sem novo pre-registro.

D4 - Liquidez intermediaria: celula TSREV Familia A 24h completa
     (LONG+SHORT), restrita a entradas cujo quote_volume na barra de
     entrada caia no quartil Q2 (calculado sobre a distribuicao do
     proprio novo periodo, mesma metodologia de corte em quartis da
     Fase 1).
```

## Construcao do sinal e regras de trade (identicas a TASK-TSREV-001)

```text
Mesma formula causal de z-score e sigma_H (shift(1) antes do rolling),
mesmo horizonte fixo de saida (24h), mesmo peso inverso-a-sigma
normalizado, mesmo custo (6,0bps roundtrip). NENHUM parametro do sinal ou
de custo muda nesta fase -- apenas o FILTRO de quais trades entram em
cada celula (lado, symbol, regime, liquidez).
```

## Divisao amostral (out-of-sample genuinamente novo)

```text
Contexto (nao decisorio): todo o periodo ja usado em TASK-TSREV-001
                          (2023-06-01 a 2026-05-31).
Teste decisivo (out-of-sample NOVO): 2026-06-01 em diante, ate a data em
                          que os dados novos forem baixados para esta
                          task -- nunca usado em nenhuma decisao anterior
                          deste projeto.
```

## Baseline do Max Drawdown

```text
Max drawdown de um portfolio buy-and-hold equal-weight dos mesmos 20
simbolos, recalculado no NOVO periodo out-of-sample (nao reusar o valor
de 11.003,94bps da TASK-TSREV-001, que era do periodo antigo).
```

## Gate pre-registrado (todos simultaneos, avaliados so no OOS novo, so
## na hipotese primaria SHORT-only)

```text
net_profit_factor > 1.05
E net_pnl_bps > 0
E max_drawdown_bps <= max_drawdown_buy_and_hold_bps (no mesmo periodo OOS novo)
E resolved_trade_count (SHORT) >= 200
```

Mesma estrutura de gate da TASK-TSREV-001 (net PF>1,05, net PnL>0, DD<=
baseline, trade_count>=200) -- nao inventado nem ajustado para esta
celula. O piso de 200 aplica-se ao numero de trades SHORT resolvidos, nao
ao total combinado.

## Invariantes obrigatorios

```text
- Nenhum download de dados alem do estritamente necessario para estender
  o dataset normalizado existente de 2026-06-01 em diante (mesmo processo
  ja usado no ADR-0007/Sprint 7, sem novo escopo de simbolos).
- sigma usado na decisao em t nunca inclui a barra t (shift(1)).
- Regime (D3) usa apenas retorno trailing conhecido ANTES da barra de
  decisao (shift(1) antes do rolling de 720h) -- sem look-ahead.
- Gate da hipotese primaria (SHORT-only) e calculado ANTES de olhar
  qualquer celula secundaria -- as secundarias sao reportadas depois, sem
  influenciar a decisao.
- Baseline de drawdown e recalculado no periodo novo, nunca reusa o
  numero do periodo antigo.
```

## Fora de escopo

```text
- Rodar esta task antes do gatilho de retomada (>=500 trades novos
  resolvidos) ser atingido.
- Sweep de limiar de z, horizonte de saida, ou definicao de regime dentro
  desta task.
- Qualquer novo criterio de filtro (ex.: outro corte de liquidez, outro
  subconjunto de symbols) alem dos 4 ja fixados aqui.
- Trailing stop, barreira tripla, position sizing dinamico, volatility
  targeting -- isso continua sendo trabalho de uma Fase 3 nao aberta.
- Order-flow/L2 microstructure -- linha de pesquisa separada, nao
  iniciada.
- ML, XGBoost, meta-labeling.
- Promocao a paper/live com base em qualquer celula, primaria ou
  secundaria.
- Reinterpretar o gate apos ver o resultado (ex.: trocar o piso de 1,05,
  o piso de 200 trades SHORT, ou a definicao de regime de D3).
```
