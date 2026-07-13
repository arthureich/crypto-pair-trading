# TASK-TSM-007 - Definicao e pre-registro: TSM volatility-targeted (managed-vol overlay)

## Status

ACCEPTED (locked) - travado 2026-07-13 antes de qualquer implementacao. Sob
ADR-0031 (Programa de Melhoria do TSM) -- refinamento adicional autorizado pelo
usuario (prioridade #4 risk overlay / #5 sizing: volatility targeting). Dev !=
promocao (OOS-gated). Params FIXOS a priori; sem re-tune; sem secundario ex-post.

## Contexto (Options-skew esta paid-gated)

O item #1 do usuario (aprofundar Options: skew/surface/term-structure) foi
investigado por reconnaissance: a API publica gratuita da Deribit fornece apenas
o snapshot ATUAL da cadeia (mark_iv por strike) + trades esparsos + o DVOL 30d
ATM (ja usado em ALT-011). Historico de 25d risk-reversal / butterfly / smile /
multi-tenor NAO e reconstruivel de dado gratis -- exige dado pago (Tardis/
Amberdata). Logo skew/surface e passo de DADO PAGO (item #6, decisao do usuario).
Seguindo a enfase do usuario ("a prioridade e fortalecer o TSM ate esgota-lo"),
esta task faz o refinamento gratis de TSM de maior suporte academico ainda nao
testado: volatility targeting.

## Revisao de literatura (grounding)

- Moreira & Muir (2017, JF, "Volatility-Managed Portfolios"): escalar exposicao
  pelo inverso da variancia recente gera alfa porque a vol e menos persistente
  que o retorno esperado.
- Man Group; Research Affiliates; AlphaArchitect: vol targeting melhora Sharpe
  (ex.: 0,40 -> 0,48-0,51 em acoes), reduz max drawdown e a cauda (vol-of-vol),
  alavancando em baixa vol e reduzindo em alta vol.
- CAVEAT HONESTO divulgado a priori (Man Group): o beneficio e MAIOR onde a vol
  e persistente e negativamente relacionada ao retorno (acoes/credito); para
  TREND puro tende a ser MUDO (o trend ja e parcialmente vol-aware). FC-II-001
  testou vol-target no funding carry (nao bateu o gate). Espera-se, portanto,
  possivelmente NEUTRO -- e um teste honesto, nao uma aposta de melhoria certa.

## Hipotese economica (clara)

Escalar a exposicao do livro TSM inversamente a sua propria vol realizada
recente (alvo de vol ~constante) deve estabilizar o risco e MELHORAR metricas
ajustadas ao risco (Sharpe) e o drawdown, sem depender de prever retorno.

## Metodologia

```text
Base INALTERADA: retornos por rebalance do TSM FC-II-008 (com funding).
Overlay (SEM knob de alavancagem):
  r        = retorno net por rebalance do TSM base.
  sigma_t  = r.shift(1).rolling(W).std()               # vol realizada causal
  target_t = sigma.shift(1).expanding().mean()          # alvo = vol media causal
             (-> escala media ~1; NAO adiciona alavancagem liquida persistente)
  scale_t  = clip(target_t / sigma_t, 0, CAP)           # CAP=3.0 (limite de
             sanidade de risco a priori, NAO tunado; divulgado)
  r_scaled_t = scale_t * r_t   (P&L e custo escalam juntos com o tamanho)
  warmup (sigma indefinido) -> scale=1 (inalterado).
W = 12 rebalances (~60d a 5d) -- janela de vol padrao da literatura, FIXA a
priori. Avaliacao: dev 2023-06..2026-05; comparar scaled vs base na bateria.
```

## Celula primaria (LOCKED, exatamente 1)

```text
Overlay vol-target inverse-vol-para-alvo, W=12, CAP=3.0, alvo=media expanding.
Exatamente 1 variante. Sem grade de W/CAP/alvo escolhida por desempenho.
```

## Bateria de robustez (TODAS; padrao ADR-0031)

```text
1. Estabilidade nos 3 subperiodos.
2. Sensibilidade a custo (grade).
3. Sensibilidade a funding (com/sem).
4. Regimes de mercado (BTC up vs down).
5. Drawdown (o argumento central -- deve melhorar).
6. Simplicidade vs ganho (1 overlay; alavancagem media ~1).
7. Justificativa economica (managed-vol, coerente).
8. Falso-positivo: ganho CONSISTENTE nos 3 subperiodos.
```

## Criterio de decisao (dev)

```text
CANDIDATO A OOS somente se: melhora Sharpe E reduz (ou nao piora) maxDD vs base,
CONSISTENTE nos 3 subperiodos E ambos regimes BTC, sobrevive custo/funding.
Caso contrario: REJEITADO/NEUTRO documentado (esperado se o beneficio for mudo
para trend), seguir. Sem promocao; gate BLOQUEADO ate OOS novo.
```

## Invariantes / Fora de escopo

```text
- Params fixos a priori (W=12, CAP=3.0); sem re-tune; sem secundario ex-post.
- Base TSM intacta (overlay opera sobre o stream de retorno; nao muda o sinal).
- Causal (sigma e target via shift(1)); dev != promocao; OOS-gated.
- FORA: Kelly (exige edge estimado); kill switches / dynamic leverage
  discricionarios (alto risco de tuning); skew/surface (paid, item #6);
  acao real.
```
