# TASK-TSM-002 - Definicao e pre-registro: Linha 2 (position sizing) -- sizing por conviccao (forca do trend)

## Status

ACCEPTED (locked) - travado 2026-07-12 antes de qualquer implementacao. Sob
ADR-0031 (Programa de Melhoria do TSM), Linha 2. Resultado na janela de
desenvolvimento e SO desenvolvimento; promocao so em OOS intocado. Params
FIXOS a priori; sem re-tune pos-resultado; sem promover secundario ex-post.

## Revisao de literatura (grounding)

- A "regra TREND" (Baz et al., "Dissecting Investment Strategies";
  Hamill-Rattray-Van Hemert; Rohrbach et al.) dimensiona a posicao pela
  FORCA ESTATISTICA do trend em vez do sinal binario: reduz exposicao a
  sinais fracos, suaviza transicoes e corta turnover (~24% em estudos)
  SEM comprometer o desempenho. Evidencia de que um sinal de forca de trend
  (fitted-trend / retorno normalizado) DOMINA o sinal do sign(retorno) fora
  de amostra, com menor turnover.
- Coerente com o proprio projeto: o TSM base ja usa inverse-vol por perna,
  mas descarta a CONVICCAO (usa so o SINAL do trailing). A hipotese natural
  de sizing e reintroduzir a conviccao.
- Distincao de trabalho ja feito: FC-II-001 testou vol-targeting continuo
  (constante-vol) no funding carry -> nao bateu o gate; TASK-TSM-001 testou
  filtro de regime -> rejeitado. Esta task e DIFERENTE: nao muda a exposicao
  total (segue unit-gross) nem gateia; muda a REPARTICAO entre pernas,
  ponderando pela forca do trend de cada uma.

## Hipotese economica (clara)

O sinal binario sign(trailing) da peso cheio a trends fracos/ambiguos
(trailing perto de zero) igual a trends fortes, injetando ruido e whipsaw.
Ponderar cada perna pela forca do trend ajustada ao risco (trailing/vol)
aposta mais nas convicoes fortes e menos nas fracas -> menos turnover/ruido
e melhor metrica ajustada ao risco, mantendo a mesma exposicao bruta.

## Metodologia

```text
Base INALTERADA: TSM vol-targeted FC-II-005/008 (peso bruto = sign(trailing)
/ vol, unit-gross, rebalance 5d, funding P&L). Flag opt-in (default OFF);
comportamento/testes da base intactos.

Sizing por conviccao (SEM knob):
  peso_bruto_i = trailing_i / vol_i     (= sign(trailing_i)*|trailing_i|/vol_i
                                          = peso_base_i * |trailing_i|)
  depois unit-gross (soma dos |peso| = 1), identico a base.
  Long-only analogo: max(trailing_i, 0)/vol_i, unit-gross.
Ou seja: mesma direcao e mesma normalizacao da base; so re-pondera as pernas
pela magnitude do trailing (conviccao). Nenhuma constante de escala, nenhum
cap tunavel -> knob-free.

Avaliacao: janela dev 2023-06..2026-05, 20 symbols, com funding; comparar
base vs conviccao na bateria de robustez. SEM veredito de promocao (dev).
```

## Celula primaria (LOCKED, exatamente 1)

```text
Sizing por conviccao linear (peso ~ trailing/vol), unit-gross, acao em todas
as pernas. Exatamente 1 variante primaria elegivel a OOS futura (busca
limitada). Sem grade de funcoes de resposta (tanh/cap/expoentes); sem
escolha de forma por desempenho no dev. (Uma forma saturante estilo
y*exp(-y^2/4) fica FORA -- introduz constantes; seria task propria se esta
abrir apetite.)
```

## Bateria de robustez (TODAS obrigatorias; ADR-0031 regra 5)

```text
1. Estabilidade entre os 3 subperiodos.
2. Sensibilidade a custo (grade de bps; breakeven).
3. Sensibilidade a funding (com/sem).
4. Regimes de mercado (BTC up vs down).
5. Drawdown (maxDD melhora, nao so Sharpe?).
6. Simplicidade vs ganho (1 flag; ganho justifica?).
7. Justificativa economica (coerente com a hipotese, nao ex-post).
8. Falso-positivo: melhora precisa ser CONSISTENTE nos 3 subperiodos E em
   ambos os regimes de BTC; concentrada em 1 = rejeicao.
```

## Criterio de decisao (dev)

```text
CANDIDATO A OOS somente se: melhora Sharpe E reduz (ou nao piora) maxDD vs a
base, DE FORMA CONSISTENTE nos 3 subperiodos E em ambos os regimes de BTC, E
sobrevive a sensibilidade de custo/funding, E o ganho justifica a
complexidade. Caso contrario: REJEITADO, hipotese encerrada com resultado
negativo documentado, seguir para a Linha 3 (portfolio construction:
risk parity / ERC / HRP). Nenhuma promocao aqui -- so em OOS intocado.
```

## Invariantes

```text
- Params fixos a priori; sem re-tune; sem promover secundario ex-post.
- Base TSM intacta (flag default OFF); mesma exposicao bruta (unit-gross).
- Causal (usa trailing_r/vol_r ja causais da base; target = unico dado
  posterior).
- Dev != promocao; gate BLOQUEADO ate OOS novo.
- so pesquisa/paper, nada real.
```

## Fora de escopo

```text
- Funcoes de resposta saturantes / caps / expoentes (introduzem constantes).
- Portfolio construction entre pernas (risk parity/ERC/HRP) -- Linha 3.
- Vol-targeting de livro inteiro / constante-vol -- ja coberto por FC-II-001
  em espirito; se aplicavel ao TSM seria task propria.
- Promocao / OOS (gate separado quando houver dado novo).
```
