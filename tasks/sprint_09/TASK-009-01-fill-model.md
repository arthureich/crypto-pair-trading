# TASK-009-01 - Implementar fill_model.py

## Dono

Backtest Agent

## Revisor

QA / Chaos Testing Agent + Execution / Risk Agent

## Sprint

Sprint 9 - Backtest executavel com simulacao de ordens (`project_control/ROADMAP.md`)

## Contexto obrigatorio

Leia antes de comecar:

```text
project_control/ROADMAP.md (secao Sprint 9)
project_control/PROJECT_STATE.md
project_control/CURRENT_SPRINT.md
project_control/DECISIONS.md (ADR-0007, ADR-0008)
reports/sprint_08_backtest.md
src/execution/slippage_estimator.py (reusar estimate_slippage, nao reimplementar consumo de book)
src/research/sprint8.py (OfflineSignalIntent, contrato de universo)
```

O Sprint 8 (ja fechado, gate PASSA escopado a 13 pares) assumiu fill perfeito
mark-to-market 1 barra depois do sinal. O Sprint 9 substitui essa suposicao
por um modelo de fill realista contra cotacoes reais tick-a-tick de junho/2023
ja baixadas e verificadas por checksum em
`data/research/binance_public/cost_pilot/raw/data/futures/um/daily/bookTicker/`.

Limite de dados honesto: so temos top-of-book (melhor bid/ask + quantidade
naquele nivel), nao profundidade L2 completa. O modelo de fill deve fechar-se
(fail-closed) no nivel 1 -- nao fabricar profundidade alem do nivel 1.

## Arquivos permitidos

```text
src/backtest/fill_model.py (novo)
src/backtest/__init__.py (novo, se necessario)
tests/test_fill_model.py (novo)
```

## Arquivos proibidos

```text
src/ledger/
src/execution/ (exceto leitura)
src/live/
src/recovery/
src/risk/execution_risk_gate.py
scripts/run_sprint8_backtest.py
src/research/sprint8.py
```

## Criterio de pronto

```text
1. Modelo de fill consome apenas top-of-book (best_bid/ask + qty), reusando
   estimate_slippage de src/execution/slippage_estimator.py para o calculo
   de consumo/slippage (nao duplicar essa logica).
2. MARKET/IOC: preenche o que estiver disponivel no nivel 1 imediatamente;
   quantidade alem disso e cancelada (nao fabrica fill).
3. LIMIT (maker): preenche apenas se uma cotacao subsequente, dentro de um
   TTL configuravel, cruzar o preco limite; senao, status EXPIRED.
4. Latencia: a cotacao usada para o fill e a primeira com
   event_time >= decision_time + latency_ms (nunca uma cotacao anterior ao
   decision_time).
5. ACK_UNKNOWN: uma fracao configuravel (determinada por hash deterministico
   do signal_id, nao por random global nao-seedado) das ordens simula
   ACK_UNKNOWN, adicionando um atraso de reconciliacao antes do resultado
   final ser conhecido -- documentar exatamente como isso afeta o timing.
6. Nenhuma funcao deste modulo importa src.execution.* (exceto
   slippage_estimator), src.ledger.*, src.live.*, src.recovery.*.
7. Falhas (sem cotacao disponivel, quantidade invalida) sao fail-closed
   (excecao ou status explicito), nunca silenciosas.
```

## Testes obrigatorios

```text
pytest tests/test_fill_model.py
- fill completo quando quantidade <= profundidade do nivel 1
- fill parcial (IOC) quando quantidade > profundidade do nivel 1
- ordem MARKET sem cotacao disponivel falha fechado
- LIMIT preenche quando cotacao futura cruza o preco
- LIMIT expira (EXPIRED) se nenhuma cotacao cruzar dentro do TTL
- latencia: a cotacao escolhida nunca tem event_time < decision_time + latency_ms
- ACK_UNKNOWN e deterministico (mesmo signal_id -> mesmo resultado sempre)
ruff check src/backtest/fill_model.py tests/test_fill_model.py
```

## Handoff esperado

Atualizar `project_control/HANDOFFS.md` com: arquivos alterados, testes
rodados, decisoes de design (ex.: formula de latencia, taxa de ACK_UNKNOWN),
pendencias. Marcar TASK-009-01 como IN_REVIEW em `project_control/TASK_BOARD.md`.
