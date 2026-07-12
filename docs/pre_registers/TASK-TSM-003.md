# TASK-TSM-003 - Definicao e pre-registro: Linha 3 (portfolio construction) -- ERC (equal risk contribution)

## Status

ACCEPTED (locked) - travado 2026-07-12 antes de qualquer implementacao. Sob
ADR-0031 (Programa de Melhoria do TSM), Linha 3. Dev != promocao (OOS-gated).
Params FIXOS a priori; sem re-tune; sem promover secundario ex-post.

## Revisao de literatura (grounding)

- Baltas, "Trend-Following, Risk-Parity and the Influence of Correlations"
  (SSRN): esquemas de ponderacao que respeitam a estrutura de CORRELACAO
  (ERC / risk parity com "multiplicador de diversificacao") melhoram
  materialmente o desempenho do trend-following, sobretudo em regimes de
  correlacao media alta. Risk-parity/ERC/HRP e o padrao em managed futures.
- HRP (Lopez de Prado, 2016): risk parity hierarquico via clustering +
  bisseccao recursiva; introduz escolhas (linkage, metrica) -> fica como
  task propria se ERC pintar algo.
- Especifico de cripto (busca ALT/Linha-1/2): altcoins se movem em bloco com
  BTC (correlacoes -> 1 em crashes). Logo o inverse-vol NAIVE (risk parity
  diagonal, que a base ja usa) IGNORA a correlacao e concentra risco em um
  unico cluster BTC-beta. ERC reparte risco pela covariancia real.

## Hipotese economica (clara)

A base pondera cada perna por inverse-vol e normaliza a unit-gross -- risk
parity DIAGONAL, que trata as pernas como independentes. Em cripto, alta
correlacao entre pernas faz o risco realizado se concentrar no cluster
BTC-beta. Distribuir por ERC (contribuicao de risco igual, usando a
covariancia) diversifica melhor -> menor drawdown e melhor metrica ajustada
ao risco, com a MESMA direcao e o MESMO split long/short da base.

## Metodologia

```text
Base INALTERADA: TSM vol-targeted FC-II-005/008 (peso ~ sign(trailing)/vol,
unit-gross, 5d, funding). Flag opt-in (default OFF); base intacta.

ERC (SEM alterar direcao nem split L/S da base):
  Em cada rebalance t, a partir dos pesos-base ls_weight[t]:
   - preserva o GROSS de cada sleeve: long_gross = soma dos pesos>0,
     short_gross = -(soma dos pesos<0).
   - covariancia causal: das retorno horario nas ULTIMAS `window` horas
     ate t (shift(1), sem usar t+), submatriz de cada sleeve (so symbols
     com dado completo na janela; symbols sem dado mantem o peso-base).
   - erc_weights(cov_sleeve) -> pesos positivos, contribuicao de risco
     igual, soma 1; escala pelo gross do sleeve e aplica o sinal.
   - resultado renormalizado nao e necessario (preserva unit-gross por
     construcao: long_gross + short_gross == gross-base).
  window = 2160h (90d) -- FIXO a priori (janela causal padrao do projeto),
  nao tunavel. algoritmo ERC = coordinate descent (Griveau-Billion et al.).
```

## Celula primaria (LOCKED, exatamente 1)

```text
ERC por sleeve preservando direcao e split L/S da base, covariancia amostral
causal de 2160h. Exatamente 1 variante primaria elegivel a OOS futura.
Sem grade de janelas; sem shrinkage tunavel; sem HRP (task propria).
```

## Bateria de robustez (TODAS obrigatorias; ADR-0031 regra 5)

```text
1. Estabilidade entre os 3 subperiodos.
2. Sensibilidade a custo (grade; breakeven).
3. Sensibilidade a funding (com/sem).
4. Regimes de mercado (BTC up vs down).
5. Drawdown (o argumento central do ERC: maxDD deve melhorar).
6. Simplicidade vs ganho (ERC e MAIS complexo -- covariancia + solver;
   o ganho precisa justificar essa complexidade, per ADR-0031 regra 6).
7. Justificativa economica (diversificacao de risco, coerente, nao ex-post).
8. Falso-positivo: melhora CONSISTENTE nos 3 subperiodos E ambos os regimes
   BTC; concentrada em 1 = rejeicao.
```

## Criterio de decisao (dev)

```text
CANDIDATO A OOS somente se: melhora Sharpe E reduz maxDD vs base, DE FORMA
CONSISTENTE nos 3 subperiodos E ambos os regimes de BTC, E sobrevive
custo/funding, E o ganho JUSTIFICA a complexidade extra (covariancia +
solver) -- barra mais alta que Linhas 1/2 por ser mais complexo. Caso
contrario: REJEITADO, encerrado com resultado negativo, seguir para a
Linha 4 (meta-labeling / ML como filtro de operacoes). Sem promocao aqui.
```

## Invariantes

```text
- Params fixos a priori (window 2160h); sem re-tune; sem secundario ex-post.
- Base TSM intacta (flag default OFF); mesma direcao e split L/S da base
  (isola o efeito de construcao de portfolio dentro do sleeve).
- Causal (covariancia usa so retorno ate t via shift(1)).
- Dev != promocao; gate BLOQUEADO ate OOS novo.
- so pesquisa/paper, nada real.
```

## Fora de escopo

```text
- HRP (clustering hierarquico) -- task propria se ERC pintar algo.
- Multiplicador de diversificacao de livro inteiro (muda exposicao bruta).
- Shrinkage de covariancia tunavel; janelas alternativas.
- Promocao / OOS (gate separado).
```
