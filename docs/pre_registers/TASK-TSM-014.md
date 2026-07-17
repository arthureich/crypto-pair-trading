# TASK-TSM-014 - Definicao e pre-registro: ROBUSTEZ TEMPORAL do TSM base (janelas fixas a priori)

## Status

ACCEPTED (locked) - travado 2026-07-17 ANTES de computar qualquer metrica
temporal. Sob ADR-0031. Prioridade #4 do programa de validacao do usuario
("robustez temporal; janelas independentes, NUNCA escolhidas apos ver
resultados"). TAMBEM preenche a lacuna de cobertura sinalizada em TSM-013
(sub-periodo salvo so em 1/7 universos cripto).

## Objetivo

Caracterizar se o edge do TSM base e consistente NO TEMPO (nao concentrado numa
janela quente) e robusto a QUANDO se mede. DESCRITIVO -- reconstroi os streams de
PnL por rebalance do TSM base (params FIXOS FC-II-008, include_funding=True, zero
re-tune) a partir de barras JA CACHEADAS (offline), e computa metricas temporais
com janelas DECLARADAS A PRIORI. Nenhuma promocao, nenhuma mudanca de parametro.

## Fonte de dados (LOCKED - so cache; NENHUM download novo)

```text
- Original-20 (referencia mais profunda): normalized/
  sprint7_binance_usdm_202306_202605_bars.csv.gz (20 symbols).
- 6 universos tematicos: normalized/tsm_multiverse_202306_202605_bars.csv.gz
  (reusa UNIVERSES + coverage gate 0.95 de run_tsm_multiverse.py).
Total: 7 universos cripto. TradFi (out-of-domain) NAO e re-rodado aqui.
```

## Janelas e parametros FIXOS A PRIORI (locked antes de ver resultados)

```text
- Cadencia de rebalance = 5 dias (hold_hours=120) -> ~73 rebalances/ano
  (365/5). Anualizacao _ANN = sqrt(24*365/120) (a mesma do projeto).
- Sub-periodos FIXOS (as janelas de longa data do projeto, ADR-0019):
  2023-06-01..2024-05-31, 2024-06-01..2025-05-31, 2025-06-01..2026-05-31.
- Janelas rolantes DERIVADAS DA CADENCIA (nao ajustadas a resultado):
  W6 = 37 rebalances (~6 meses), W12 = 73 rebalances (~12 meses), passo 1.
```

## Metodologia / analises (LOCKED)

```text
Para cada um dos 7 universos cripto, reconstruir o stream de PnL/rebalance do
TSM base (TsmTrendConfig(include_funding=True)) offline; entao:

(A) SUB-PERIODO x UNIVERSO (backfill da lacuna de TSM-013 -> 7/7):
    Sharpe base por (universo x 3 sub-periodos fixos). Reportar, por sub-periodo:
    media cross-universo, dispersao (sd), fracao de universos positivos;
    identificar o sub-periodo sistematicamente mais fraco; SINALIZAR qualquer
    par (universo, sub-periodo) com Sharpe negativo.

(B) ROLLING-WINDOW SHARPE (W6=37, W12=73; passo 1), por universo:
    fracao de janelas com Sharpe>0, min/mediana/max do Sharpe rolante, e a maior
    sequencia consecutiva de janelas com Sharpe<0 (pior "trecho morto"). Pooled:
    fracao de TODAS as janelas rolantes positivas entre os 7 universos.

(C) DURACAO DE DRAWDOWN (time-underwater), por universo:
    sobre a curva de equity (cumsum do PnL): maior drawdown em DURACAO (maior
    pico-a-recuperacao, em rebalances -> dias x5) e fracao do tempo underwater.
```

## Criterio de decisao

```text
DESCRITIVO -- sem veredito de promocao. Declara-se ROBUSTEZ TEMPORAL se:
  (a) cada universo e positivo em >= 2/3 dos sub-periodos fixos, sem sub-periodo
      catastrofico (Sharpe < -0.5 em algum universo seria um alerta), E
  (b) a MAIORIA das janelas rolantes (pooled) tem Sharpe>0, E
  (c) os drawdowns se recuperam (duracao maxima limitada, nao permanente).
Se falhar em qualquer eixo -> documentar HONESTAMENTE quando/onde o edge
enfraquece (ex.: um sub-periodo fraco comum, um trecho morto longo). Sem
selecao ex-post de janela; sem mudanca de parametro; sem promocao live.
```

## Invariantes / Fora de escopo

```text
- Params FIXOS FC-II-008 (include_funding=True); ZERO re-tune.
- Janelas (sub-periodos + W6/W12) DECLARADAS A PRIORI; W6/W12 derivadas da
  cadencia (5d), NAO ajustadas a resultado.
- Offline: so barras cacheadas; NENHUM download novo.
- So cripto (in-domain). TradFi reportado a parte (TSM-012), NAO re-rodado.
- Causal (mesma logica do TSM base). Descritivo: sem novo teste de hipotese
  formal, sem promocao, sem live.
- FORA: escolher janelas apos ver Sharpe; otimizar cadencia; multipla-correcao
  formal (n insuf.); re-baixar dados; adicionar universos novos (isso e #3).
```
