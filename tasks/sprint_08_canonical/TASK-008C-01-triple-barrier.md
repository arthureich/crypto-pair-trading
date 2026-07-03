# TASK-008C-01 - Implementar triple_barrier.py

## Dono

Quant Research Agent

## Revisor

Backtest Agent + QA / Chaos Testing Agent

## Sprint

Sprint 8 Canonico - Triple Barrier direcional e backtest estatistico
(`project_control/ROADMAP.md`, ver ADR-0009)

## Contexto obrigatorio

```text
project_control/ROADMAP.md (secao Sprint 8)
project_control/DECISIONS.md (ADR-0009)
src/research/kalman.py, src/research/ou.py (rolling_zscore, ja causal)
data/research/binance_public/normalized/sprint7_binance_usdm_202306_202605_research_gate.json
```

Implementa a barreira tripla direcional: short spread lucra se o spread cai,
stop se sobe; long spread lucra se o spread sobe, stop se cai; barreira
vertical por multiplo do half-life OU do par (capado).

Importante sobre look-ahead: a barreira e resolvida escaneando barras
FUTURAS ja conhecidas apos um sinal de entrada gerado causalmente (mesmo
padrao de "resolucao de label olha o futuro, geracao de sinal nao" ja usado
no Sprint 8/9 para calcular PnL). Isso NAO e look-ahead no sinal de entrada.
Documentar isso explicitamente nos testes e no docstring.

## Arquivos permitidos

```text
src/research/triple_barrier.py (novo)
tests/test_triple_barrier_directional.py (novo)
```

## Arquivos proibidos

```text
src/ledger/, src/execution/, src/live/, src/recovery/
src/backtest/ (Sprint 9, nao mexer)
```

## Criterio de pronto

```text
1. label_directional_triple_barrier(zscore_causal, open_time, config) retorna
   um label por sinal de entrada com: side (LONG_SPREAD/SHORT_SPREAD),
   entry_index/time/zscore, outcome (PROFIT/STOP/VERTICAL/NO_DATA),
   exit_index/time/zscore, bars_held.
2. SHORT_SPREAD (entrada com z >= entry_zscore): PROFIT se z cair ate o alvo
   (reversao); STOP se z subir mais alem da entrada por uma margem; VERTICAL
   se nenhuma barreira for tocada dentro do limite de barras.
3. LONG_SPREAD (entrada com z <= -entry_zscore): logica espelhada.
4. Barreira vertical e derivada do half-life do par (ex.: 4x half-life em
   horas, capado em um maximo razoavel).
5. NO_DATA se nao houver barras suficientes apos a entrada para resolver
   nenhuma barreira (fail-closed, nao inventar resultado).
6. So consome o z-score causal ja existente (rolling_zscore, shift(1)) --
   nao recalcula nada que possa vazar futuro na DECISAO de entrada.
```

## Testes obrigatorios

```text
pytest tests/test_triple_barrier_directional.py
- SHORT_SPREAD resolve PROFIT quando o z realmente reverte antes do stop/vertical
- LONG_SPREAD resolve PROFIT quando o z realmente sobe antes do stop/vertical
- STOP e detectado corretamente antes do PROFIT quando o excesso e adverso
- VERTICAL e retornado quando nenhuma barreira e tocada dentro do limite
- NO_DATA quando faltam barras futuras suficientes
- teste de causalidade: truncar a serie em um ponto razoavel dentro do
  limite de barras muda o outcome de VERTICAL/NO_DATA para o mesmo resultado
  que a serie completa produziria ATE aquele ponto (prova que a barreira so
  usa dados ja existentes na serie, nao inventa nada alem do fornecido)
ruff check src/research/triple_barrier.py tests/test_triple_barrier_directional.py
```

## Handoff esperado

Atualizar HANDOFFS.md, marcar TASK-008C-01 IN_REVIEW no TASK_BOARD.md.
