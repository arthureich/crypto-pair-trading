# TASK-FUND-003 - Rebalanceamento incremental por limiar de rendimento marginal

## Dono

Backtest Agent

## Revisor

Quant Research Agent + QA / Chaos Testing Agent + PM Agent

## Workstream

Funding Carry Signal Iteration (aberta por ADR-0013)

## Contexto obrigatorio

```text
tasks/funding_carry/TASK-FUND-001-define-hypothesis.md
reports/funding_carry_backtest.md
src/research/funding_carry.py
project_control/DECISIONS.md (ADR-0013)
```

TASK-FUND-002 confirmou gross edge real e positivo (funding + componente de
preco correlacionado) em todos os K testados, mas o gate NAO PASSA porque a
regra pre-registrada (rebalanceamento completo de 100% do book a cada
intervalo de 8h, por 3 anos) acumula custo (19.722,00 bps em K=5) que
excede o gross edge (8.992,18 bps). Esta tarefa testa se reduzir o
turnover -- so trocar uma perna quando a troca compensa economicamente --
preserva edge suficiente para passar o gate, sem introduzir nenhum
parametro novo de calibracao.

## Decisao de design (usuario, esta sessao)

Entre duas formulacoes propostas -- buffer de rank fixo (K_out) vs limiar
de rendimento marginal usando a constante de custo ja existente -- o
usuario aprovou explicitamente e exclusivamente a segunda, pelo motivo
registrado: um buffer de rank introduziria um hiperparametro novo sujeito
a calibracao/overfitting; o limiar de rendimento ancora a decisao na
mesma constante fisica de custo ja pre-registrada (6,0bps), sem inflacionar
graus de liberdade do modelo.

## Hipotese pre-registrada

### Regra de retencao/troca (causal, sem parametro novo)

Em cada rebalanceamento (exceto o primeiro, que faz bootstrap identico a
fase 1), o book de cada lado (K longs, K shorts) e mantido de um intervalo
para o outro, exceto quando uma troca compensa:

```text
Para o lado LONG (queremos funding baixo):
  worst_held  = perna held com o MAIOR funding_rate_asof (a mais proxima
                de nao merecer mais estar long)
  best_candidate = simbolo NAO held (nem long nem short) com o MENOR
                funding_rate_asof disponivel

  Trocar worst_held por best_candidate SE:
    (funding(worst_held) - funding(best_candidate)) * 10000
      > cost_bps_per_leg_roundtrip

Para o lado SHORT (queremos funding alto), regra espelhada:
  worst_held  = perna held com o MENOR funding_rate_asof
  best_candidate = simbolo NAO held com o MAIOR funding_rate_asof
  Trocar SE (funding(best_candidate) - funding(worst_held)) * 10000
      > cost_bps_per_leg_roundtrip
```

Repetir a troca (greedy) em cada lado enquanto houver uma troca que ainda
compense, usando um pool de candidatos calculado UMA VEZ no inicio do
intervalo (antes de qualquer troca), para evitar ciclos dentro do mesmo
intervalo. Nenhum simbolo pode estar held em ambos os lados simultaneamente.

### Alocacao de capital (pesos)

```text
- Peso-alvo de qualquer perna held permanece 1/(2K), todo intervalo --
  identico a fase 1, sem modelagem de deriva de NAV.
- Perna que permanece held: peso-alvo nao muda -> delta-peso (Δw) = 0 ->
  nao gera ordem, nao paga custo, mas continua contribuindo PnL de
  funding+preco normalmente (esta exposta ao mercado o intervalo todo).
- Perna que entra: Δw = +1/(2K) -> paga entrada.
- Perna que sai: Δw = -1/(2K) -> paga saida.
- Uma troca completa (sai uma perna + entra outra) e tratada como UM
  evento de custo equivalente a um round-trip completo
  (cost_bps_per_leg_roundtrip, a MESMA constante de 6,0bps -- nao se
  inventa uma constante de "meio round-trip"). Isto e uma escolha de
  modelagem explicita, nao uma medicao.
- Bootstrap (primeiro rebalanceamento, sem posicoes previas): monta o
  livro completo de 2K pernas do zero, custo flat idêntico a um intervalo
  da fase 1 (cost_bps_per_leg_roundtrip), consistente com "estabelecer
  2K posicoes do zero equivale ao mesmo custo de rebalanceamento completo
  que a fase 1 sempre cobra".
```

### Simbolo held que fica inelegivel (gap de dados)

