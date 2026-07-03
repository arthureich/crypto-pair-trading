# TASK-008C-02 - Implementar statistical_backtest.py

## Dono

Backtest Agent

## Revisor

Quant Research Agent + QA / Chaos Testing Agent

## Sprint

Sprint 8 Canonico

## Depende de

TASK-008C-01

## Contexto obrigatorio

```text
project_control/ROADMAP.md (secao Sprint 8)
project_control/DECISIONS.md (ADR-0009)
src/research/triple_barrier.py
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.json (41 pares estatisticos)
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_bars.csv (ou .csv.gz)
```

Backtest a nivel de candle (barra de 1h), NAO tick-a-tick (isso e o Sprint
9). Custo conservador FIXO por especificacao do roadmap -- nao usar a
evidencia real de custo do ADR-0007/Sprint 9 aqui (esse e o ponto do
roadmap: um gate barato e rapido antes do trabalho caro com dado real).
Funding usa o `funding_carry_bps_per_day` real ja calculado no Sprint 7.

## Arquivos permitidos

```text
src/backtest/statistical_backtest.py (novo)
tests/test_statistical_backtest.py (novo)
scripts/run_sprint8_canonical_backtest.py (novo)
```

## Arquivos proibidos

```text
src/ledger/, src/execution/, src/live/, src/recovery/
src/backtest/fill_model.py, execution_simulator.py, replay_engine.py (Sprint 9, nao mexer)
```

## Criterio de pronto

```text
1. Para cada par, gera sinais causais (z-score >= entry_zscore ou <=
   -entry_zscore) e resolve cada um via label_directional_triple_barrier.
2. PnL bruto = movimento do spread entre entrada e saida (mesma logica de
   combinacao ponderada por beta ja usada e revisada no Sprint 8/9 --
   reusar essa formula, nao reinventar).
3. Custo = funding_carry_bps_per_day real * dias mantido + uma constante
   fixa conservadora de fee/slippage por perna documentada explicitamente
   (nao e medicao, e suposicao -- dizer isso no relatorio).
4. Metricas por par E agregadas: Sharpe, Sortino, max drawdown, profit
   factor, hit rate, avg win/loss, turnover, tempo medio em trade.
5. Sem look-ahead: sinal de entrada so usa dado causal; resolucao de
   barreira so usa barras ja existentes no dataset (nao gera dado).
6. Gate: profit factor liquido >= 1.10 para o par continuar aprovado.
```

## Testes obrigatorios

```text
pytest tests/test_statistical_backtest.py
- PnL liquido = bruto - custo (funding + fee fixo), formula auditavel
- profit factor, Sharpe, Sortino calculados corretamente contra caso sintetico conhecido
- pares com profit factor < 1.10 sao marcados como rejeitados, nao escondidos
- sem look-ahead (mesma tecnica de truncar serie usada na TASK-008C-01)
ruff check src/backtest/statistical_backtest.py tests/test_statistical_backtest.py scripts/run_sprint8_canonical_backtest.py
```

## Handoff esperado

Atualizar HANDOFFS.md, marcar TASK-008C-02 IN_REVIEW no TASK_BOARD.md.
