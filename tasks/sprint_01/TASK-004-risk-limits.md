# TASK-004 - Risk Limits Specification

## Sprint

Sprint 1 - Operational System Specification

## Dono

Execution / Risk Agent

## Revisor obrigatorio

QA / Chaos Testing Agent

## Status

DONE

## Progresso

100%

## Contexto obrigatorio

Antes de comecar, leia:

- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`
- `project_control/TASK_BOARD.md`
- `project_control/RISKS.md`
- `project_control/INTERFACES.md`
- `project_control/DECISIONS.md`
- `docs/architecture.md`
- `docs/state_machine.md`
- `tasks/sprint_01/TASK-004-risk-limits.md`

## Objetivo

Create `docs/risk_limits.md` defining MVP risk limits, entry blockers, kill-switch triggers, forbidden configurations, and escalation behavior.

## Escopo

- Define MVP capital and exposure constraints.
- Define forbidden configurations.
- Define entry blockers.
- Define kill-switch triggers.
- Define risk-reducing mode rules.
- Define fail-closed behavior for missing or stale risk inputs.

## Fora de escopo

- Risk gate implementation.
- Live engine implementation.
- Exchange connector implementation.
- Sizing implementation.
- Model implementation.

## Arquivos permitidos

- `docs/risk_limits.md`
- `project_control/RISKS.md`
- `project_control/HANDOFFS.md`
- `project_control/TEST_MATRIX.md`
- `project_control/TASK_BOARD.md`

## Arquivos proibidos

- `src/`
- `tests/`
- `notebooks/`
- `models/`
- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`

## Criterio de pronto

- Risk limits are concrete and testable.
- Forbidden configurations are explicit: Cross Margin, Kelly, 10x, live multi-exchange, leverage before Sprint 26.
- Kill-switch triggers are listed with owner, threshold, and action.
- Missing or stale risk inputs fail closed.
- Thresholds are measurable or marked as unresolved Sprint 1 gate items.
- Entry blockers include stale book, ledger uncertainty, and ACK_UNKNOWN.
- Risk-reducing behavior cannot increase exposure.
- Risk-reducing behavior includes proof obligation: new stress risk must be lower than old stress risk.
- `RISKS.md` and `TEST_MATRIX.md` are updated.
- Handoff is written.

## Testes obrigatorios

- Documentation keyword checks for forbidden configurations, entry blockers, kill-switch triggers, and fail-closed behavior.

## Riscos

- Kill switch is vague or fail-open.
- Risk limits are not measurable.
- Missing inputs are interpreted optimistically.
- Risk-reducing mode increases exposure.

## Handoff esperado

Ao terminar, atualizar `project_control/HANDOFFS.md` com:

- o que foi feito
- arquivos alterados
- testes rodados
- pendencias
- proximos passos
- marcar TASK-004 como IN_REVIEW em `project_control/TASK_BOARD.md`
