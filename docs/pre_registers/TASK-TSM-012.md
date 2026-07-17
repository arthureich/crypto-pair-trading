# TASK-TSM-012 - Definicao e pre-registro: generalizacao CROSS-ASSET-CLASS do TSM (indices/commodities/forex/ETFs)

## Status

ACCEPTED (locked) - travado 2026-07-17 antes de baixar/analisar dado. Sob
ADR-0031. VALIDACAO de generalizacao (prioridade #2 do usuario). Responde a
pergunta central: o edge e TREND-FOLLOWING (fenomeno multi-ativos) ou apenas
cripto? Horizontes economicos FIXOS (28d trend / 7d vol / 5d hold), ZERO re-tune.

## Revisao de literatura (grounding)

- Hurst, Ooi & Pedersen, "A Century of Evidence on Trend-Following Investing"
  (AQR): trend-following e positivo e consistente ao longo de >100 anos em
  ACOES, BONDS, COMMODITIES e MOEDAS -- fenomeno multi-ativos, nao especifico.
- Moskowitz, Ooi & Pedersen, "Time Series Momentum" (2012, JFE): TSM positivo
  em 58 instrumentos de 4 classes de ativos.
- Logo, se o TSM base (28d/5d, inverse-vol) e um instancia real desse fenomeno,
  deve dar Sharpe POSITIVO em indices, commodities, forex e ETFs -- nao so
  cripto. Se falhar fora de cripto, a leitura muda (edge pode ser
  cripto-especifico / de microestrutura de perp).

## Adaptacao de frequencia (decisao do usuario: preservar horizontes economicos)

```text
TradFi e DIARIO (mercados fecham); cripto e 24/7 horario. Rodar "o mesmo TSM"
cross-asset = preservar os HORIZONTES ECONOMICOS em barras DIARIAS:
  lookback = 28 barras (28 dias de pregao ~ 28d trend, = 672h/24)
  vol_window = 7 barras (7d, = 168h/24)
  hold = 5 barras (5d, = 120h/24)
Isto NAO e re-tune: sao os MESMOS horizontes (28/7/5 dias) do config horario,
so expressos em barras diarias. include_funding=False (TradFi nao tem funding de
perp). Anualizacao correta para hold de 5 pregoes: sqrt(252/5) (252 pregoes/ano).
```

## Metodologia

```text
Dado: Yahoo Finance chart API (diario, close), keyless, custo ZERO. Janela
2023-06-01..2026-05-31 (mesma do projeto). Universos POR CLASSE (calendarios
alinhados dentro da classe):
  - indices: ^GSPC ^NDX ^DJI ^RUT ^GDAXI ^FTSE ^N225 ^HSI ...
  - commodities: GC=F SI=F CL=F NG=F HG=F ZW=F ZC=F ZS=F PL=F ...
  - forex: EURUSD=X JPY=X GBPUSD=X AUDUSD=X USDCAD=X USDCHF=X NZDUSD=X ...
  - etfs: SPY QQQ IWM GLD SLV TLT IEF EFA EEM XLE XLF XLK ...
Coverage gate: >= 90% dos pregoes esperados na janela (feriados/calendarios
variam por classe -> gate um pouco mais brando que cripto).
Estrategia: TSM (lookback=28, vol_window=7, hold=5, include_funding=False),
long/short unit-gross, custo 6bps/perna. Por universo: TSM Sharpe (anualiz.
sqrt(252/5)) vs buy-and-hold equal-weight; maxDD; net; Sharpe por subperiodo.
Headline: em quantas das 4 classes o TSM tem Sharpe > 0 E > buy-and-hold.
```

## Celula primaria (LOCKED)

```text
TSM horizontes-fixos (28/7/5 dias) por classe de ativo. Sem re-tune; sem escolha
de instrumentos por desempenho (listas por classe + coverage gate). 4 classes.
```

## Criterio de decisao

```text
GENERALIZA MULTI-ATIVOS se o TSM tem Sharpe > 0 E > buy-and-hold na MAIORIA das
4 classes (>= 3/4), coerente com a literatura -> forte evidencia de que o edge e
trend-following genuino, nao cripto-especifico. Classes onde falha sao
documentadas e caracterizadas (nao escondidas). Se falhar amplamente fora de
cripto -> registrar que o edge pode ser cripto-especifico (resultado honesto,
igualmente valioso). Nao e promocao live (dados/execucao TradFi diferentes).
```

## Invariantes / Fora de escopo

```text
- Horizontes economicos FIXOS (28/7/5 dias); ZERO re-tune; instrumentos por
  regra objetiva (classe + coverage).
- Causal (mesma logica); custo ZERO (Yahoo publico); include_funding=False.
- Anualizacao diaria correta (sqrt(252/5)) -- nao a horaria.
- Nao e promocao live (execucao/custos/roll de futuros TradFi diferem; futuros
  continuos do Yahoo tem vies de roll -- ressalva documentada).
- FORA: otimizar horizontes por classe; modelar roll/carry de futuros; intraday
  TradFi; crypto-daily control (usuario optou por nao fazer agora).
```
