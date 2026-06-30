# TASK_BOARD

Last updated: 2026-06-30

## Status permitidos

```text
BACKLOG
READY
IN_PROGRESS
BLOCKED
IN_REVIEW
CHANGES_REQUESTED
DONE
ARCHIVED
```

## Regras

- Agent can start only tasks in READY.
- Task cannot be READY without definition of done.
- Task cannot be READY without allowed files.
- Critical-area tasks require a mandatory reviewer.
- Blocked tasks must include a clear blocker.
- No task can be DONE without review and handoff.

## Quadro

| ID | Sprint | Tarefa | Dono | Status | Branch | Revisor | Bloqueio |
|---|---:|---|---|---|---|---|---|
| TASK-001 | 1 | Criar architecture.md | Architect Agent | DONE | - | PM Agent | nenhum |
| TASK-002 | 1 | Definir state machine | Execution / Risk Agent | DONE | - | Architect Agent | nenhum |
| TASK-003 | 1 | Definir event contracts | Ledger Agent | DONE | - | Architect Agent | nenhum |
| TASK-004 | 1 | Definir risk limits | Execution / Risk Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-005 | 1 | Definir recovery protocol | Ledger Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-006 | 2 | Criar schema SQLite inicial | Ledger Agent | DONE | - | Architect Agent | nenhum |
| TASK-007 | 2 | Implementar bootstrap SQLite WAL | Ledger Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-008 | 2 | Definir modelos do Ledger | Ledger Agent | DONE | - | Architect Agent | nenhum |
| TASK-009 | 2 | Implementar EventStore append/read | Ledger Agent | DONE | - | Architect Agent + QA / Chaos Testing Agent | nenhum |
| TASK-010 | 2 | Testar EventStore e rebuild basico | QA / Chaos Testing Agent | DONE | - | Ledger Agent | nenhum |
| TASK-011 | 3 | Implementar clientOrderId deterministico | Execution / Risk Agent | DONE | - | Architect Agent | nenhum |
| TASK-012 | 3 | Implementar helpers de idempotencia | Ledger Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-013 | 3 | Implementar reconciliacao cumulativa | Ledger Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-014 | 3 | Implementar guard de ACK_UNKNOWN | Execution / Risk Agent | DONE | - | Ledger Agent + QA / Chaos Testing Agent | nenhum |
| TASK-015 | 3 | Testes integrados Sprint 3 | QA / Chaos Testing Agent | DONE | - | Ledger Agent | nenhum |
| TASK-016 | 4 | Detectar ORDER_SENT nao resolvido apos restart | Ledger Agent | DONE | - | Execution / Risk Agent + QA / Chaos Testing Agent | fallback PM review |
| TASK-017 | 4 | Classificar recovery boot e resume gate | Ledger Agent | DONE | - | QA / Chaos Testing Agent | fallback PM review |
| TASK-018 | 4 | Decidir rota de partial fill | Execution / Risk Agent | DONE | - | Ledger Agent + QA / Chaos Testing Agent | fallback PM review |
| TASK-019 | 4 | Testes chaos/integracao Sprint 4 | QA / Chaos Testing Agent | DONE | - | Ledger Agent | fallback PM review |
| TASK-020 | 4 | Gate review Sprint 4 | PM Agent | DONE | - | Ledger Agent + QA / Chaos Testing Agent | fallback PM review |
| TASK-021 | 5 | Definir book health e sequenciamento L2 | Market Data Agent | DONE | - | Execution / Risk Agent | nenhum |
| TASK-022 | 5 | Invalidar book em gap/stale | Market Data Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-023 | 5 | Decidir snapshot resync | Market Data Agent | DONE | - | Execution / Risk Agent + QA / Chaos Testing Agent | nenhum |
| TASK-024 | 5 | Testes Sprint 5 book health | QA / Chaos Testing Agent | DONE | - | Market Data Agent | nenhum |
| TASK-025 | 5 | Gate review Sprint 5 | PM Agent | DONE | - | Market Data Agent + QA / Chaos Testing Agent | nenhum |
| TASK-026 | 6 | Criar BookExecutionFeatures | Market Data Agent | DONE | - | Execution / Risk Agent | nenhum |
| TASK-027 | 6 | Implementar spread/depth/imbalance/volatilidade | Market Data Agent | DONE | - | QA / Chaos Testing Agent | nenhum |
| TASK-028 | 6 | Implementar SlippageEstimator | Execution / Risk Agent | DONE | - | Market Data Agent + QA / Chaos Testing Agent | nenhum |
| TASK-029 | 6 | Implementar FeatureCache | Market Data Agent | DONE | - | Execution / Risk Agent | nenhum |
| TASK-030 | 6 | Testes e gate review Sprint 6 | QA / Chaos Testing Agent + PM Agent | DONE | - | Market Data Agent + Execution / Risk Agent | nenhum |

