# TASK-009-02 - Implementar execution_simulator.py

## Dono

Backtest Agent

## Revisor

Quant Research Agent + QA / Chaos Testing Agent

## Sprint

Sprint 9 - Backtest executavel com simulacao de ordens

## Depende de

TASK-009-01 (fill_model.py)

## Contexto obrigatorio

```text
project_control/ROADMAP.md (secao Sprint 9)
src/backtest/fill_model.py
src/research/sprint8.py (OfflineSignalIntent, beta)
reports/sprint_08_backtest.md (metodologia idealizada que esta sendo substituida)
```

O Sprint 8 tratava cada perna como 100% preenchida ao preco de 1 barra depois.
O Sprint 9 simula entrada e saida perna-a-perna usando fill_model.py, e deve
expor explicitamente quando as duas pernas nao preenchem na mesma proporcao
(leg risk / exposicao residual) -- isso e um resultado esperado e importante
de reportar, nao um bug a esconder.

## Arquivos permitidos

```text
src/backtest/execution_simulator.py (novo)
tests/test_execution_simulator.py (novo)
```

## Arquivos proibidos

```text
src/ledger/, src/live/, src/recovery/, src/risk/execution_risk_gate.py
scripts/run_sprint8_backtest.py (nao alterar; Sprint 9 e um caminho novo,
    paralelo, nao uma reescrita do runner do Sprint 8)
```

## Criterio de pronto

```text
1. Simula entrada (MARKET/IOC ou LIMIT, configuravel) nas duas pernas usando
   fill_model.py, cada perna com sua propria cotacao real.
2. Simula saida apos o horizonte de holding (mesmo 1h do Sprint 8, para
   isolar a variavel testada: realismo de execucao, nao estrategia de saida).
3. PnL usa a quantidade REALMENTE preenchida por perna, nao a quantidade
   pretendida -- se uma perna preenche 60% e a outra 100%, o PnL reflete
   essa exposicao residual, com um flag explicito LEG_FILL_MISMATCH.
4. Pondera a perna B pelo beta do sinal (mesma correcao ja aplicada no
   Sprint 8 pos-revisao) -- nao reintroduzir o bug de peso 1:1.
5. Nao importa src.live, src.ledger, src.execution.client_order_id,
   src.recovery.
```

## Testes obrigatorios

```text
pytest tests/test_execution_simulator.py
- round-trip com fill completo nas duas pernas
- round-trip com fill parcial em uma perna (LEG_FILL_MISMATCH sinalizado)
- PnL usa peso beta corretamente
- ordem MARKET sem cotacao disponivel resulta em trade nao executado, nao em excecao nao tratada
ruff check src/backtest/execution_simulator.py tests/test_execution_simulator.py
```

## Handoff esperado

Atualizar HANDOFFS.md, marcar TASK-009-02 IN_REVIEW no TASK_BOARD.md.
