# Funding Price Divergence New-OOS Diagnostic

TASK-ALT-005 / ADR-0023. Pure information-content validation on genuine new OOS data. No strategy, no economic gate, no SignalIntent, no Execution/Ledger/Recovery/ML/live change.

Window: 2026-06 through 2026-07 (end exclusive).
Symbols: 20. Archives planned: 100. Checksums verified: True.

## Decision

`NAO_PROMOVE`

## Data Gate

Status: `PASS`
Reasons: ()
Valid observations: 13920

## Information Result

Full-sample rho: -0.118324
Full-sample N: 13920

| Period | Rho | N |
|---|---:|---:|
| 2026-06 | -0.118324 | 13920 |

## Conclusao

**A pista nao se replicou -- pior, o sinal inverteu com forca.**
`TASK-ALT-001` encontrou `funding_price_divergence` positivamente
correlacionada e estavel em 3 subperiodos independentes (+0,0276,
+0,0230, +0,0239 -- uma faixa estreita de apenas 0,0046). No novo OOS
genuinamente inedito (2026-06, nunca usado em nenhuma decisao anterior
deste projeto), o rho e **-0,118324** -- nao apenas abaixo do limiar de
0,03, mas com o sinal invertido e uma magnitude ~4x maior que o
full-sample original.

**Isto e exatamente o resultado que a disciplina de "novo OOS
genuino" foi desenhada para revelar.** Se este teste tivesse reusado o
mesmo periodo 2023-06/2026-05 (ou usado um holdout interno daquele
periodo), a estabilidade observada teria parecido uma confirmacao
razoavel. O teste em dado realmente novo mostra que essa estabilidade
nao se estende para frente -- e um lembrete concreto de por que este
projeto recusa validar hipoteses no mesmo dado que as gerou.

**Decisao final: `NAO_PROMOVE`, aplicada sem ajuste de limiar ou
segundo teste.** Per o pre-registro (`TASK-ALT-005`), nenhum novo mes,
nenhuma nova feature, e nenhum novo horizonte serao testados para
"salvar" esta pista. `funding_price_divergence` fecha definitivamente
-- tanto no periodo original (`TASK-ALT-001`, SEM_INFORMACAO) quanto no
novo OOS (`TASK-ALT-005`, NAO_PROMOVE). A Familia G (Funding Structure)
nao tem mais nenhuma pista aberta.