## Progresso

| ID | Progresso | Notas |
|---|---:|---|
| TASK-001 | 100% | PM final review passed; architecture specification is documented and integrated. |
| TASK-002 | 100% | Architect review passed; state machine specification is documented and integrated. |
| TASK-003 | 100% | Architect review passed after metadata and TEST_MATRIX cleanup; event contracts are documented and integrated. |
| TASK-004 | 100% | QA review passed; risk limits specification is documented and integrated. |
| TASK-005 | 100% | QA review passed; recovery protocol specification is documented and integrated. |
| TASK-006 | 100% | Architect re-review passed; initial SQLite schema is documented, validated, and integrated. |
| TASK-007 | 100% | QA review passed; SQLite WAL bootstrap is implemented and integrated. |
| TASK-008 | 100% | Architect review passed; Ledger models are implemented and integrated. |
| TASK-009 | 100% | Architect and QA reviews passed; EventStore append/read APIs are implemented and integrated. |
| TASK-010 | 100% | Ledger/PM review passed; EventStore test coverage is integrated. |
| TASK-011 | 100% | Architect review passed; deterministic clientOrderId integrated. |
| TASK-012 | 100% | QA review passed; Ledger idempotency helpers integrated. |
| TASK-013 | 100% | QA review passed; cumulative fill reconciliation integrated. |
| TASK-014 | 100% | Ledger and QA reviews passed; ACK_UNKNOWN retry guard integrated. |
| TASK-015 | 100% | Ledger review passed; Sprint 3 integration tests integrated. |
| TASK-016 | 100% | PM fallback review passed; unresolved ORDER_SENT scanner integrated. |
| TASK-017 | 100% | PM fallback review passed; recovery boot gate integrated. |
| TASK-018 | 100% | PM fallback review passed; partial-fill route helper integrated. |
| TASK-019 | 100% | PM fallback review passed; Sprint 4 chaos/integration tests integrated. |
| TASK-020 | 100% | Sprint 4 gate passed; report created. |
| TASK-021 | 100% | Execution / Risk review passed; book sequencing helper integrated. |
| TASK-022 | 100% | QA / Chaos review passed; gap/stale invalidation integrated. |
| TASK-023 | 100% | Execution / Risk and QA / Chaos reviews passed; snapshot resync helper integrated. |
| TASK-024 | 100% | Sprint 5 focused and full test suites passed; TEST_MATRIX updated. |
| TASK-025 | 100% | Sprint 5 gate passed; report created. |
| TASK-026 | 100% | Execution / Risk review passed; BookExecutionFeatures fail-closed usability integrated. |
| TASK-027 | 100% | Market Data and QA reviews passed; spread/depth/imbalance/volatility helpers integrated. |
| TASK-028 | 100% | Market Data and QA reviews passed; SlippageEstimator integrated with explicit failure reasons. |
| TASK-029 | 100% | Execution / Risk review passed; FeatureCache stale fail-closed behavior integrated. |
| TASK-030 | 100% | Sprint 6 gate passed after P1 QA findings were corrected and re-reviewed. |
