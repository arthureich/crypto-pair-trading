# TASK-009-04 - Testes de Sprint 9 (no-look-ahead, fail-closed, chaos)

## Dono

QA / Chaos Testing Agent

## Revisor

Backtest Agent + PM Agent

## Sprint

Sprint 9 - Backtest executavel com simulacao de ordens

## Depende de

TASK-009-01, TASK-009-02, TASK-009-03

## Contexto obrigatorio

```text
src/backtest/fill_model.py
src/backtest/execution_simulator.py
src/backtest/replay_engine.py
tests/test_fill_model.py, tests/test_execution_simulator.py, tests/test_replay_engine.py (revisar cobertura ja criada pelas tasks anteriores)
```

## Arquivos permitidos

```text
tests/test_fill_model.py
tests/test_execution_simulator.py
tests/test_replay_engine.py
tests/test_sprint9_chaos.py (novo, cenarios adicionais de chaos)
```

## Arquivos proibidos

```text
src/backtest/*.py (revisao read-only do codigo; testes adicionais apenas)
src/ledger/, src/live/, src/recovery/
```

## Criterio de pronto

```text
1. Confirmar cobertura de: partial fill, IOC, maker expirado, latencia,
   ACK_UNKNOWN, causalidade (sinal em t nao usa cotacao < t).
2. Adicionar cenarios de chaos faltantes: rede de cotacoes com gap temporal
   grande (sem cotacao por horas), quantidade zero disponivel, ambas as
   pernas expirando simultaneamente.
3. Nenhum teste depende de rede real (todos usam fixtures locais).
```

## Testes obrigatorios

```text
pytest tests/test_fill_model.py tests/test_execution_simulator.py tests/test_replay_engine.py tests/test_sprint9_chaos.py
pytest tests -q (suite completa, sem regressao)
ruff check src tests scripts
```

## Handoff esperado

Atualizar TEST_MATRIX.md com as novas linhas de teste, HANDOFFS.md, marcar
TASK-009-04 IN_REVIEW no TASK_BOARD.md.
