# TASK-FC-II-002 - Definicao e pre-registro: Diagnostico de Conteudo Informacional da Basis Spot-Futures, com teste de informacao INCREMENTAL sobre o funding

## Status

ACCEPTED (locked) - travado em 2026-07-10 antes de qualquer computo do
resultado. Sob a fase "Funding Iteration 2" (ADR-0027), que ja listou
basis como candidata de Trilha B. Diagnostico de conteudo informacional
(estilo Research Phase II / ADR-0019), NAO uma estrategia -- sem gate
economico. Resultado e "tem informacao (incremental)" ou "nao tem".

## Motivacao e reconnaissance

Reconnaissance de dado (2026-07-10): klines spot dos 20 symbols existem
em `data.binance.vision` para todo o periodo (40/40 probes 200, ~24MB o
download inteiro). POReM nao e necessario baixar: os bars de futuros do
sprint7 ja trazem `premium_close` (indice de premio = basis instantanea
perp-vs-indice) e `index_close`/`mark_close`, 100% populados.

Prior: basis e funding sao parentes (o funding e o mecanismo que amarra
o perp ao spot). Medido: corr(premium_close, funding_rate_asof) = 0,568
no painel -- correlacionados, mas ~68% da variancia do premium NAO e
explicada pelo funding. A Familia G (funding structure / funding_price_
divergence) ja deu SEM_INFORMACAO, o que rebaixa o prior; mas a basis
instantanea nao e identica ao funding liquidado (que tem caps/clamps e
agenda), entao pode carregar informacao propria.

## Pergunta central (o que distingue esta task de reconfirmar o carry)

Nao basta "basis correlaciona com retorno futuro" (provavelmente sim, via
carry ja conhecido). A pergunta pre-registrada e:

> A basis carrega informacao sobre o retorno futuro 24h ALEM da que o
> funding_rate_asof ja carrega?

Operacionalizado por correlacao de Spearman PARCIAL, controlando por
funding. Uma feature so "conta" se sobreviver ao controle.

## Metodologia (reusa ADR-0019 + camada parcial)

```text
Motor: src/research/info_content.py (evaluate_information_content) para a
parte padrao; + partial_spearman_rho (feature, target | control) para a
camada incremental.

Target: forward_return_24h[t] = log_price[t+24h] - log_price[t] (mesmo
horizonte da Fase II, nao re-escolhido).

Control (para a camada incremental): funding_rate_asof[t] (causal, ja
as-of).

3 subperiodos cronologicos NAO-sobrepostos (2023-06/2024-05, 2024-06/
2025-05, 2025-06/2026-05) -- os MESMOS de TASK-ALT-001/002/003, nao
reparticionados.

Criterio "tem informacao" (padrao, identico a Fase II):
  |rho_amostra_completa| >= 0,03 E sinal consistente nos 3 subperiodos.

Criterio "tem informacao INCREMENTAL sobre o funding" (o que decide esta
task):
  |rho_parcial(feature, fwd_ret | funding)_amostra_completa| >= 0,03
  E sinal do rho_parcial consistente nos 3 subperiodos.
Uma feature so e considerada portadora de sinal novo se passar no
criterio INCREMENTAL. Passar so no padrao (mas nao no parcial) e lido
como "apenas re-expressa o carry ja conhecido".
```

## Features candidatas (LOCKED, 4, causais, formalizadas antes do resultado)

```text
1. basis_level[t]      = premium_close[t]
   (premio instantaneo perp-vs-indice; conhecido em t, causal.)
2. basis_zscore[t]     = (premium_close[t] - m[t]) / s[t], onde
   m,s = shift(1).rolling(2160h) mean/std do premium_close do symbol
   (mesma janela causal de 90d da Fase II).
3. basis_change_24h[t] = premium_close[t] - premium_close[t-24]
   (momentum da basis nas ultimas 24h).
4. basis_excess_funding[t] = premium_close[t] - funding_rate_asof[t]
   (basis instantanea MENOS funding liquidado -- a feature mais
   diretamente "incremental": captura quando a basis diverge do que o
   funding settlou.)

Todas causais: features 2 e 3 usam shift(1)/lag antes de qualquer
janela; 1 e 4 usam apenas valores conhecidos em t. O TARGET e o unico
uso de dado posterior a t.
```

## Universo e amostra

```text
20 symbols do dataset normalizado sprint7 (2023-06/2026-05). Painel
empilhado (pooled), mesmo padrao de TASK-ALT-001/002/003.
```

## Invariantes obrigatorios

```text
- Toda feature causal (shift(1) antes de rolling nas features 2 e 3).
- O TARGET (retorno futuro 24h) e o unico dado posterior a t.
- 3 subperiodos e limiar 0,03 identicos a Fase II -- nao reparticionados
  nem re-tunados.
- Sem gate economico, SignalIntent, execucao, ledger, ou qualquer acao
  real -- diagnostico puro.
- Sem novo download (usa premium_close/funding_rate_asof/log_price ja
  presentes). O reconnaissance de spot fica registrado como fallback nao
  usado.
- Uma feature so promove a "candidata a estrategia futura" se passar no
  criterio INCREMENTAL (parcial sobre funding).
```

## Fora de escopo

```text
- Desenhar estrategia sobre uma feature que passe (task separada,
  pre-registrada).
- Outras fontes novas (options/on-chain/cross-exchange).
- Reparticionar subperiodos, ajustar 0,03, mutual information ou
  estimadores nao-lineares.
- Horizontes alem de 24h (um horizonte curto de microestrutura fica
  como candidato de FUTURA task, nao testado aqui).
- Baixar spot klines (desnecessario; premium index ja presente).
```
