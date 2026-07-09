# TASK-ML-001 - Definicao e pre-registro: Meta-Labeling Condicionado a Regime como FILTRO sobre o Funding Carry Incremental K=5

## Status

ACCEPTED (locked) - travado explicitamente pelo usuario em 2026-07-09,
antes de qualquer codigo. Ver `project_control/DECISIONS.md` ADR-0026.
Fase de DESENVOLVIMENTO (harness de CV, features, selecao de
modelo/threshold via CV na janela existente) autorizada a comecar agora.
O GATE de PROMOTE/NAO_PROMOVE permanece BLOQUEADO ate o holdout de OOS
novo (>= 500 rebalanceamentos resolvidos apos 2026-05-31) existir --
nenhum veredito de promocao pode ser computado antes disso.

## Workstream

Novo programa de pesquisa: **Funding Carry Inteligente** -- usar ML
para extrair mais valor de um edge que JA existe, nao para descobrir um
sinal novo. Este e o PRIMEIRO e UNICO bet do programa a ser
pre-registrado agora; as demais familias de ML (ranking, RL, deep
learning, GNN, dynamic sizing, dynamic K, survival, dynamic threshold)
ficam explicitamente FORA DE ESCOPO ate esta task fechar seu proprio
gate (ver "Fora de escopo").

## Por que esta hipotese, e nao uma das outras 9 (prior empirico, nao
## chute entre 10)

Duas evidencias que o proprio projeto ja produziu tornam esta a aposta
de maior prior:

```text
1. FUNDING CARRY INCREMENTAL K=5 e o resultado mais proximo de um gate
   em todo o projeto: profit factor liquido 1,0904 vs gate 1,10 (0,0096
   de distancia), PnL liquido JA POSITIVO (+5.620,99 bps) sobre 3.287
   rebalanceamentos (nao e limite de amostra). O edge BRUTO e real e
   persistente (+8.992,18 bps); o rebalanceamento incremental ja cortou
   99,83% do custo. Ou seja: existe edge economico plausivel para um
   filtro CONCENTRAR -- e o modo de falha e "custo/selecao", nao um
   blow-up estrutural.

2. FAMILIA J (Regime Detection, TASK-ALT-003) foi o UNICO sinal forte
   encontrado em todo o programa: realized_vol_168h rho=0,30,
   realized_vol_24h rho=0,29, estaveis nos 3 subperiodos. ADR-0021
   classificou-o como informacao de RISCO/CONTEXTO, explicitamente NAO
   alpha direcional, e proibiu qualquer uso operacional sem uma task
   nova pre-registrada. ESTA e essa task: usar regime como camada de
   CONDICIONAMENTO ("executar a perna de carry so quando o estado de
   vol/regime favorece"), que e exatamente o uso que ADR-0021 previu.
```

Nenhuma outra das 9 familias de ML tem suporte empirico independente
dentro deste projeto. Ranking seria o segundo bet, mas so se este
sobreviver ao gate.

## Natureza desta task: FILTRO (meta-labeling), nao gerador de sinal

Filosofia de Lopez de Prado (meta-labeling): o modelo PRIMARIO ja
existe e ja esta pre-registrado (o funding carry incremental K=5, ADR-
0013/TASK-FUND-003) -- ele decide QUAIS pernas abrir. O modelo
SECUNDARIO (meta) decide APENAS "esta perna especifica vale a pena
executar?". O ML nunca gera um sinal novo, nunca preve preco, nunca
escolhe lado. Ele so faz um corte binario sobre pernas que o sinal
primario ja escolheu.

```text
Fluxo (semantica travada pelo usuario 2026-07-09: gatear so
ENTRADAS/SWAPS -- Opcao 1):
  Funding carry incremental K=5  (sinal primario, INALTERADO)
        v
  a cada rebalanceamento a politica incremental PROPOE entradas/swaps
  (novas pernas que substituiriam uma perna mantida ou preencheriam um
   slot vazio no bootstrap)
        v
  meta-modelo: para CADA entrada/swap proposto, P(a nova perna sera
  net-lucrativa ao longo do seu hold ate o proximo swap/saida)
        v
  se P < threshold, VETA o swap: mantem a perna anterior no slot (ou
  fica em caixa se o slot estava vazio -- so no bootstrap). NUNCA gera
  perna nova, nunca inverte lado.
        v
  re-roda a politica incremental COM o veto aplicado e re-sumariza com
  summarize_funding_carry_backtest (MESMA convencao de PnL/custo)
```

