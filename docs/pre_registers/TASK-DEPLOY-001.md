# TASK-DEPLOY-001 - Pre-registro: transformar a TSM validada em sistema forward executavel, auditavel e anti-overfit

## Status

ACCEPTED (locked) - travado 2026-07-18. Sob ADR-0033. NAO e pesquisa de alpha.
O objetivo e medir se o edge JA encontrado sobrevive a custos, execucao e
capacidade reais; e endurecer a operacao. NENHUMA acao com dinheiro real.

## Principio central (LOCKED)

NAO re-otimizar a estrategia. Separar rigorosamente: pesquisa de alpha /
validacao estatistica / simulacao de execucao / gestao de risco / engenharia de
producao / acompanhamento forward. Mudancas de infra, logging, execucao e
seguranca NAO podem alterar os parametros economicos da estrategia congelada.

## Fases (plano travado)

```text
Fase 0  Reconciliar e CONGELAR a config canonica (artifacts/tsm/canonical-config
        .json), com hash reproduzivel e commit de origem; resolver a ambiguidade
        de nome (core vs combined) pelos ARTEFATOS, nao pelos relatorios.
Fase 1  Auditoria de metricas/unidades -- resolver o maxDD ~0.31-0.80 ("shallow"):
        e 80%, outra unidade, formatacao, ou bug? Drawdown por universo nas DUAS
        framings; testes de borda de drawdown.
Fase 2  Paper-forward IMUTAVEL (append-only), 3 streams: teorico / executavel /
        implantacao conservadora; registrar sinal ANTES da execucao simulada.
Fase 3  Modelo de execucao realista (uma politica conservadora PRE-fixada; sem
        escolher a politica que maximiza Sharpe; guardas anti-lookahead).
Fase 4  Capacidade / liquidez / impacto (grade de capital so para caracterizar;
        soft/hard capacity; ativos que limitam).
Fase 5  Controles de producao (limites, modos de falha, idempotencia, kill
        switches) -- por justificativa operacional, nunca por melhorar backtest.
Fase 6  Ajuste por multiplas tentativas (ledger de tentativas, DSR/PSR, numero
        efetivo de tentativas, dependencia entre universos, block bootstrap).
Fase 7  Monitoramento forward (horizontes 1/3/6/12/18-24m; metricas; alertas SEM
        modificar a estrategia automaticamente).
```

## O que NAO fazer (LOCKED)

```text
Sem novo grid de lookbacks; sem novo threshold de sinal; sem tanh/sigmoid/
saturacao escolhida por Sharpe; sem conviction sizing, meta-labeling, regime
filter, ML; sem escolha ex-post de universos; sem remover ativos negativos apos
ver resultado; sem alterar W/CAP/alvo de vol/ERC; sem escolher politica de
execucao pelo backtest; sem combinar estrategia nao-validada; sem reclassificar
negativo como sucesso; sem usar o forward para retuning; sem real trading; sem
push remoto sem autorizacao.
```

## Tratamento de bugs (LOCKED)

```text
Bug de infra (nao muda logica economica): corrigir, testar, documentar, preservar
outputs anteriores. Bug que muda sinais/pesos/timestamps/PnL: NAO sobrescrever
historico; nova versao; diff de impacto; marcar resultados afetados; reiniciar o
forward da versao corrigida; nao juntar periodos incompativeis.
```

## Entregaveis

```text
canonical-config.json (+hash +source_commit); metric-units-audit.md; per-universe
-drawdown-audit.csv/json; ledger forward imutavel; theoretical-vs-executable;
capacity analysis; production risk policy; failure-mode tests; multiple-testing/
haircut report; forward monitoring report; status atualizado. Cada relatorio
distingue fact / estimate / assumption / limitation / decision.
```

## Politica de parada (LOCKED)

```text
Ao concluir: congelar a familia TSM; manter apenas o forward; nao abrir variantes
novas sobre a mesma janela; registrar ideias em backlog; exigir nova hipotese,
novo pre-registro e dados realmente independentes antes de testar qualquer coisa.
Sucesso NAO e aumentar Sharpe historico; e descobrir honestamente se o edge
sobrevive no mundo real.
```
