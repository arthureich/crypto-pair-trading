# TASK-CS-002 - Definicao e pre-registro: Cross-Sectional Mean Reversion (replicacao fiel de literatura, horizonte distinto de CS-001)

## Status

DONE (definicao). Aprovado explicitamente pelo usuario nesta sessao antes
de qualquer codigo ser escrito. Ver `project_control/DECISIONS.md`
ADR-0018.

## Workstream

Research Family E - Cross-Sectional Factors, segunda task (sequencial,
per ADR-0017). Executada apos o fechamento de `TASK-CS-001` (NAO PASSA
decisivo). CS-003 (Residual Momentum), CS-004 (PCA Statistical
Arbitrage), CS-005 (Ensemble) permanecem backlog planejado.

## Por que NAO reusar o horizonte semanal de CS-001 (fato matematico,
## nao escolha estetica)

Se esta task usasse o MESMO horizonte de formacao/holding de CS-001
(168h) e o MESMO ranking (retorno bruto de formacao), apenas invertendo
os lados (LONG nos perdedores, SHORT nos vencedores), o resultado liquido
OOS ja e determinado ANTES de qualquer novo backtest: o portfolio de
reversao no mesmo horizonte e o espelho exato do portfolio de momentum
(`gross_reversal = -gross_momentum`), e o custo e identico (mesmas
pernas, mesmo custo por perna). Usando os numeros reais de CS-001 (gross
OOS momentum = -64,61bps, custo OOS = 306,00bps):

```text
gross_reversal_mirror = -(-64,61) = +64,61bps
net_reversal_mirror   = 64,61 - 306,00 = -241,39bps  (negativo, certo)
```

Rodar esse espelho exato nao seria um teste novo -- seria reafirmar
CS-001 com o sinal trocado, sem informacao adicional. Por isso esta task
usa um horizonte GENUINAMENTE DISTINTO (24h), consistente com a propria
literatura classica: reversao de curto prazo e momentum de medio prazo
sao tratados como fenomenos em escalas de tempo DIFERENTES, nao o mesmo
sinal com o sinal trocado (ex.: Jegadeesh 1990 para reversao semanal em
equities, coexistindo com momentum de 3-12 meses -- aqui adaptado para
24h dado o dataset horario e o universo de cripto).

## Hipotese primaria (unica, decisoria)

```text
Cross-Sectional Mean Reversion, horizonte de 24h: retorno de formacao de
24h prediz NEGATIVAMENTE o retorno das proximas 24h -- comprar
perdedores, vender vencedores (sinal invertido em relacao a CS-001).
```

## Divulgacao explicita de proximidade com trabalho anterior (registrada
## ANTES de rodar qualquer backtest desta task)

Este projeto JA possui uma medida descritiva relacionada: TSREV Familia
B (`TASK-TSREV-002`, ADR-0014), horizonte 24h, full-sample (nao
OOS-split), reversao cross-sectional por DECIL (k=2, nao quintil k=4) de
Z-SCORE (retorno normalizado por volatilidade, nao retorno bruto).
Resultado ja conhecido e publicado em `tsrev_backtest_results.json`:
profit factor 0,87, net PnL -9.035,01bps (negativo).

Isso NAO e o mesmo teste (metrica de ranking diferente -- bruto vs
normalizado; K diferente -- 4 vs 2; amostra diferente -- OOS-only vs
full-sample), mas e proximo o suficiente para registrar honestamente que
esta task nao esta sendo escolhida "as cegas": ja existe uma evidencia
descritiva fraca na mesma direcao (reversao 24h nao lucrativa). Esta
divulgacao e feita ANTES do backtest de CS-002 rodar, para que o
resultado -- seja qual for -- possa ser lido corretamente a luz dessa
informacao previa, em vez de ser apresentado como uma surpresa nova.

## Regra de decisao (explicita, literal)

```text
Somente esta hipotese primaria (reversao cross-sectional, 24h, retorno
bruto) pode fundamentar a continuidade da linha Cross-Sectional Mean
Reversion.

Nenhum sweep de horizonte, de K, ou de convencao de peso e permitido
dentro desta task. Se o resultado nao passar o gate, per ADR-0017/a
recomendacao do usuario, a pesquisa baseada em fatores classicos de
preco (Research Family E) fecha, e a proxima fase abre numa categoria
NOVA (nao "Family F"): Market Microstructure / Alternative Data (open
interest, order flow, liquidacoes, funding como feature) -- fora do
escopo desta task, requer seu proprio pre-registro.
```

