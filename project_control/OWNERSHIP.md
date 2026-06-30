# OWNERSHIP

## Area Ownership

| Area | Dono principal | Revisor obrigatorio |
|---|---|---|
| Project control | PM Agent | Documentation Agent |
| Architecture | Architect Agent | PM Agent |
| Interfaces | Architect Agent | Ledger Agent + Execution / Risk Agent |
| Decisions / ADRs | Architect Agent | PM Agent |
| Ledger | Ledger Agent | Architect Agent + QA / Chaos Testing Agent |
| Recovery | Ledger Agent | Execution / Risk Agent + QA / Chaos Testing Agent |
| Market Data | Market Data Agent | Execution / Risk Agent |
| Order Book | Market Data Agent | QA / Chaos Testing Agent |
| Kalman/OU | Quant Research Agent | Backtest Agent |
| Backtest | Backtest Agent | Quant Research Agent + QA / Chaos Testing Agent |
| Execution Risk Gate | Execution / Risk Agent | Architect Agent + QA / Chaos Testing Agent |
| Order Router | Execution / Risk Agent | Ledger Agent + QA / Chaos Testing Agent |
| ML Models | ML Agent | Quant Research Agent + QA / Chaos Testing Agent |
| Monitoring | DevOps / Observability Agent | Execution / Risk Agent |
| Docs | Documentation Agent | PM Agent |

## Critical Review Rule

Any task touching one of these paths requires mandatory review:

```text
src/ledger/
src/execution/
src/live/
src/recovery/
src/risk/execution_risk_gate.py
```

## Sprint 1 Document Ownership

| Path | Dono principal | Revisor obrigatorio |
|---|---|---|
| docs/architecture.md | Architect Agent | PM Agent |
| docs/state_machine.md | Execution / Risk Agent | Architect Agent |
| docs/event_contracts.md | Ledger Agent | Architect Agent |
| docs/risk_limits.md | Execution / Risk Agent | QA / Chaos Testing Agent |
| docs/recovery_protocol.md | Ledger Agent | QA / Chaos Testing Agent |
