# Family F (Open Interest) Information-Content Diagnostic

Research Phase II, TASK-ALT-002. Status: pure diagnostic, per `project_control/DECISIONS.md` ADR-0020. No strategy, no economic gate -- measures whether each feature shows a stable, non-trivial Spearman correlation with 24h forward returns.

Forward horizon: 24h. Rolling causal window: 2160h (90 days). Magnitude threshold: 0.03.

## Results

| Feature | Full rho | Full N | 2023-06_2024-05 | 2024-06_2025-05 | 2025-06_2026-05 | Sign consistent | Has information |
|---|---:|---:|---:|---:|---:|---|---|
| oi_delta | -0.0189 | 524488 | -0.0321 (n=174752) | -0.0202 (n=175016) | -0.0048 (n=174720) | True | False |
| oi_volume_ratio | -0.0147 | 524824 | -0.0162 (n=174996) | -0.0100 (n=175108) | -0.0093 (n=174720) | True | False |
| oi_percentile | 0.0014 | 428718 | 0.0117 (n=87526) | 0.0039 (n=167168) | 0.0134 (n=174024) | True | False |
| oi_acceleration | -0.0095 | 523692 | -0.0194 (n=174048) | -0.0086 (n=174924) | -0.0001 (n=174720) | True | False |
| oi_price_divergence | 0.0109 | 427638 | 0.0068 (n=86546) | -0.0025 (n=167092) | 0.0267 (n=174000) | False | False |

## Conclusao

**Nenhuma das 5 features cumpre o criterio pre-registrado -- e nenhuma
chega perto do limiar de 0,03 (a maior magnitude, `oi_delta`, fica a
0,0111 do limiar, mais de 2x a distancia do near-miss de
`funding_price_divergence` na Familia G).**

**Padrao diferente do observado na Familia G: aqui o achado interessante
e DECAIMENTO, nao estabilidade.** `oi_delta` (a feature mais forte)
mostra sinal negativo consistente nos 3 subperiodos -- mas a magnitude
decai monotonicamente: -0,0321 (2023-06/2024-05) -> -0,0202
(2024-06/2025-05) -> -0,0048 (2025-06/2026-05), praticamente zero no
periodo mais recente. `oi_acceleration` mostra o mesmo padrao de
decaimento (-0,0194 -> -0,0086 -> -0,0001). Isso e consistente com a
leitura de eficiencia de mercado ja registrada na Fase 1 de Payoff
Engineering (BTC/ETH, os symbols mais liquidos, tiveram os piores
desempenhos) -- se este efeito de OI já existiu de forma mais forte no
passado, o mercado parece ter incorporado essa informacao progressivamente,
reduzindo seu conteudo preditivo ao longo do periodo estudado.

**`oi_price_divergence` e a unica feature com INVERSAO de sinal**
(+0,0068 / -0,0025 / +0,0267) -- amostra tambem estavel em relacao a
`oi_percentile`, ambas reduzidas (~428k vs ~524k das demais) pelo
warmup duplo (rolling de 90 dias tanto no proprio OI quanto no retorno
de preco, mais acentuado para symbols que entraram no universo depois
de 2023-06, como ARBUSDT e SUIUSDT).

**Decisao final desta task:** nenhuma das 5 features de Open Interest
cumpre o criterio pre-registrado de "tem informacao." Per ADR-0020,
nenhum re-teste com limiar ajustado, nenhuma nova feature de OI, e
nenhum novo horizonte serao adicionados a esta task apos ver este
resultado. TASK-ALT-002 fecha como diagnostico concluido, sem strategy
design decorrente.

**Com G e F ambos sem informacao**, a Research Phase II ainda tem duas
linhas nao fechadas: o near-miss estavel de `funding_price_divergence`
(TASK-ALT-001, candidato a uma task futura independente) e Familia J
(Regime Detection, ainda nao iniciada). Familia H (Order Flow) continua
cara/adiada; Familia I (Liquidation Dynamics) continua BLOQUEADA por
falta de fonte de dados historica.
