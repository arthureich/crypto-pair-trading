# TASK-TSM-013 - Definicao e pre-registro: CARACTERIZACAO ESTATISTICA da robustez do TSM (agregacao cross-universo)

## Status

ACCEPTED (locked) - travado 2026-07-17 ANTES de computar qualquer estatistica
agregada. Sob ADR-0031. Prioridade #5 do programa de validacao do usuario
("caracterizacao estatistica": media/std/CI/dispersao de metricas entre
universos; identificar onde a estrategia degrada). E uma SINTESE DESCRITIVA de
resultados JA COMMITADOS (TSM-008/009/010/011/012) -- NAO um novo teste de
hipotese, NAO uma nova promocao, NAO um novo backtest.

## Objetivo

Transformar o conjunto de validacoes ja rodadas (base TSM com params FIXOS
FC-II-008, zero re-tune) numa UNICA declaracao estatistica de robustez: qual e
a distribuicao do Sharpe (e maxDD, net) do TSM base entre universos cripto, com
que intervalo de confianca, com que taxa de positividade, e ONDE degrada.
Reporta TradFi (fora de dominio) SEPARADAMENTE (nunca pooled com cripto).

## Fonte de dados (LOCKED - so artefatos ja committados; NENHUM backtest novo)

```text
Lidos de data/research/binance_public/cost_pilot/*.json (ja no repo):
- tsm_bybit_crossexchange.json -> universo original-20 (Binance), campos
  headline{sharpe,max_dd,mean_turnover,net,baseline_sharpe} + sub_period_sharpe.
  (Bybit = mesmo universo, outra venue -> usado so como nota de robustez de
  venue, NAO como observacao de universo separada.)
- tsm_multiverse.json -> 6 universos tematicos (defi, gaming, large_cap,
  mid_alt_l1, mid_tier_ref, old_guard), cada um base/buy_hold/combined
  {sharpe,max_dd,net,n}.
- tsm_out_of_universe.json -> sub_periods do mid_tier_ref (dado temporal extra;
  o Sharpe de universo vem do multiverse, NAO duplicado).
- tsm_combined_dev.json -> combined do original-20 (para o delta overlay).
- tsm_asset_classes.json -> 4 classes TradFi (indices/commodities/forex/etfs),
  cada uma tsm/buy_hold{sharpe,max_dd,net,n} + sub_period_tsm.
```

## Populacoes (LOCKED)

```text
Populacao A -- CRIPTO (IN-DOMAIN), n=7 universos distintos, TSM base fixo:
  original-20, defi, gaming, large_cap, mid_alt_l1, mid_tier_ref, old_guard.
  (mid_tier_ref == out_of_universe -> contado UMA vez.)
Populacao B -- TradFi (OUT-OF-DOMAIN), n=4 classes: indices, commodities,
  forex, etfs. Reportada SEPARADAMENTE; NUNCA pooled com A.
```

## Estatisticas a computar (LOCKED - definidas antes de ver os agregados)

```text
Para a Populacao A (cripto), TSM base:
1. Por metrica em {Sharpe, maxDD, net}: n, media, desvio (amostral, ddof=1),
   min, max, mediana.
2. Sharpe: fracao > 0; fracao > buy-hold do proprio universo.
3. IC 95% da MEDIA do Sharpe por bootstrap percentil (numpy default_rng(seed=0),
   10000 reamostragens com reposicao) -- semente FIXA -> reproduzivel. Reportar
   tambem o IC 95% t-Student como cross-check (n pequeno).
4. Mapa de degradacao: ordenar universos por Sharpe; nomear melhor e pior;
   reportar o spread (max-min) e o coeficiente de variacao.

Overlay (combined ERC+vol-target menos base), universos onde combined existe
(n=7: original-20 + 6 tematicos):
5. delta Sharpe (combined-base): media, desvio, min, max; fracao combined>base;
   fracao combined maxDD < base maxDD. (Prior de TSM-009/010: overlay ajuda so
   na minoria -> quantificar honestamente.)

Temporal (sub-periodos fixos 2023-06/2024-05, 2024-06/2025-05, 2025-06/2026-05)
-- SO onde ha dado (original-20, mid_tier_ref, e as 4 classes TradFi):
6. Por sub-periodo: media e dispersao do Sharpe base entre as runs disponiveis;
   identificar o sub-periodo sistematicamente mais fraco. Nota HONESTA de
   cobertura (5 dos 7 universos cripto tematicos NAO tem sub-periodo salvo).

Para a Populacao B (TradFi), TSM base, SEPARADAMENTE:
7. Mesmas estatisticas descritivas de {Sharpe, maxDD, net}; fracao>0; fracao
   >buy-hold (ja sabido =0/4). Contexto: limite documentado (TSM-012).
```

## Criterio de decisao

```text
NENHUM veredito de promocao. Isto e caracterizacao DESCRITIVA. A saida e uma
frase de robustez: "TSM base = Sharpe medio X (IC95 [a,b]) em n=7 universos
cripto, positivo em k/7, > buy-hold em m/7; degrada mais em <universo>; overlay
ajuda em j/7; TradFi fora-de-dominio reportado a parte (0/4)."
Se a media for positiva com IC que exclui zero E positividade alta -> declara-se
robustez estatistica IN-DOMAIN (cripto). Se o IC cruzar zero -> honestamente
"nao conclusivo". Sem mudanca de parametro; sem promocao ex-post.
```

## Invariantes / Fora de escopo

```text
- So le JSON ja committado; NAO roda backtest novo; NAO altera params.
- Cripto (A) e TradFi (B) NUNCA pooled.
- Bootstrap com semente FIXA (default_rng(0)); reproduzivel.
- n pequeno (7) -> bootstrap + t reportados juntos; sem sobre-afirmar precisao.
- Descritivo: sem novo teste de hipotese, sem promocao, sem live.
- FORA: re-rodar universos; adicionar universos novos (isso e prioridade #3,
  task separada); modelar significancia formal / correcao multipla (n insuf.).
```
