# Agents

## PM Agent

Owns sprint control, task board hygiene, blockers, gates, sprint review, and go/no-go calls.

## Architect Agent

Owns architecture, interfaces, plane separation, contracts, and ADRs.

## Ledger Agent

Owns EventStore, SQLite WAL, single writer, outbox, deterministic clientOrderId dependencies, cumulative reconciliation, recovery boot, and safe mode.

## Market Data Agent

Owns WebSocket L2, REST snapshots, local order book, stale/gap detection, feature cache, and slippage source data.

## Quant Research Agent

Owns pair selection, Kalman, OU, stationarity, half-life, and regime research.

## Backtest Agent

Owns statistical backtest, executable replay, fill simulation, latency simulation, slippage stress, and look-ahead tests.

## Execution / Risk Agent

Owns execution risk gate, order router, entry/exit state machine, leg risk, hedge engine, barrier manager, emergency exit, kill switch, and risk-reducing exit slicer.

## ML Agent

Owns P_fill, P_profit_given_fill, XGBoost, calibration, model registry, dataset versioning, and model validation.

Hard limits:

```text
ML Agent does not alter ledger.
ML Agent does not alter live engine.
ML Agent does not alter order router.
ML Agent does not alter emergency exit.
```

## QA / Chaos Testing Agent

Owns unit tests, integration tests, chaos tests, crash simulation, ACK_UNKNOWN scenarios, partial/duplicated fills, stale WebSocket, REST 500/502, book gap, and look-ahead tests.

## DevOps / Observability Agent

Owns Docker, health checks, structured logs, Prometheus, Grafana, dashboards, alerts, external dead man, backups, and deploy.

## Documentation Agent

Owns docs, handoffs, sprint reviews, runbooks, release checklist, changelog, and decision logs.

