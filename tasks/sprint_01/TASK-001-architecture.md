# TASK-001 - Architecture Specification

## Sprint

Sprint 1 - Operational System Specification

## Dono

Architect Agent

## Revisor obrigatorio

PM Agent

## Status

DONE

## Progresso

100%

## Contexto obrigatorio

Antes de comecar, leia:

- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`
- `project_control/TASK_BOARD.md`
- `project_control/INTERFACES.md`
- `project_control/DECISIONS.md`
- `tasks/sprint_01/TASK-001-architecture.md`

## Objetivo

Create `docs/architecture.md` describing system architecture, plane separation, allowed dependencies, forbidden dependencies, failure isolation, and high-level data flow.

## Escopo

- Define Market Data Plane, Signal Plane, Execution Plane, Ledger Plane, External Dead Man Switch, ML component, and Recovery component.
- Define allowed and forbidden data flows.
- Define initial deployment assumptions.
- Keep Signal order prohibition explicit.
- Keep Ledger transactional truth explicit.

## Fora de escopo

- Source code implementation.
- Trading endpoint integration.
- Ledger database implementation.
- Model implementation.
- Backtest implementation.

## Arquivos permitidos

- `docs/architecture.md`
- `project_control/INTERFACES.md`
- `project_control/DECISIONS.md`
- `project_control/HANDOFFS.md`

## Arquivos proibidos

- `src/`
- `tests/`
- `notebooks/`
- `project_control/TASK_BOARD.md`
- `project_control/PROJECT_STATE.md`
- `project_control/CURRENT_SPRINT.md`

## Criterio de pronto

- All planes and components are defined.
- Signal Plane cannot send orders.
- Execution exits do not depend on ML.
- Ledger is transactional truth.
- External Dead Man Switch is independent from the main process.
- Interfaces are reflected in `project_control/INTERFACES.md` if needed.
- Any structural decision is recorded in `project_control/DECISIONS.md`.
- Handoff is written.

## Testes obrigatorios

- Documentation keyword checks for required planes, components, data-flow sections, failure isolation, deploy assumptions, and safety invariants.

## Riscos

- Hidden Signal-to-exchange path.
- Hidden state truth outside Ledger.
- Dead Man Switch depending on the main process.
- ML contaminating deterministic execution safety.

## Handoff esperado

Ao terminar, atualizar `project_control/HANDOFFS.md` com:

- o que foi feito
- arquivos alterados
- testes rodados
- pendencias
- proximos passos
