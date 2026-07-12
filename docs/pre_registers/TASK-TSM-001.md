# TASK-TSM-001 - Definicao e pre-registro: Linha 1 (filtro de regime) para o TSM vol-targeted

## Status

ACCEPTED (locked) - travado 2026-07-12 antes de qualquer implementacao. Sob
ADR-0031 (Programa de Melhoria do TSM). Resultado na janela de
desenvolvimento e SO desenvolvimento (sem veredito de promocao); promocao
so em OOS intocado. Params FIXOS a priori; sem re-tune pos-resultado.

## Revisao de literatura (grounding)

- Moreira & Muir (2017, JF) "Volatility-Managed Portfolios": escalar a
  exposicao para baixo quando a variancia recente e alta gera alfa/Sharpe
  porque a vol e menos persistente que o retorno esperado -> "timing" de
  regime de risco funciona. Barroso & Santa-Clara: mesma logica cobre
  crashes de momentum.
- Literatura cripto (SSRN/arXiv 2020-2026): cripto RECOMPENSA momentum de
  serie-temporal MAIS que cross-sectional (coerente com o TSM ser nosso lead
  e CS-001/002 falharem); altcoins se movem em bloco com BTC (regimes de
  breadth/dispersao existem); mercado tem TROCAS DE REGIME frequentes; a
  regra "TREND" escala posicoes pela FORCA ESTATISTICA do trend.
- Precedente interno (cautela divulgada): ALT-004 testou gate de regime de
  VOL no TSREV (reversao) e falhou -- mas reversao tem dependencia de regime
  OPOSTA a trend; FC-II-001 testou vol-targeting continuo (sizing) e nao
  bateu o gate. Esta task e um FILTRO discreto (quando operar), nao sizing
  continuo (que e a Linha 2), e condiciona na FORCA DO TREND, nao na vol
  isolada -- distincao divulgada, com a ressalva de que a forca usa vol no
  denominador (sobreposicao parcial com condicionamento de vol).

## Hipotese economica (clara)

O edge do TSM se concentra quando existe um trend forte a seguir; em regimes
de baixa conviccao (choppy) ele faz whipsaw e paga custo por ruido. Logo,
ficar FLAT na metade de baixa-forca do tempo deve preservar a maior parte do
edge e CORTAR whipsaw/custo/drawdown -> melhor metrica ajustada ao risco
(Sharpe) e menor maxDD, com ~metade da exposicao/turnover.

## Metodologia

```text
Base INALTERADA: TSM vol-targeted FC-II-005 (sinal = sign(retorno trailing
28d), size ~1/vol por perna, unit-gross, rebalance 5d, 6bps/perna). O filtro
e um flag opt-in (default OFF); comportamento/testes da base intactos.

Medida de forca de trend agregada (causal, reusa componentes do proprio TSM):
  strength_i[t] = |trailing_return_i[t]| / realized_vol_i[t]
  aggregate[t]  = media cross-sectional de strength_i[t] (skipna)
  (trailing e vol sao exatamente os ja computados pela base; trailing[t] usa
   preco ate t, vol usa shift(1).rolling -> aggregate[t] e causal em t.)

Gate de regime (binario, SEM knob):
  median[t] = aggregate.shift(1).rolling(2160h).median()   # 90d causal
  regime_on[t] = aggregate[t] >= median[t]
  Nos rebalances: pesos = pesos_base * regime_on (1 -> unit-gross base;
  0 -> FLAT). Mediana movel = corte canonico, nao tunavel.

Avaliacao: mesma janela dev 2023-06..2026-05, 20 symbols; comparar o TSM
COM filtro vs TSM base (FC-II-005 com funding, FC-II-008) nas metricas da
bateria de robustez. SEM veredito de promocao (dev).
```

## Celula primaria (LOCKED, exatamente 1)

```text
Filtro binario mediana-90d sobre a forca de trend agregada, acao OFF=FLAT.
Exatamente 1 variante primaria elegivel a OOS futura (busca limitada,
ADR-0031 regra 3). Nenhuma grade de percentis; nenhuma escolha de threshold
por desempenho no dev.
```

## Bateria de robustez (TODAS obrigatorias; ADR-0031 regra 5)

```text
1. Estabilidade entre os 3 subperiodos (o filtro ajuda em cada um, nao so no
   agregado?).
2. Sensibilidade a custo (o ganho sobrevive a custos maiores? breakeven).
3. Sensibilidade a funding (com/sem P&L de funding, FC-II-008).
4. Regimes de mercado (BTC up vs down).
5. Drawdown (maxDD melhora, nao so Sharpe?).
6. Simplicidade vs ganho (o ganho justifica a complexidade extra de 1 flag?).
7. Justificativa economica (coerente com a hipotese, nao ex-post).
8. Falso-positivo estatistico: o filtro precisa ajudar de forma CONSISTENTE;
   melhora concentrada em 1 subperiodo/regime = rejeicao (mesma logica das
   familias de info).
```

## Criterio de decisao (dev)

```text
CANDIDATO A OOS somente se: melhora Sharpe E reduz (ou nao piora) maxDD vs a
base, DE FORMA CONSISTENTE nos 3 subperiodos E em ambos os regimes de BTC, E
sobrevive a sensibilidade de custo/funding, E o ganho justifica a
complexidade. Caso contrario: REJEITADO, hipotese encerrada com resultado
negativo documentado, seguir para a Linha 2 (position sizing).
Nenhuma promocao aqui -- so em OOS intocado (pos-2026-05-31).
```

## Invariantes

```text
- Params fixos a priori; sem re-tune pos-resultado; sem promover secundario
  ex-post.
- Base TSM intacta (flag default OFF).
- Filtro causal (aggregate[t] e median shift(1) conhecidos em t).
- Dev != promocao; gate de promocao BLOQUEADO ate OOS novo.
- so pesquisa/paper, nada real.
```

## Fora de escopo

```text
- Sizing continuo por forca/vol (Linha 2).
- Multiplos thresholds / grade de percentis (viola busca limitada).
- Outras medidas de regime (breadth por sinal, dispersao, etc.) -- se esta
  fechar apetite, cada uma seria uma task propria, pre-registrada.
- Promocao / OOS (task/gate separado quando houver dado novo).
```
