# TASK-TSREV-001 - Definicao e pre-registro: Reversao Time-Series e Cross-Sectional

## Status

DONE (definicao). Aprovado explicitamente pelo usuario nesta sessao antes
de qualquer codigo ser escrito. Ver `project_control/DECISIONS.md`
ADR-0014.

## Workstream

Research Family C - TSREV (Time-Series/Cross-Sectional Reversal).
Nao herda metricas nem conclusoes de Signal Iteration 1 (ADR-0010) nem de
Funding Carry (ADR-0013).

## Hipotese primaria (unica, decisoria)

```text
Familia: A - Time-Series Reversal
Horizonte: 24h
```

### Justificativa da escolha (registrada ANTES da implementacao)

O diagnostico exploratorio ja realizado nesta sessao
(`reports/tsmom_diagnostic.md`) encontrou, para a mesma familia (retorno
proprio do ativo prevendo retorno futuro do proprio ativo, horizonte
casado):

```text
- correlacao negativa em TODAS as 4 janelas testadas (4h,8h,12h,24h)
- magnitude mais forte em 24h (-0,031, a mais negativa das 4)
- sign persistence sistematicamente <50%, caindo ainda mais no decil
  mais extremo (44,2% em 24h)
- 20 de 20 simbolos concordando individualmente (unanime)
```

24h foi escolhido por ter o prior empirico mais forte e mais consistente
entre as opcoes -- nao porque um backtest completo de TSREV 24h especifico
ja foi rodado e pareceu lucrativo. Nenhum backtest de estrategia (entrada/
saida/custo) foi rodado antes desta escolha.

## Regra de decisao (explicita, literal)

```text
Somente a hipotese primaria (Time-Series Reversal, 24h) pode fundamentar
a continuidade desta linha de pesquisa.

Resultados das hipoteses secundarias serao tratados exclusivamente como
evidencia exploratoria e poderao servir apenas para formular futuros
pre-registros independentes, nunca para validar esta pesquisa -- mesmo
que uma celula secundaria performe melhor que a primaria.

Nenhuma celula (primaria ou secundaria) autoriza promocao a paper
trading, live trading, ou nova linha principal de desenvolvimento.
```

## Hipoteses secundarias (descritivas, nao-decisorias)

```text
Familia A (Time-Series Reversal): 6h, 12h, 48h
Familia B (Cross-Sectional Reversal, mesmo sinal z, corte por decil,
           dollar-neutral, full-rebalance a cada intervalo): 6h, 12h,
           24h, 48h
```

## Construcao do sinal (identica para A e B, causal)

```text
r_i,t(H) = log_price_i[t] - log_price_i[t-H]           (retorno causal)
hourly_ret_i = log_price_i.diff(1)
sigma_hourly_i[t] = hourly_ret_i.shift(1).rolling(720).std()   (30 dias,
                     EXCLUINDO o retorno horario da propria barra t)
sigma_H_i[t] = sigma_hourly_i[t] * sqrt(H)
z_i,t = r_i,t(H) / sigma_H_i[t]
```

`shift(1)` na volatilidade garante que o sigma usado na decisao em t nao
inclui a barra t -- mesma disciplina causal ja aplicada ao ATR do TSMOM.

## Familia A (Time-Series Reversal) - regra de trade

```text
Por simbolo, uma posicao por vez:

Entrada LONG  se z_i,t < -1,0
Entrada SHORT se z_i,t > +1,0
(limiar unico, sem sweep)

Saida: horizonte fixo H (igual a janela de formacao), sem trailing stop,
sem barreira tripla -- a saida ocorre exatamente H horas depois da
entrada, incondicionalmente.

Posicao ainda aberta no fim dos dados = OPEN_AT_END, excluida das
metricas resolvidas (nao fabrica preco de saida).
```

## Familia B (Cross-Sectional Reversal) - regra de trade

```text
A cada intervalo de H horas: ranquear os 20 simbolos por z_i,t
(mesmo sinal). LONG nos 2 de menor z (piores, decil 10%), SHORT nos 2 de
maior z (melhores, decil 10%) -- k=2, decil literal com 20 simbolos.
Dollar-neutro, peso igual, book fechado e reaberto a cada intervalo
(mesmo padrao "full rebalance" da fase 1 do funding carry -- mais simples,
condiz com "nada sofisticado" pedido pelo usuario).
```

## Tamanho de posicao (Familia A)

```text
peso_i = (1 / sigma_H_i na entrada) normalizado para media 1,0 entre
         todos os trades resolvidos -- mesma convencao inversa-a-vol ja
         usada e revisada no TSMOM.
```

## Custo

```text
cost_bps_roundtrip = 6.0 (constante conservadora mais usada neste
                          projeto -- Sprint 8 canonico, funding carry --
                          nao os 12,0bps taker-taker do TSMOM, pois uma
                          entrada de reversao a media e plausivelmente
                          makeable, diferente de um breakout).
```

## Divisao amostral (out-of-sample)

```text
Desenvolvimento (in-sample, contexto apenas): 2023-06-01 a 2025-05-31
Teste decisivo (out-of-sample):               2025-06-01 a 2026-05-31

O gate e decidido SOMENTE no periodo out-of-sample. O periodo
in-sample e reportado para contexto/robustez, nunca para decidir.
```

## Baseline do Max Drawdown

```text
Max drawdown de um portfolio buy-and-hold equal-weight dos mesmos 20
simbolos, no MESMO periodo out-of-sample -- "a estrategia precisa
arriscar menos que simplesmente ficar comprado no mercado."
```

## Gate pre-registrado (todos simultaneos, avaliados so no OOS, so na
## hipotese primaria)

```text
net_profit_factor > 1.05
E net_pnl_bps > 0
E max_drawdown_bps <= max_drawdown_buy_and_hold_bps (no mesmo periodo OOS)
E resolved_trade_count >= 200
```

## Invariantes obrigatorios

```text
- sigma usado na decisao em t nunca inclui a barra t (shift(1)).
- r_i,t(H) usa apenas log_price conhecido até t (causal por construcao,
  diff backward).
- Familia B: ranking cross-sectional em cada intervalo usa apenas z
  conhecido naquele instante -- sem look-ahead.
- Posicao aberta no fim dos dados nunca e fabricada como fechada.
- Gate da hipotese primaria e calculado ANTES de olhar qualquer celula
  secundaria -- as secundarias sao reportadas depois, sem influenciar a
  decisao.
```

## Fora de escopo

```text
- Sweep de limiar de z, de horizonte de saida, ou de decil dentro da
  hipotese primaria.
- Trailing stop, barreira tripla, ou qualquer saida dinamica na Familia A.
- ML, XGBoost, meta-labeling.
- Novo download de dados.
- Promocao a paper/live com base em qualquer celula, primaria ou
  secundaria.
- Reinterpretar o gate apos ver o resultado (ex.: trocar o piso de 1,05
  por outro valor, ou o piso de 200 trades).
```