Distincao explicita treino vs avaliacao (padrao de meta-labeling):
  - LABEL de TREINO = net PnL de cada entrada/swap que a politica
    incremental NAO-FILTRADA de fato fez, ao longo do hold realizado sob
    essa politica nao-filtrada, menos o custo de entrada. Rotula-se a
    decisao do modelo primario como ela foi tomada.
  - AVALIACAO (OOS de cada fold da CV e holdout final) = re-roda a
    politica incremental COM o veto do meta-modelo aplicado, mede o PnL
    real da estrategia filtrada e compara ao baseline nao-filtrado na
    MESMA janela. O gate final e honesto mesmo que o veto altere holds
    futuros, porque a avaliacao usa a politica filtrada de verdade.

O sinal primario, seu K=5, seu modelo de custo e sua convencao de sinal
NAO sao alterados nesta task. Se alterados, seria outra task.

## Unidade de rotulo (meta-label)

```text
Uma observacao = uma ENTRADA/SWAP (symbol, rebalanceamento de entrada)
que a politica incremental NAO-FILTRADA de fato executou. Nao e "toda
perna por intervalo" -- e o momento em que uma perna nova entra no
livro.

Label binario:
  y = 1 se o net PnL realizado da perna, acumulado ao longo de TODOS os
        intervalos em que ela ficou no livro sob a politica nao-filtrada
        (funding recebido/pago +/- retorno de preco da perna a cada
        intervalo), MENOS o custo de entrada por perna ja pre-registrado,
        for > 0
  y = 0 caso contrario.

O PnL por intervalo de cada perna reusa EXATAMENTE o computo de
_book_funding_and_price_pnl_bps / _price_return de funding_carry.py --
nao ha nova formula de PnL nesta task. Uma perna mantida ate o fim dos
dados (sem swap posterior) e rotulada pelo PnL acumulado ate o fim.
```

## Features candidatas (LOCKED, deliberadamente pequenas -- 9 no total,
## formalizadas ANTES de qualquer fit)

Feature set pequeno e proposital: com edge de 0,0096 de folga, um modelo
com dezenas de features ACHA um jeito de "passar" 1,10 in-sample por
overfit. Limitar o espaco de features e a primeira defesa.

```text
Regime / contexto (6) -- reusa VERBATIM as features causais de
TASK-ALT-003 (Familia J), ja implementadas e testadas em
scripts/diagnostic_alt_regime_detection.py:
  1. realized_vol_24h
  2. realized_vol_168h
  3. trend_intensity_168h
  4. market_dispersion_24h
  5. market_abs_return_24h
  6. volume_shock_24h

Funding-native, por perna, causais (3):
  7. funding_rate_asof          (a taxa ja liquidada da propria perna --
                                 a mesma coluna causal que o sinal usa)
  8. funding_zscore             (shift(1).rolling(2160h) mean/std do
                                 funding_rate_asof do proprio symbol --
                                 mesma normalizacao causal de ALT-001/002)
  9. cross_sectional_rank       (posicao de rank da perna entre as 2K no
                                 rebalanceamento; conhecida em t, causal)

TODAS causais por construcao: shift(1) antes de qualquer rolling. O
LABEL (net PnL futuro da perna) e o UNICO lugar onde dado posterior a t
e usado.
```

## Classe de modelo e busca (LOCKED antes do fit)

```text
Classe: XGBoost classificador binario (xgboost>=3.3.0, JA e dependencia
do projeto -- nenhuma dependencia pesada nova). Uma unica classe de
modelo; nenhuma outra (nem sklearn, nem rede) sera tentada nesta task.

Grid de hiperparametros FIXO e pequeno, declarado aqui:
  max_depth        in {2, 3, 4}
  n_estimators     in {100, 300}
  learning_rate    in {0.03, 0.10}
  min_child_weight in {5, 20}
  (subsample=0.8, colsample_bytree=0.8, fixos)
  => 24 combinacoes, e so.

class_weight balanceado (scale_pos_weight) para o desbalanceamento do
label. Seed fixa e registrada. Nenhuma busca de arquitetura ou de
feature alem deste grid.
```

## Harness de validacao (A TRAVA -- construida e testada ANTES de
## qualquer modelo)

```text
1. PURGED + EMBARGOED walk-forward cross-validation (Lopez de Prado):
   - Rotulos de pernas se sobrepoem no tempo (holds simultaneos), entao
     CV ingenuo VAZA. Purga = remover do treino toda perna cujo horizonte
     de hold intersecta o periodo de teste do fold. Embargo apos cada
     fold de teste = 1x o horizonte de hold (o intervalo de
     rebalanceamento, 8h).
   - Folds cronologicos, walk-forward (treino sempre no passado do teste).

2. SELECAO do modelo e do threshold de probabilidade acontece SO nos
   folds de CV (metrica declarada: PF liquido da estrategia filtrada no
   fold, sujeito a um piso de N de pernas mantidas). O threshold e o
   hiperparametro vencedor sao CONGELADOS ao fim da CV.

3. HOLDOUT FINAL tocado EXATAMENTE UMA VEZ, com o modelo/threshold ja
   congelados. Nenhum ajuste depois de olhar o holdout.
```

