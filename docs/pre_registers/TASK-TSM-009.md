# TASK-TSM-009 - Definicao e pre-registro: teste de generalizacao OUT-OF-UNIVERSE do TSM combinado

## Nota de execucao (transparencia, 2026-07-13)

Dos 15 candidatos pre-declarados, 5 (SNXUSDT, XLMUSDT, EOSUSDT, XTZUSDT e o
parcial MKRUSDT) NAO baixaram neste ambiente por resets de conexao transitorios
da data.binance.vision (WinError 10054) -- foram descartados por DISPONIBILIDADE
DE DADO, nao por desempenho (nenhum resultado foi visto antes do corte). A
universe realizada = 10 symbols com klines+funding completos: NEAR, FIL, AAVE,
ALGO, ICP, SAND, MANA, AXS, GRT, CRV (todos passam o coverage gate de 95%).
Como a selecao foi por completude de download (ortogonal a performance), nao ha
vies de resultado. So klines + fundingRate foram baixados (unico que o TSM usa;
mark/index/premium desnecessarios).

## Status

ACCEPTED (locked) - travado 2026-07-13 antes de baixar/analisar qualquer dado.
Sob ADR-0031. NAO e refinamento (TSM convergiu) -- e VALIDACAO de generalizacao:
o candidato lider combinado (ERC + vol-targeting, TASK-TSM-008), com config
FIXA do dev na universe original de 20 perps, rodado INALTERADO numa universe
DIFERENTE de perps. Sem re-tune, sem otimizacao -- teste de robustez de breadth.

## Motivacao (por que e alto valor e sem overfit)

O usuario apontou que refinar mais o TSM na mesma janela dev so aumenta risco de
falso-positivo; o ganho de informacao vem de dado NOVO. Um teste out-of-universe
(mesma logica, symbols diferentes) e uma forma de OOS que NAO adiciona graus de
liberdade ao dev: se o edge do TSM combinado se mantem numa universe de alts
diferente, e forte evidencia de que e real e nao um artefato dos 20 symbols
originais. Se some, o edge pode ser especifico da universe original.

## Hipotese

O edge do TSM combinado (trend vol-targeted + ERC + vol-target overlay) e uma
propriedade GERAL de perps cripto liquidos, nao dos 20 symbols originais. Logo,
rodado numa universe diferente de alts liquidos, deve bater o buy-and-hold
(Sharpe, drawdown) de forma consistente -- ~na mesma ordem de grandeza do dev.

## Metodologia

```text
Universe NOVA (candidatos pre-declarados, USDM perps liquidos NAO nos 20
originais; long history): NEAR, FIL, AAVE, ALGO, ICP, SAND, MANA, AXS, GRT,
CRV, MKR, SNX, XLM, EOS, XTZ (15 candidatos). Filtro OBJETIVO (nao cherry-pick):
manter so os que tem cobertura >= 95% das barras horarias esperadas em
2023-06..2026-05 (mesma janela do dev); symbols com historico insuficiente sao
descartados pelo filtro, nao por escolha.
Pipeline: reusa historical_dataset (build_archive_plan/download_archives/
normalize_archive_plan) -- MESMA normalizacao do sprint7 (log_price,
funding_rate_asof, etc.). Dado publico Binance, custo ZERO.
Estrategia: config FIXA = TSM combinado (include_funding=True, portfolio_erc=True)
+ overlay apply_vol_target no stream de retorno. IDENTICA a TASK-TSM-008. Sem
qualquer parametro re-ajustado para a nova universe.
Comparacao: combinado vs base TSM vs buy-and-hold equal-weight, na universe nova,
janela 2023-06..2026-05. Metricas: Sharpe, maxDD, net; robustez por 3
subperiodos.
```

## Celula primaria (LOCKED, exatamente 1)

```text
TSM combinado (config TASK-TSM-008 inalterada) na universe nova filtrada por
cobertura. 1 teste. Sem grade; sem re-tune; sem escolha de symbols por
desempenho (o filtro de cobertura e o unico criterio de inclusao).
```

## Criterio de decisao

```text
GENERALIZA (edge real, robusto) se: na universe nova, o combinado tem Sharpe >
buy-and-hold E net > 0 E consistente nos 3 subperiodos, em ordem de grandeza
comparavel ao dev (Sharpe ~1). 
NAO GENERALIZA (edge pode ser especifico da universe original / mais fragil do
que parecia) se: o combinado nao bate o buy-and-hold ou e inconsistente na nova
universe -> registrar honestamente; enfraquece a confianca no candidato.
Isto NAO promove nem rejeita para live (dev-window de outra universe, nao OOS
temporal); e evidencia de BREADTH que informa a confianca no candidato OOS.
```

## Invariantes / Fora de escopo

```text
- Config do combinado FIXA (herdada de TASK-TSM-008); ZERO re-tune na nova
  universe; symbols filtrados so por cobertura objetiva.
- Causal (mesma logica ja testada); custo ZERO (Binance public).
- NAO e promocao live (e validacao de generalizacao cross-universe).
- FORA: otimizar params/universe; adicionar novos sinais; COIN-M (poderia ser
  outro teste); acao real.
```
