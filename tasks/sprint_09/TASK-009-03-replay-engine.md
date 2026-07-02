# TASK-009-03 - Implementar replay_engine.py

## Dono

Backtest Agent

## Revisor

QA / Chaos Testing Agent + Market Data Agent

## Sprint

Sprint 9 - Backtest executavel com simulacao de ordens

## Depende de

TASK-009-01, TASK-009-02

## Contexto obrigatorio

```text
project_control/ROADMAP.md (secao Sprint 9)
src/backtest/fill_model.py
src/backtest/execution_simulator.py
src/research/sprint8.py (generate_pair_signal_intents, build_walk_forward_splits)
data/research/binance_public/cost_pilot/sprint8_backtest_pair_results.csv (sinais ja gerados no Sprint 8)
project_control/SPRINT8_UNIVERSE.json
```

Reusa os MESMOS sinais causais ja gerados e revisados no Sprint 8
(generate_pair_signal_intents), para isolar exatamente o que o Sprint 9 muda:
realismo de execucao, nao geracao de sinal. Le os arquivos brutos ja baixados
e verificados por checksum em
data/research/binance_public/cost_pilot/raw/data/futures/um/daily/bookTicker/
-- NAO baixar nada novo.

Cuidado de memoria: um arquivo diario e ~20-60MB descomprimido. Carregar
apenas o dia necessario por simbolo por vez (o Sprint 8 ja teve um OOM kill
por carregar um mes inteiro de uma vez -- nao repetir esse erro). Usar um
cache pequeno (LRU, poucos arquivos) se o mesmo dia for reusado por sinais
proximos.

## Arquivos permitidos

```text
src/backtest/replay_engine.py (novo)
scripts/run_sprint9_replay.py (novo)
tests/test_replay_engine.py (novo)
```

## Arquivos proibidos

```text
src/ledger/, src/live/, src/recovery/, src/risk/execution_risk_gate.py
scripts/run_sprint8_backtest.py, scripts/run_sprint7_execution_cost_download.py
```

## Criterio de pronto

```text
1. Replay e causal: para cada sinal, so consome cotacoes com
   event_time >= created_at do sinal (nunca antes).
2. Usa os arquivos diarios ja baixados; falha fechado (erro claro) se um
   arquivo esperado nao existir, nunca ignora silenciosamente o simbolo.
3. Memoria: nunca mantem mais de um pequeno numero fixo de dias
   descomprimidos em memoria simultaneamente (documentar o limite).
4. Roda sobre os 13 pares backtest-approved do Sprint 8 (SPRINT8_UNIVERSE.json
   + resultado do Sprint 8), reusando os mesmos sinais walk-forward.
5. Gera metricas agregadas e por par: PnL bruto/liquido, taxa de fill
   completo vs parcial vs expirado vs sem cotacao, taxa de ACK_UNKNOWN,
   exposicao residual por LEG_FILL_MISMATCH.
```

## Testes obrigatorios

```text
pytest tests/test_replay_engine.py
- replay nao consome cotacao anterior ao sinal (teste de causalidade)
- arquivo ausente falha fechado com mensagem clara
- memoria: teste que confirma que o cache de dias carregados tem tamanho limitado
ruff check src/backtest/replay_engine.py scripts/run_sprint9_replay.py tests/test_replay_engine.py
```

## Handoff esperado

Atualizar HANDOFFS.md, marcar TASK-009-03 IN_REVIEW no TASK_BOARD.md.
