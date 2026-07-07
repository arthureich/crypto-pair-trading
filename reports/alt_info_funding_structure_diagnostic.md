# Family G (Funding Structure) Information-Content Diagnostic

Research Phase II, TASK-ALT-001. Status: pure diagnostic, per `project_control/DECISIONS.md` ADR-0019. No strategy, no economic gate -- measures whether each feature shows a stable, non-trivial Spearman correlation with 24h forward returns.

Forward horizon: 24h. Rolling causal window: 2160h (90 days). Magnitude threshold: 0.03.

## Results

| Feature | Full rho | Full N | 2023-06_2024-05 | 2024-06_2025-05 | 2025-06_2026-05 | Sign consistent | Has information |
|---|---:|---:|---:|---:|---:|---|---|
| funding_extreme | -0.0050 | 482400 | 0.0244 (n=132480) | 0.0084 (n=175200) | -0.0414 (n=174720) | False | False |
| funding_reversal | -0.0044 | 525120 | -0.0114 (n=175200) | 0.0118 (n=175200) | -0.0135 (n=174720) | False | False |
| funding_acceleration | 0.0064 | 524640 | -0.0161 (n=174720) | 0.0094 (n=175200) | 0.0238 (n=174720) | False | False |
| funding_price_divergence | 0.0248 | 481920 | 0.0276 (n=132000) | 0.0230 (n=175200) | 0.0239 (n=174720) | True | False |

## Conclusao

**3 de 4 features nao mostram informacao, e por um motivo claro: o sinal
da correlacao muda entre subperiodos.** `funding_extreme` vai de +0,0244
(2023-06/2024-05) a -0,0414 (2025-06/2026-05) -- literalmente inverte de
direcao. `funding_reversal` e `funding_acceleration` mostram o mesmo
padrao de instabilidade. Isso e exatamente o tipo de "efeito espurio de
amostra completa" que o criterio de consistencia de sinal em 3
subperiodos foi desenhado para filtrar -- nenhuma dessas 3 features
seria um preditor confiavel, mesmo que a magnitude na amostra completa
parecesse promissora isoladamente.

**`funding_price_divergence` e o unico caso interessante: SINAL
ESTAVEL, magnitude quase no limiar.** rho positivo e notavelmente
consistente nos 3 subperiodos (0,0276 / 0,0230 / 0,0239 -- uma faixa
estreita de apenas 0,0046) e na amostra completa (0,0248) -- mas fica a
0,0052 do limiar pre-registrado de 0,03. Por disciplina (mesma regra
aplicada ao near-miss do Funding Carry incremental, TASK-FUND-003, que
faltou 0,0096 do gate de 1,10), este resultado e classificado
estritamente como **SEM_INFORMACAO** per o criterio fixado -- nao ha
ajuste do limiar apos ver o numero.

**Diferenca importante em relacao aos near-misses anteriores desta
sessao:** o near-miss do Funding Carry era de UM UNICO numero (profit
factor no periodo OOS). Aqui, a estabilidade em 3 janelas
INDEPENDENTES E NAO-SOBREPOSTAS torna o achado mais interessante --
nao e um acaso de uma amostra especifica, e um padrao que se repete
com magnitude quase identica em tres periodos de ~12 meses cada. Isso
NAO decide nada por si (o criterio pre-registrado e claro e nao muda),
mas e uma pista legitima e bem fundamentada para uma FUTURA task
independente (nao um re-teste desta), caso o usuario queira investigar
`funding_price_divergence` com um limiar diferente, um horizonte
diferente, ou como uma das features candidatas de uma Familia F futura
combinada com Open Interest.

**Decisao final desta task:** nenhuma das 4 features de Funding
Structure cumpre o criterio pre-registrado de "tem informacao." Per
ADR-0019, nenhum re-teste com limiar ajustado, nenhuma nova feature de
funding, e nenhum novo horizonte serao adicionados a esta task apos ver
este resultado. TASK-ALT-001 fecha como diagnostico concluido, sem
strategy design decorrente. Familia F (Open Interest) e a proxima na
sequencia acordada.
