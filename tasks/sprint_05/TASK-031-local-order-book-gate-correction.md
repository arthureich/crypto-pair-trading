# TASK-031 - Corrigir gate: LocalOrderBook snapshot/diff

## Sprint

Sprint 5 - Market Data Plane: book local

## Dono

Market Data Agent

## Revisor obrigatorio

QA / Chaos Testing Agent + PM Agent

## Contexto obrigatorio

Antes de comecar, leia:

- project_control/PROJECT_STATE.md
- project_control/CURRENT_SPRINT.md
- project_control/INTERFACES.md
- src/market_data/book_health.py
- tests/test_book_health.py
- tasks/sprint_05/TASK-031-local-order-book-gate-correction.md

## Objetivo

Implementar um livro local L2 puro e testavel que aplique snapshots e diff
updates, valide sequencia, exponha top of book e falhe fechado quando o livro
nao estiver sincronizado, fresco ou completo.

## Escopo

- LocalOrderBook/BookBuilder
- aplicacao de snapshot
- aplicacao de diff update em sequencia
- descarte de eventos antigos/duplicados
- invalidacao em sequence gap
- remocao de nivel com quantidade zero
- best_bid e best_ask
- book_age_ms
- in_sync/valid/needs_resync
- testes focados de book local

## Fora de escopo

- WebSocket client real
- Exchange REST client real
- Execution Risk Gate completo
- order router
- signal generation
- research/Kalman/OU
- paper trading
- live trading

## Arquivos permitidos

- src/market_data/book_builder.py
- src/market_data/__init__.py
- tests/test_book_builder.py

## Arquivos proibidos

- src/live/
- src/execution/
- src/ledger/
- src/research/

## Criterio de pronto

- snapshot e reconstruido corretamente
- diff updates sao aplicados corretamente
- best_bid e best_ask estao corretos
- quantidade zero remove nivel
- eventos antigos/duplicados sao descartados sem corromper estado
- sequence gap invalida o book
- stale book e detectado
- book sem bids/asks e invalido
- book_age_ms funciona
- book.in_sync e confiavel
- testes passam

## Testes obrigatorios

- `UV_CACHE_DIR=.uv-cache uv run --with pytest pytest tests/test_book_builder.py --basetemp=pytest_temp_run_task031 -o cache_dir=pytest_temp_run_task031/.pytest_cache`

## Handoff esperado

Atualizar project_control/HANDOFFS.md com:

- o que foi feito
- arquivos alterados
- testes rodados
- pendencias
- riscos
