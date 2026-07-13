# TASK-TSM-005 - Definicao e pre-registro: Linha 5 (ensemble) -- TSM (trend) + funding-carry K=5 (carry)

## Status

ACCEPTED (locked) - travado 2026-07-12 antes de qualquer implementacao. Sob
ADR-0031 (Programa de Melhoria do TSM), Linha 5. Dev != promocao (OOS-gated).
Blend SEM knob (equal-risk); sem re-tune; sem promover secundario ex-post.

## Revisao de literatura (grounding)

- Koijen, Moskowitz, Pedersen, Vrugt "Carry" (2018, JFE): carry e um fator
  distinto e complementar a momentum/trend em todas as classes de ativos.
- Managed futures (AQR; Baltas & Kosowski): TREND + CARRY sao as duas fontes
  de retorno canonicas e DIVERSIFICANTES de CTAs; combina-las por risk parity
  melhora o Sharpe quando a correlacao dos streams e baixa.
- Precedente interno: das familias nao-TSM testadas, a UNICA com edge foi o
  funding carry K=5 incremental (near-miss PF 1,0904, net POSITIVO na janela
  dev +5.620 bps). E o UNICO parceiro de ensemble economicamente defensavel
  (ADR-0027 proibe ensemble com fontes ja SEM_INFO -> exclui OI/basis/flow).
  Cautela divulgada: o 1o mes OOS do carry (jun/2026) foi NEGATIVO -- por isso
  qualquer beneficio no dev e OOS-gated.

## Hipotese economica (clara)

Trend (TSM) e carry (funding) capturam premios distintos; se seus retornos
sao pouco correlacionados, um blend equal-risk dos dois streams tem Sharpe
maior que o TSM sozinho (diversificacao). Testa se ADICIONAR carry ao TSM
melhora a metrica ajustada ao risco do TSM.

## Metodologia

```text
Streams de P&L (dev 2023-06..2026-05):
  - TSM: net por rebalance de 5d (run_tsm_trend_backtest, include_funding).
  - Carry: net_pnl_bps por intervalo (run_incremental_funding_carry_backtest,
    K=5 pre-registrado).
Alinhamento: agregar cada stream por SEMANA calendario (soma do P&L na
semana); manter so semanas com dado nos DOIS. Frequencia comum semanal.
Padronizacao: cada stream semanal dividido pela sua vol dev (unidade de
risco); escala (bps vs fracao) cancela -> Sharpe invariante a escala.
Blend equal-risk (SEM knob): 0,5*z_tsm + 0,5*z_carry.
Metricas: Sharpe anualizado (sqrt(52)) de TSM, carry, blend; correlacao dos
streams; max drawdown de cada cumulativo.
```

## Celula primaria (LOCKED, exatamente 1)

```text
Blend equal-risk 50/50 (dois streams padronizados a unit-vol), semanal.
Exatamente 1 variante. Sem grade de pesos; sem otimizacao de alocacao por
desempenho (isso seria curve-fitting da alocacao).
```

## Bateria de robustez (as aplicaveis; ADR-0031 regra 5)

```text
1. Estabilidade entre os 3 subperiodos (o blend > TSM em cada um?).
2. Drawdown (o blend reduz maxDD vs TSM?).
3. Correlacao dos streams (baixa/negativa justifica o blend; alta positiva
   nao -- diagnostico do mecanismo).
4. Simplicidade vs ganho (operar DOIS livros e mais complexo/custoso;
   o ganho de Sharpe justifica?).
5. Justificativa economica (trend+carry diversificam -- coerente, nao ex-post).
6. Falso-positivo: beneficio CONSISTENTE nos 3 subperiodos; concentrado = rejeicao.
(Sensibilidade a custo/funding: cada stream ja e net de seus custos; o blend
nao adiciona custo de sinal, so o de operar dois livros -- nota qualitativa.)
```

## Criterio de decisao (dev)

```text
CANDIDATO A OOS somente se: Sharpe do blend > Sharpe do TSM sozinho, de forma
CONSISTENTE nos 3 subperiodos, com correlacao de streams baixa/negativa
(mecanismo real de diversificacao) E maxDD do blend <= TSM. Caso contrario:
REJEITADO, encerrado com resultado documentado, seguir para a Linha 6
(execucao). Sem promocao; gate BLOQUEADO ate OOS (reforcado pelo carry ja ter
dado OOS negativo em jun/2026).
```

## Invariantes

```text
- Blend equal-risk sem knob; sem otimizacao de pesos; sem re-tune.
- Cada stream vem do seu backtest ja testado (TSM FC-II-005/008; carry
  FUND-003), inalterados.
- Padronizacao usa vol dev (nota: sizing in-sample; e diagnostico dev, nao
  promocao -- promocao usa OOS).
- Dev != promocao; gate BLOQUEADO ate OOS novo.
- so pesquisa/paper, nada real.
```

## Fora de escopo

```text
- Otimizacao de alocacao trend/carry (grade de pesos) -- curve-fitting.
- Ensemble com fontes ja SEM_INFO (OI/basis/flow/regime) -- ADR-0027 proibe.
- Blend em nivel de sinal (misturar os sinais) -- e outro desenho; aqui e
  blend de STREAMS de retorno.
- Promocao / OOS (gate separado quando houver dado novo).
```
