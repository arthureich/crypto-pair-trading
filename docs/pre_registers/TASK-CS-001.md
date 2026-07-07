# TASK-CS-001 - Definicao e pre-registro: Cross-Sectional Momentum (replicacao fiel de literatura cripto)

## Status

DONE (definicao). Aprovado explicitamente pelo usuario nesta sessao antes
de qualquer codigo ser escrito. Ver `project_control/DECISIONS.md`
ADR-0017.

## Workstream

Research Family E - Cross-Sectional Factors. Primeira task da familia;
CS-002 (Cross-Sectional Mean Reversion), CS-003 (Residual Momentum),
CS-004 (PCA Statistical Arbitrage) e CS-005 (Ensemble) ficam registradas
como backlog planejado, nao iniciadas -- por decisao explicita do
usuario, esta familia e executada uma task por vez, nao em paralelo, para
preservar o mesmo rigor de nao formular uma hipotese futura depois de ver
o resultado de uma anterior.

Nao herda metricas nem conclusoes de nenhuma familia anterior (A: Kalman/
OU mean-reversion, ADR-0010; B: Funding Carry, ADR-0013; TSMOM; C: TSREV,
ADR-0014; D: Payoff Engineering, ADR-0015/0016).

## Objetivo desta task (diferente das familias anteriores)

Todas as familias anteriores testaram hipoteses formuladas internamente
neste projeto (diagnosticos proprios). Esta task inverte a ordem: replica
uma formulacao JA DOCUMENTADA na literatura academica especifica de
cripto, o mais fielmente possivel dentro das limitacoes deste dataset
(20 symbols, barras horarias, 2023-06 a 2026-05), para verificar se um
efeito com respaldo previo sobrevive neste universo e sob custo
realista -- antes de formular qualquer variante propria.

## Hipotese primaria (unica, decisoria)

```text
Cross-Sectional Momentum, formulacao semanal estilo Liu & Tsyvinski
(2021, Journal of Financial Economics, "Risks and Returns of
Cryptocurrencies"): retorno da semana de formacao prediz positivamente o
retorno da semana seguinte -- comprar vencedores, vender perdedores.
```

### Justificativa da escolha (registrada ANTES de rodar qualquer backtest)

```text
- Formulacao especifica de cripto (nao uma convencao de equities
  emprestada, como o classico 12-1 de Jegadeesh-Titman) -- mais fiel ao
  ativo real deste projeto.
- Horizonte semanal produz amostra razoavel dentro dos 3 anos de dados
  disponiveis (~150 semanas nao-sobrepostas), diferente do horizonte
  mensal classico (~36 observacoes) ou do 12-1 classico (~24
  observacoes), ambos com poder estatistico baixo demais para este
  universo pequeno (20 symbols).
- E a formulacao MAIS SIMPLES das opcoes de replicacao consideradas --
  consistente com o principio de "nao inventar, replicar literatura
  antes de inovar" desta task.
```

Nenhum backtest de momentum foi rodado antes desta escolha. O diagnostico
informal de "Momentum Cross-Sectional" ja feito nesta sessao
(`reports/tsmom_diagnostic.md`, horizontes 12h-7d, frac_positive
48-52%) NAO substitui este teste -- aquele diagnostico usou horizontes
intradiarios/curtos sem a convencao formal de formacao/holding semanal
da literatura, e nao era causalmente idêntico a esta formulacao (nao
usava ranking cross-sectional em decis/quintis).

## Regra de decisao (explicita, literal)

```text
Somente esta hipotese primaria (momentum semanal, quintil, formacao=
holding=168h) pode fundamentar a continuidade da linha Cross-Sectional
Momentum.

Nenhum sweep de horizonte, de K, ou de convencao de peso e permitido
dentro desta task. Se o resultado nao passar o gate, a linha fecha como
"nao replicado neste universo/periodo" -- nao sera re-testada com
parametros ajustados apos ver o resultado (mesma disciplina de
ADR-0010/TASK-FUND-003).

Nenhuma celula (primaria ou qualquer futura secundaria de CS-002+)
autoriza promocao a paper trading, live trading, ou nova linha principal
de desenvolvimento.
```

## Construcao do sinal (causal, fiel a literatura -- SEM normalizacao por
## volatilidade, diferente do z-score usado em TSREV)

```text
r_i,t(H) = log_price_i[t] - log_price_i[t-H]     (retorno de formacao,
                                                   causal, conhecido em t)
```

Sem divisao por sigma: a literatura de momentum classico ordena por
retorno bruto de formacao, nao por retorno ajustado a volatilidade
(isso seria uma variante de "risk-adjusted momentum", fora do escopo
desta replicacao fiel).

## Regra de trade

