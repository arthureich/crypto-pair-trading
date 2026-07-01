# TASK-007-07 - Criar testes de research base

## Sprint

Sprint 7 - Research base: pair selection, Kalman e OU

## Dono

QA Agent

## Revisor obrigatorio

Quant Research Agent

## Contexto obrigatorio

Antes de comecar, leia:

- project_control/PROJECT_STATE.md
- project_control/CURRENT_SPRINT.md
- project_control/TEST_MATRIX.md
- src/research/pair_selection.py, se existir
- src/research/stationarity.py, se existir
- src/research/kalman.py, se existir
- src/research/ou.py, se existir
- tasks/sprint_07/TASK-007-07-research-tests.md

## Objetivo

Criar e revisar testes automatizados que provem o comportamento minimo dos
modulos de research base.

## Escopo

- testes de pair selection
- testes de stationarity
- testes de Kalman
- testes de OU
- dados sinteticos deterministas
- regressao contra look-ahead em z-score/correlacao rolling
- verificacao de ausencia de DataFrame global mutavel

## Fora de escopo

- backtest completo
- validacao de lucro
- paper trading
- live trading
- XGBoost

## Arquivos permitidos

- tests/test_pair_selection.py
- tests/test_stationarity.py
- tests/test_kalman.py
- tests/test_ou.py
- project_control/HANDOFFS.md
- project_control/TEST_MATRIX.md

## Arquivos proibidos

- src/live/
- src/execution/
- src/ledger/
- src/models/

## Criterio de pronto

- ativo sem dados suficientes e rejeitado
- par com baixa correlacao e rejeitado
- pares sao ranqueados por score
- ADF/KPSS retornam estrutura padronizada
- half-life preliminar e calculado
- Kalman recupera beta sintetico aproximado
- Kalman gera spread_t com mesmo tamanho da serie
- Kalman marca beta instavel
- OU estima theta positivo em serie mean-reverting
- OU rejeita ou alerta theta <= 0
- z-score rolling nao usa dado futuro
- testes passam

## Testes obrigatorios

- `pytest tests/test_pair_selection.py`
- `pytest tests/test_stationarity.py`
- `pytest tests/test_kalman.py`
- `pytest tests/test_ou.py`

## Handoff esperado

Atualizar project_control/HANDOFFS.md com:

- testes criados
- resultado real
- gaps de cobertura
- pendencias
- riscos