## Gate final: BLOQUEADO ate OOS genuinamente novo (consistente com
## ADR-0023/0024)

```text
RISCO DE DATA-MINING (declarado, nao contornado): o resultado do funding
carry K=5 (1,0904) JA foi visto na janela 2023-06/2026-05. Uma hipotese
de meta-labeling desenhada para melhorar EXATAMENTE esse resultado,
testada NA MESMA janela, e data-mining -- o mesmo padrao que ADR-0023
(PAYOFF-002) e ADR-0024 (ALT-006) bloquearam.

Portanto:
  - DESENVOLVIMENTO (engenharia de features, harness de purged-CV,
    selecao de modelo/threshold via CV na janela existente) PODE proceder
    agora. Isso NAO gera veredito de promocao.
  - O GATE de PROMOTE/NAO_PROMOVE fica BLOQUEADO ate existir OOS
    genuinamente novo (dados de rebalanceamento resolvidos apos
    2026-05-31), reusando o mes de Junho/2026 ja baixado uma vez que
    houver acumulo suficiente.
  - TRIGGER pre-registrado: holdout final deve conter >= 500
    rebalanceamentos resolvidos novos (a partir de 2026-06-01) -- mesmo
    piso do gate do sinal-base. A ~3 rebalanceamentos/dia isso e ~5,5
    meses (~meados de Novembro/2026). Numero honesto; nao encolhido para
    apressar veredito.
```

## Criterios de sucesso (pre-registrados, TODOS obrigatorios, no holdout
## novo e intocado)

```text
PROMOTE somente se as 4 condicoes valerem simultaneamente:
  (a) PF liquido da estrategia FILTRADA >= 1,10   (o gate do sinal-base)
  (b) PnL liquido da estrategia FILTRADA > 0
  (c) a estrategia filtrada ainda atua em >= 500 rebalanceamentos no
      holdout  (guarda contra "PF 1,3 em 200 trades" -- nao pode vencer
      negociando quase nada)
  (d) PF liquido filtrado EXCEDE o PF do baseline K=5 NAO-FILTRADO no
      MESMO holdout por >= +0,02 absoluto  (a guarda anti-overfit
      central: bater 1,10 no absoluto nao basta; o filtro tem que
      demonstravelmente AGREGAR valor sobre a coisa que ele filtra)

Qualquer condicao que falhe => NAO_PROMOVE, e o primeiro bet do programa
de ML fecha (ou informa uma hipotese revisada, separadamente
pre-registrada). Nenhum ajuste de threshold/feature/gate apos ver o
holdout.
```

## Invariantes obrigatorios

```text
- Todas as 9 features sao causais: shift(1) antes de qualquer rolling.
- O LABEL (net PnL futuro da perna) e o UNICO uso de dado posterior a t.
- Purga + embargo removem vazamento de rotulos sobrepostos -- testado
  unitariamente (um caso construido onde purga ausente vazaria e a purga
  o impede).
- Sinal primario, K=5, modelo de custo e convencao de PnL: INALTERADOS.
- Classe de modelo, grid de hiperparametros, metrica de selecao e regra
  de threshold: CONGELADOS neste documento antes de qualquer fit.
- Holdout final tocado exatamente uma vez.
- Fail closed: qualquer feature ausente, qualquer falha na auditoria de
  look-ahead, ou qualquer holdout com < 500 rebalanceamentos aborta sem
  veredito.
- Gate de promocao BLOQUEADO ate o trigger de OOS novo ser satisfeito.
```

## Fora de escopo (compressao deliberada das "10 familias" para 1 bet)

```text
Cada item abaixo, SE perseguido, e uma task NOVA e separadamente
pre-registrada, e SO depois de esta fechar/informar seu gate:
  - Learning-to-rank (LambdaMART/LightGBM Ranker) sobre o carry.
  - Reinforcement learning (timing de rebalanceamento/swap).
  - Deep learning (Transformer/TFT/LSTM/TCN) -- ALEM DISSO: volume de
    dados (~3.300 settlements/symbol) NAO justifica; provavelmente nunca
    entra.
  - Graph neural network.
  - Dynamic position sizing / dynamic capital allocation.
  - Dynamic K / dynamic swap-threshold aprendido.
  - Survival analysis para tempo de hold.
Tambem fora de escopo:
  - Qualquer alteracao no sinal primario, no K=5, no custo ou na
    convencao de PnL.
  - Qualquer feature alem das 9 formalizadas.
  - Qualquer computo de veredito de promocao antes do OOS novo.
  - Novo download alem da extensao pos-2026-05-31 que as tasks de
    near-miss ja precisam (nenhum family novo e baixado).
  - Mutual information ou qualquer seletor de feature automatico.
```
