# TASK-008C-03 - Rodar backtest real e gerar relatorio

## Dono

Backtest Agent

## Revisor

PM Agent + Quant Research Agent

## Sprint

Sprint 8 Canonico

## Depende de

TASK-008C-02

## Contexto obrigatorio

```text
scripts/run_sprint8_canonical_backtest.py
41 pares estatisticos do Sprint 7 (nao os 31 cost-gated nem os 13
backtest-approved -- ver ADR-0009 sobre o universo escolhido)
```

## Arquivos permitidos

```text
reports/backtest_statistical.md (novo)
data/research/binance_public/cost_pilot/sprint8_canonical_*.json,*.csv (saida)
```

## Criterio de pronto

```text
1. Roda de verdade (nao mock) contra as barras reais de junho/2023-maio/2026
   ja normalizadas no Sprint 7.
2. Relatorio explicita: metodologia da barreira, formula de custo
   conservador fixo (com o valor exato usado e a justificativa), metricas
   por par e agregadas, quais pares passam profit factor >= 1.10 e quais
   nao, decisao de gate.
3. Deixa claro que esse resultado usa CUSTO CONSERVADOR ESTIMADO, diferente
   do resultado do Sprint 9 que usa custo real tick-a-tick -- os dois nao
   sao diretamente comparaveis sem essa ressalva.
```

## Testes obrigatorios

```text
Suite completa: pytest tests -q
ruff check src scripts tests
```

## Handoff esperado

Handoff de fechamento da Sprint 8 Canonica em HANDOFFS.md, decisao de gate
(quantos pares passam profit factor >= 1.10), atualizar RISKS.md para
fechar o debito tecnico do ADR-0008.