```text
Se um simbolo held perde elegibilidade (funding_rate_asof ou log_price
nao-finito naquele intervalo), ele e removido a forca do book (nao se
pode continuar precificando uma posicao que nao se pode observar). A
vaga liberada e preenchida pelo melhor candidato disponivel
INCONDICIONALMENTE (nao passa pelo teste de limiar -- manter uma vaga
vazia e estritamente pior que qualquer candidato real quando a saida foi
forcada). Esta tarefa nao encontra este caso no dataset real (auditoria
da TASK-FUND-001 confirmou 0 valores NaN em funding_rate_asof nos 20
simbolos), mas o codigo trata o caso de forma fail-closed e tem teste
dedicado com dados sinteticos.
```

### Configuracao (mesma grade da TASK-FUND-002, para comparabilidade)

```text
PRIMARIA: K = 5 (decide o gate)
SECUNDARIAS (descritivas): K = 3, K = 8
cost_bps_per_leg_roundtrip = 6.0 (mesma constante, sem novo parametro)
```

### Gate (identico ao pre-registrado na TASK-FUND-001)

```text
net_profit_factor >= 1.10 E resolved_rebalances >= 500, avaliado apenas em K=5.
```

## Invariantes obrigatorios

```text
- Decisao de troca usa somente funding_rate_asof causal no momento da
  decisao (nunca preco futuro) -- verificado por teste dedicado.
- Nenhum simbolo held em ambos os lados simultaneamente.
- Pool de candidatos fixado no inicio do intervalo (sem reciclagem
  dentro do mesmo intervalo).
- Vazamento de estado entre rebalanceamentos e explicito e testado (o
  book do intervalo N+1 depende do book resolvido no intervalo N).
- Sem novo parametro de calibracao alem do que a TASK-FUND-001 ja
  registrou.
```

## Arquivos permitidos

```text
src/research/funding_carry.py
scripts/run_funding_carry_incremental_backtest.py
tests/test_funding_carry.py
reports/funding_carry_incremental_backtest.md
data/research/binance_public/cost_pilot/funding_carry_incremental_*.json
data/research/binance_public/cost_pilot/funding_carry_incremental_*.csv
project_control/
tasks/funding_carry/
```

## Arquivos proibidos

```text
src/ledger/
src/execution/
src/live/
src/recovery/
data/research/binance_public/normalized/ (nenhum novo download)
```

## Criterio de pronto

```text
1. Regra de troca e alocacao de capital implementadas exatamente per esta
   especificacao.
2. Testes cobrindo: convencao causal, held-state carregado entre
   intervalos, custo cobrado so nas pernas trocadas (nao nas mantidas),
   bootstrap, simbolo forcado a sair por gap de dados.
3. Suite completa + ruff limpos.
4. Rodado real no mesmo dataset da TASK-FUND-002 (sem novo download),
   K=5/3/8, decisao de gate reportada honestamente (PASSA ou NAO PASSA).
5. reports/funding_carry_incremental_backtest.md escrito com resultado
   real, comparando explicitamente contra a fase 1 (TASK-FUND-002).
```

## Status

DONE

## Progresso

100%

## Resultado

```text
K=5 (primario): net profit factor 1,0904 (limiar 1,10, diferenca 0,0096,
  NAO PASSA -- 3.287 rebalanceamentos resolvidos, 6,57x o piso de 500, nao
  e problema de poder estatistico)
K=3 (descritivo): net profit factor 1,1356 (PASSA, nao substitui K=5)
K=8 (descritivo): net profit factor 1,0856 (NAO PASSA)

Custo cai 99,83% vs fase 1 (19.722,00 -> 33,60 bps em K=5)
Net PnL vira positivo (-10.729,82 -> +5.620,99 bps em K=5)
Ver reports/funding_carry_incremental_backtest.md para metodologia
completa e analise.
```

## Revisao formal

```text
Quant Research Agent: PASSA. Regra de retencao usa somente
funding_rate_asof causal no momento da decisao; verificado por teste
dedicado (test_incremental_swap_decision_is_causal_independent_of_forward_price).
Nenhum parametro novo introduzido, conforme aprovado pelo usuario.

Backtest Agent: PASSA. Convencao de sinal reusada via helper compartilhado
com a fase 1 (ja verificada por revisao adversarial independente).
Contabilidade de custo (so pernas trocadas pagam) implementada e testada
com valores calculados a mao.

PM Agent: PASSA. Gate decidido estritamente por K=5 primario; K=3 passar
nao foi usado para reabrir ou substituir a decisao, conforme disciplina
pre-registrada (ADR-0010).
```