## Construcao do sinal (causal, retorno bruto -- mesma convencao de
## CS-001, diferente do z-score de TSREV)

```text
r_i,t(H) = log_price_i[t] - log_price_i[t-H]     (retorno de formacao,
                                                   causal, conhecido em t,
                                                   H=24h)
```

## Regra de trade

```text
A cada H=24h: ranquear os 20 symbols do universo por r_i,t(H).

LONG  nos K=4 de MENOR retorno de formacao (perdedores, quintil
      inferior) -- aposta em reversao para cima.
SHORT nos K=4 de MAIOR retorno de formacao (vencedores, quintil
      superior) -- aposta em reversao para baixo.

Sinal INVERTIDO em relacao a CS-001 (que e momentum: compra vencedores,
vende perdedores).

Holding: H=24h fixo, sem skip-period, sem trailing stop, sem barreira.
Book fechado e reaberto integralmente a cada 24h (full rebalance, mesmo
padrao de CS-001/TSREV Familia B/Funding Carry fase 1).
```

## Tamanho de posicao

```text
peso_i = 1 / (2*K) = 1/8 por posicao, fixo, equal-weight, dollar-neutro
         -- identico a CS-001.
```

## Custo

```text
cost_bps_roundtrip = 6.0 (mesma constante de CS-001/TSREV/Funding Carry).
```

## Divisao amostral (out-of-sample)

```text
Reusa EXATAMENTE a mesma fronteira ja pre-registrada em
TASK-TSREV-001/TASK-CS-001:

Desenvolvimento (in-sample, contexto apenas): 2023-06-01 a 2025-05-31
Teste decisivo (out-of-sample):               2025-06-01 a 2026-05-31
```

## Baseline do Max Drawdown

```text
Max drawdown de um portfolio buy-and-hold equal-weight dos mesmos 20
symbols, no MESMO periodo out-of-sample -- mesma funcao generica
(`buy_and_hold_max_drawdown_bps`) ja usada em CS-001/TSREV.
```

## Gate pre-registrado (todos simultaneos, avaliados so no OOS)

```text
net_profit_factor > 1.10   (mesmo piso de CS-001, por consistencia)
E net_pnl_bps > 0
E max_drawdown_bps <= max_drawdown_buy_and_hold_bps (no mesmo periodo OOS)
E resolved_trade_count (nivel de perna individual) >= 200
```

## Metodologia de validacao

```text
Split cronologico simples in-sample/out-of-sample (identico a
CS-001/TASK-TSREV-001) -- nao walk-forward, nao purged CV, pela mesma
justificativa de CS-001 (regra fixa, sem sweep de hiperparametro).
```

## Invariantes obrigatorios

```text
- r_i,t(H) usa apenas log_price conhecido ate t (causal, diff backward).
- Ranking cross-sectional em cada rebalanceamento usa apenas retorno de
  formacao conhecido naquele instante -- sem look-ahead.
- Posicao aberta no fim dos dados nunca e fabricada como fechada.
- Gate e calculado apenas no periodo out-of-sample.
```

## Fora de escopo

```text
- Sweep de horizonte (H diferente de 24h), de K, ou de convencao de peso.
- Normalizacao por volatilidade (isso seria replicar a TSREV Familia B
  de novo, nao uma hipotese nova).
- Walk-forward multi-fold ou purged CV.
- CS-003 (Residual Momentum), CS-004 (PCA Statistical Arbitrage), CS-005
  (Ensemble) -- backlog planejado, cada uma exige seu proprio
  pre-registro.
- Mudanca de universo (ex.: symbols de menor liquidez/menor
  capitalizacao) -- o usuario decidiu explicitamente NAO mudar o
  universo agora, para preservar comparabilidade com toda a pesquisa ja
  feita nesta sessao; universos alternativos ficam registrados como
  ideia futura, nao iniciada.
- Pivot para Market Microstructure/Alternative Data dentro desta task --
  so acontece DEPOIS do fechamento desta task, com seu proprio
  pre-registro, per a recomendacao do usuario.
- Novo download de dados.
- ML, XGBoost, meta-labeling.
- Promocao a paper/live com base em qualquer resultado desta task.
- Reinterpretar o gate apos ver o resultado.
```