```text
A cada H=168h (1 semana): ranquear os 20 symbols do universo por r_i,t(H).

LONG  nos K=4 de MAIOR retorno de formacao (vencedores, quintil superior
      de 20 symbols).
SHORT nos K=4 de MENOR retorno de formacao (perdedores, quintil inferior).

Sinal INVERTIDO em relacao ao TSREV Familia B (que e reversao: compra
perdedores, vende vencedores). Aqui e momentum: compra vencedores, vende
perdedores.

Holding: H=168h fixo, sem skip-period, sem trailing stop, sem barreira.
Book fechado e reaberto integralmente a cada intervalo de H horas (full
rebalance, mesmo padrao ja usado em TSREV Familia B e Funding Carry fase
1).

Cada posicao individual (symbol, lado, rebalanceamento) e registrada como
uma "trade" resolvida quando o horizonte de holding se completa dentro
dos dados; se o fim dos dados chega antes, a posicao e OPEN_AT_END, nunca
fabricada como fechada.
```

## Tamanho de posicao

```text
peso_i = 1 / (2*K) = 1/8 por posicao, fixo, igual para todas as 8 pernas
         de cada rebalanceamento (4 long + 4 short) -- equal-weight,
         dollar-neutro. Convencao padrao de portfolios de quintil na
         literatura (nao a ponderacao inversa-a-vol usada no TSREV
         Familia A, que era especifica de uma estrategia time-series
         single-asset).
```

## Custo

```text
cost_bps_roundtrip = 6.0 (mesma constante conservadora reusada em
                          TSREV e Funding Carry -- nao os 12,0bps
                          taker-taker do TSMOM, que era especifico de
                          entradas de breakout, presumivelmente menos
                          makeable que um rebalanceamento programado).
```

## Divisao amostral (out-of-sample)

```text
Reusa EXATAMENTE a mesma fronteira ja pre-registrada em
TASK-TSREV-001 -- nao escolhida de novo por hipotese, para evitar
qualquer aparencia de split escolhido para favorecer o resultado:

Desenvolvimento (in-sample, contexto apenas): 2023-06-01 a 2025-05-31
Teste decisivo (out-of-sample):               2025-06-01 a 2026-05-31

O gate e decidido SOMENTE no periodo out-of-sample. O periodo in-sample
e reportado para contexto/robustez, nunca para decidir.
```

## Baseline do Max Drawdown

```text
Max drawdown de um portfolio buy-and-hold equal-weight dos mesmos 20
symbols, no MESMO periodo out-of-sample -- mesma funcao generica
(`buy_and_hold_max_drawdown_bps`) ja usada e revisada em TSREV.
```

## Gate pre-registrado (todos simultaneos, avaliados so no OOS)

```text
net_profit_factor > 1.10   (mesmo piso "casa" ja usado em Funding Carry
                            e no Sprint 8 canonico -- nao o 1,05 do TSREV,
                            que foi justificado especificamente para uma
                            estrategia time-series single-asset, nem o
                            1,20 do TSMOM, especifico de breakout)
E net_pnl_bps > 0
E max_drawdown_bps <= max_drawdown_buy_and_hold_bps (no mesmo periodo OOS)
E resolved_trade_count (nivel de perna individual) >= 200
```

## Metodologia de validacao (decisao explicita do usuario)

```text
Split cronologico simples in-sample/out-of-sample (identico ao padrao
ja usado e provado em TASK-TSREV-001/TASK-FUND-001), NAO walk-forward
com multiplos folds, NAO purged cross-validation. Justificativa: esta
task usa uma regra fixa, unica, sem sweep de hiperparametro nem selecao
de modelo entre folds -- o problema que purged CV resolve (contaminacao
entre folds quando ha overlap de labels DURANTE selecao de
modelo/hiperparametro) nao se aplica aqui. Walk-forward/purged CV fica
registrado como candidato de infraestrutura para uma FUTURA task que
efetivamente precise de selecao de hiperparametro (ex.: uma variante de
momentum com sweep de K ou H), nao para esta replicacao de regra unica.
```

## Invariantes obrigatorios

```text
- r_i,t(H) usa apenas log_price conhecido ate t (causal por construcao,
  diff backward, sem shift adicional necessario pois nao ha
  normalizacao por sigma).
- Ranking cross-sectional em cada rebalanceamento usa apenas retorno de
  formacao conhecido naquele instante -- sem look-ahead.
- Posicao aberta no fim dos dados nunca e fabricada como fechada.
- Gate e calculado apenas no periodo out-of-sample.
```

## Fora de escopo

```text
- Sweep de horizonte (H diferente de 168h), de K (quintil diferente de
  4), ou de convencao de peso dentro desta task.
- Skip-period (convencao usada em algumas formulacoes mensais de
  momentum, mas nao na formulacao semanal escolhida).
- Normalizacao por volatilidade (risk-adjusted momentum) -- variante
  distinta, exigiria seu proprio pre-registro.
- Walk-forward multi-fold ou purged CV nesta task (ver Metodologia
  acima).
- CS-002 (Cross-Sectional Mean Reversion), CS-003 (Residual Momentum),
  CS-004 (PCA Statistical Arbitrage), CS-005 (Ensemble) -- backlog
  planejado, cada uma exige seu proprio pre-registro antes de qualquer
  codigo, escrito somente apos esta task fechar.
- Novo download de dados.
- ML, XGBoost, meta-labeling.
- Promocao a paper/live com base em qualquer resultado desta task.
- Reinterpretar o gate apos ver o resultado (ex.: trocar o piso de
  1,10, o piso de 200 trades, ou a definicao de quintil).
```
