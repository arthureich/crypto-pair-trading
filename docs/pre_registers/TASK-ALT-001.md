# TASK-ALT-001 - Definicao e pre-registro: Diagnostico de Conteudo Informacional, Familia G (Funding Structure)

## Status

DONE (definicao). Aprovado explicitamente pelo usuario nesta sessao antes
de qualquer codigo ser escrito. Ver `project_control/DECISIONS.md`
ADR-0019.

## Workstream

Research Phase II - Alternative Information, primeira task. Familia G
(Funding Structure), a primeira executada por ter dado JA EXISTENTE no
dataset normalizado (`funding_rate_asof`, causal, 100% de cobertura,
verificado nesta sessao) -- zero novo download.

## Natureza desta task: DIAGNOSTICO, nao estrategia

Diferente de toda pesquisa anterior deste projeto (feature -> regra ->
backtest), esta task inverte a ordem: mede se uma feature tem conteudo
informacional preditivo ANTES de desenhar qualquer regra de entrada/saida
de trade. Sem gate de PASSA/NAO_PASSA de performance economica -- o
resultado e "tem informacao" ou "nao tem informacao," per criterios
fixados abaixo. Se uma feature mostrar informacao, o desenho de uma
estrategia operacional em torno dela e um TASK-ALT-002 (ou posterior)
separado, com seu proprio pre-registro -- mesmo padrao ja usado em
ADR-0015 (Payoff Engineering Fase 1 diagnostico -> Fase 2 estrategia).

## Regra geral da Fase II (vale para toda a fase, nao so esta task)

```text
Nenhuma hipotese desta fase pode se basear exclusivamente em OHLCV
(open/high/low/close/volume). Familia J (Regime Detection) e uma
excecao explicita e deliberada: por nao gerar trades nem afirmar ter
descoberto edge (e uma camada de segmentacao/contexto para condicionar
outras estrategias), pode usar features derivadas de OHLCV (ex.:
volatilidade, tendencia).
```

## Metodologia geral de diagnostico (infraestrutura reutilizavel, nao
## especifica desta task)

```text
Metrica primaria: correlacao de Spearman (rank, monotonica, sem
suposicao de linearidade, sem hiperparametro de binning/vizinhanca) entre
uma feature causal[t] e o retorno futuro[t, t+H].

Nao mutual information: decisao explicita do usuario, pela mesma
preferencia por simplicidade que motivou o abandono de Kalman/OU e de
purged CV nesta sessao -- MI exigiria escolhas de binning/estimador sem
beneficio claro para o proposito de triagem inicial.

Estabilidade: a correlacao e calculada separadamente em 3 subperiodos
cronologicos NAO-SOBREPOSTOS de ~12 meses cada (2023-06 a 2024-05,
2024-06 a 2025-05, 2025-06 a 2026-05) -- particao DIFERENTE da fronteira
in-sample/out-of-sample ja usada em TASK-TSREV-001/CS-001/CS-002
(deliberado: aqui o proposito e testar estabilidade temporal ampla, nao
decidir um gate de estrategia).

Critério de "tem informacao" (fixado ANTES de rodar qualquer diagnostico
real):

  |rho_amostra_completa| >= 0.03
  E sinal de rho consistente nos 3 subperiodos E na amostra completa

0,03 e um limiar de magnitude deliberadamente baixo -- reflete que
preditores individuais fracos ja sao economicamente relevantes em
finance (nao se espera rho alto de uma unica feature), mas o criterio de
CONSISTENCIA DE SINAL em 3 janelas nao-sobrepostas e o que realmente
filtra ruido de um efeito espurio de amostra completa.
```

## Horizonte de retorno futuro (target), fixado para toda a Familia G

```text
forward_return[t, t+H] = log_price[t+H] - log_price[t], H=24h -- mesmo
horizonte ja usado em TASK-CS-002 (reusado por consistencia, nao
re-escolhido por hipotese).
```

## Features candidatas desta task (4, propostas pelo usuario em
## linguagem natural, formalizadas explicitamente ANTES do diagnostico
## rodar)

```text
1. funding_extreme[t]: z-score causal do funding atual relativo a sua
   propria historia recente --
     mean_90d[t] = funding_rate_asof.shift(1).rolling(2160h).mean()
     std_90d[t]  = funding_rate_asof.shift(1).rolling(2160h).std()
     funding_extreme[t] = (funding_rate_asof[t] - mean_90d[t]) / std_90d[t]

2. funding_reversal[t]: variacao do funding nas ultimas 24h --
     funding_reversal[t] = funding_rate_asof[t] - funding_rate_asof[t-24]

3. funding_acceleration[t]: variacao da variacao (2a diferenca) --
     funding_acceleration[t] = funding_reversal[t] - funding_reversal[t-24]

4. funding_price_divergence[t]: funding subindo (relativo a sua propria
   historia) enquanto preco NAO acompanha, ou vice-versa --
     price_return_24h[t] = log_price[t] - log_price[t-24]
     z_funding_reversal[t] = funding_reversal[t] normalizado
         (shift(1).rolling(2160h) mean/std do proprio funding_reversal)
     z_price_return[t] = price_return_24h[t] normalizado
         (shift(1).rolling(2160h) mean/std do proprio price_return_24h)
     funding_price_divergence[t] = z_funding_reversal[t] - z_price_return[t]

Todas as 4 sao causais por construcao (shift(1) antes de qualquer
rolling, apenas dados conhecidos em t).
```

## Universo e amostra

```text
20 symbols do dataset ja normalizado (mesmo universo de toda a pesquisa
desta sessao). Painel empilhado (pooled): todas as observacoes
(symbol, open_time) de todos os 20 symbols juntas na mesma correlacao --
maximiza tamanho de amostra, mesmo padrao de pooling ja usado em
TASK-TSREV-001 (trades pooled entre symbols).
```

## Invariantes obrigatorios

```text
- Toda feature usa shift(1) antes de qualquer rolling -- a barra t nunca
  influencia sua propria estatistica normalizadora.
- O TARGET (retorno futuro) e o UNICO lugar onde dados posteriores a t
  sao usados -- e o proposito de um diagnostico preditivo, nao uma
  violacao de causalidade (a FEATURE, que e o que decidiria uma acao,
  nunca ve o futuro).
- Nenhum gate de performance economica, custo, ou execucao nesta task --
  e puramente um diagnostico de conteudo informacional.
- Os 3 subperiodos sao fixados ANTES de rodar o diagnostico -- nenhuma
  reparticao apos ver resultados parciais.
```

## Fora de escopo

```text
- Desenhar qualquer regra de entrada/saida/position sizing em torno de
  uma feature que mostrar informacao -- isso e uma TASK-ALT-002 (ou
  posterior) separada, com seu proprio pre-registro.
- Qualquer outra feature de funding alem das 4 formalizadas acima.
- Qualquer outro horizonte de retorno futuro alem de 24h.
- Mutual information ou qualquer estimador nao-linear.
- Familias F (Open Interest), H (Order Flow), I (Liquidation Dynamics,
  formalmente BLOCKED por falta de fonte de dados historica -- ver
  ADR-0019), J (Regime Detection) -- cada uma exige seu proprio
  pre-registro.
- Novo download de dados (esta task usa dado ja existente).
```
