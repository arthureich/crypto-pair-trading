# Family H (Order Flow / Book Depth) Information-Content Diagnostic

Research Phase II, TASK-ALT-007. Status: pure diagnostic, per `project_control/DECISIONS.md` ADR-0025. No strategy, no economic gate -- measures whether each feature shows a stable, non-trivial Spearman correlation with 24h forward returns.

Forward horizon: 24h. Rolling causal window: 2160h (90 days). Magnitude threshold: 0.03.

## Results

| Feature | Full rho | Full N | 2023-06_2024-05 | 2024-06_2025-05 | 2025-06_2026-05 | Sign consistent | Has information |
|---|---:|---:|---:|---:|---:|---|---|
| book_imbalance_1pct | -0.0176 | 524398 | -0.0308 (n=175084) | -0.0063 (n=174740) | -0.0060 (n=174574) | True | False |
| book_imbalance_5pct | -0.0025 | 524398 | 0.0017 (n=175084) | -0.0225 (n=174740) | 0.0207 (n=174574) | False | False |
| depth_concentration | -0.0108 | 524398 | -0.0177 (n=175084) | -0.0166 (n=174740) | -0.0008 (n=174574) | True | False |
| depth_change_24h | -0.0065 | 522856 | -0.0174 (n=174148) | -0.0185 (n=174280) | 0.0136 (n=174428) | False | False |
| imbalance_price_divergence | 0.0208 | 392611 | 0.0131 (n=105072) | 0.0215 (n=128900) | 0.0236 (n=158639) | True | False |

## Conclusao

**Nenhuma das 5 features cumpre o criterio pre-registrado.** Isto fecha
o ultimo avenue originalmente planejado da Research Phase II (Familias
F, G, H, J todas executadas; I permanece formalmente bloqueada).

**Padrao 1 -- decaimento (repete o achado de `oi_delta`/`oi_acceleration`
na Familia F):** `book_imbalance_1pct` e `depth_concentration` mostram
sinal consistente nos 3 subperiodos, mas magnitude DECAINDO ao longo do
tempo -- `book_imbalance_1pct`: -0,0308 (2023-06/2024-05) -> -0,0063
(2024-06/2025-05) -> -0,0060 (2025-06/2026-05); `depth_concentration`:
-0,0177 -> -0,0166 -> -0,0008, praticamente zero no periodo mais
recente. Terceira vez nesta fase (apos `oi_delta`/`oi_acceleration`) que
um sinal de estrutura de mercado decai para perto de zero no periodo
mais recente -- reforca a leitura de eficiencia de mercado crescente ja
registrada na Fase 1 de Payoff Engineering e na Familia F.

**Padrao 2 -- crescimento (novo, distinto de tudo visto antes na
Fase II):** `imbalance_price_divergence` e a UNICA feature com sinal
positivo estavel E CRESCENTE: 0,0131 -> 0,0215 -> 0,0236, quase
dobrando entre o primeiro e o ultimo subperiodo. E o near-miss mais
proximo desta task (0,0208 full-sample, a 0,0092 do limiar de 0,03),
mas com uma trajetoria OPOSTA aos near-misses/padroes anteriores desta
fase (o de `funding_price_divergence` foi estavel; os de `oi_delta`/
`book_imbalance_1pct` decaem). Se este crescimento continuar, uma
observacao futura poderia cruzar o limiar organicamente -- mas isso
NAO autoriza rebaixar o limiar agora nem redesenhar a feature para
"ajudar" o proximo ponto.

**Decisao final desta task:** nenhuma das 5 features de book depth
cumpre o criterio de "tem informacao." Per ADR-0025, nenhum re-teste
com limiar ajustado, nenhuma nova feature, e nenhum novo horizonte
serao adicionados a esta task apos ver este resultado. TASK-ALT-007
fecha como diagnostico concluido, sem strategy design decorrente.
`imbalance_price_divergence` fica registrado como candidato legitimo
para uma futura task de validacao em novo periodo -- NAO um re-teste
no mesmo dado, mesma disciplina ja aplicada a `funding_price_divergence`
(`TASK-ALT-001`/`TASK-ALT-005`).

**Estado final da Research Phase II apos esta task:** G, F, e H fecham
sem informacao direcional; J encontrou informacao real de
regime/volatilidade, mas seu primeiro uso operacional (TASK-ALT-004)
nao ajudou a TSREV. Um segundo uso operacional (TASK-ALT-006) e a
retomada do near-miss de G (TASK-ALT-005, ja fechado NAO_PROMOVE)
seguem o padrao ja estabelecido. Familia I permanece formalmente
bloqueada por falta de fonte de dados historica.
