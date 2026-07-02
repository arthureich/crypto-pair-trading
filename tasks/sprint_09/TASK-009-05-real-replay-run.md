# TASK-009-05 - Rodar replay real nos 13 pares aprovados

## Dono

Backtest Agent

## Revisor

PM Agent + Quant Research Agent

## Sprint

Sprint 9 - Backtest executavel com simulacao de ordens

## Depende de

TASK-009-04

## Contexto obrigatorio

```text
scripts/run_sprint9_replay.py
project_control/SPRINT8_UNIVERSE.json
data/research/binance_public/cost_pilot/raw/ (dados reais ja verificados)
```

## Arquivos permitidos

```text
data/research/binance_public/cost_pilot/sprint9_*.json (saida)
data/research/binance_public/cost_pilot/sprint9_*.csv (saida)
```

## Arquivos proibidos

```text
qualquer src/*.py (esta e uma tarefa de execucao, nao de codigo)
```

## Criterio de pronto

```text
1. Executa scripts/run_sprint9_replay.py contra dados reais (nao mock) para
   os 13 pares backtest-approved do Sprint 8.
2. Reporta: PnL bruto/liquido realista, taxa de fill completo/parcial/
   expirado/sem-cotacao, taxa de ACK_UNKNOWN, comparacao explicita com o
   resultado idealizado do Sprint 8 (quanto o realismo de execucao mudou o
   resultado).
3. Nenhum download novo -- so consome dados ja preservados.
```

## Testes obrigatorios

```text
Nao aplicavel (tarefa de execucao). Confirmar que a suite completa ainda
passa antes e depois: pytest tests -q
```

## Handoff esperado

Atualizar HANDOFFS.md com os numeros reais obtidos, marcar TASK-009-05
IN_REVIEW no TASK_BOARD.md.
