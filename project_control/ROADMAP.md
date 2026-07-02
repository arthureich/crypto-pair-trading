# ROADMAP

Status: master 28-sprint roadmap, provided by the user on 2026-07-02. This is
now the authoritative source for sprint sequencing, objectives, and gates.
Prior sprints' `CURRENT_SPRINT.md`/`TASK_BOARD.md` content is reconciled
against this document; see `DECISIONS.md` ADR-0008 for the numbering
reconciliation this introduced.

The full text of the roadmap (as provided) is preserved verbatim below.
Do not edit sprint definitions here without an ADR — this file is the
contract every future `CURRENT_SPRINT.md` must trace back to.

## Fase 1 — Sprints 1 a 14 ate Live Minimo

1. Especificacao operacional do sistema
2. Ledger base com SQLite WAL
3. Idempotencia, clientOrderId e reconciliacao cumulativa
4. Recovery boot e modo safe
5. Market Data Plane: book local
6. Features de execucao e slippage
7. Research base: pair selection, Kalman e OU
8. Triple Barrier direcional e backtest estatistico
9. Backtest executavel com simulacao de ordens
10. Execution Risk Gate
11. Paper trading engine
12. Dataset real, P_fill e P_profit
13. Calibracao, thresholds e paper trading final
14. Preparacao e ativacao do Live Minimo

## Fase 2 — Sprints 15 a 28 ate Producao Institucional

15. Live Minimo Observado
16. Live Conservador
17. Auditoria de performance real
18. Expansao para 2 pares
19. Risk Engine de portfolio v1
20. Sizing dinamico conservador
21. Execucao avancada v1
22. Emergency Exit v2
23. Infraestrutura de producao
24. Regime detection e quebra estrutural
25. Universo dinamico de pares
26. Alavancagem moderada
27. Multi-exchange piloto
28. Producao Institucional

## Regra central

Primeiro provar que o sistema nao se mata; depois provar que ele tem edge;
depois operar pequeno; depois escalar. Nunca pular etapas.

## Sprint 9 — Backtest executavel com simulacao de ordens (detalhe completo)

### Objetivo

Transformar o backtest em uma simulacao realista de execucao.

### Por que existe

Um sinal pode ser lucrativo no candle e perder dinheiro na execucao. Aqui se
testa partial fill, slippage, latencia, IOC, maker nao preenchido e
ACK_UNKNOWN.

### Entregaveis

```text
src/backtest/replay_engine.py
src/backtest/execution_simulator.py
src/backtest/fill_model.py
reports/backtest_executable_v1.md
```

### Tarefas principais

```text
implementar replay causal
simular bid/ask realista
simular slippage por profundidade
simular partial fill
simular IOC
simular maker nao preenchido
simular ordem expirada
simular latencia
simular ACK_UNKNOWN
```

### Criterio de pronto

```text
ordem nao tem fill garantido
partial fill gera exposicao residual
ACK_UNKNOWN forca reconciliacao simulada
PnL liquido ainda e positivo em cenario conservador
stress de fee e slippage nao destroi completamente o edge
```

## Sprint 8 canonico (para referencia -- ver reconciliacao em ADR-0008)

O roadmap original define Sprint 8 como "Triple Barrier direcional e backtest
estatistico" (`src/research/triple_barrier.py`,
`src/backtest/statistical_backtest.py`, metricas Sharpe/Sortino/profit
factor, gate de profit factor liquido > 1.10). O Sprint 8 realmente executado
neste projeto ("Backtest walk-forward cost-aware") divergiu desse escopo
canonico -- ver ADR-0008 para o que foi feito, o que ficou pendente, e como
isso afeta o Sprint 9.
