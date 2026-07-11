# Research Program Retrospective (2026-07)

> SUPERSEDED (2026-07-11) by `reports/strategy_results_and_feedback.md`, which
> is the current consolidated ledger of all strategies/hypotheses (results +
> feedback, grouped) and covers work done after this retrospective (funding
> carry incremental, ML meta-labeling, position sizing, basis, short-horizon,
> flow, and the forward paper track). Kept for history.

Consolida, num unico documento, todas as linhas de pesquisa fechadas
nesta sessao -- da Sprint 10 ate a Research Phase II. Escrito durante
um periodo de espera genuina (duas linhas promissoras, `TASK-PAYOFF-002`
e `TASK-ALT-006`, estao bloqueadas por calendario, nao por decisao).
Nao introduz nenhum resultado novo -- e uma sintese do que ja foi
publicado em `reports/`, `docs/pre_registers/`, e
`project_control/DECISIONS.md`.

## 1. Sumario executivo

Nesta sessao, mais de uma dezena de tasks, agrupadas em nove familias
tematicas distintas (A, Funding Carry, TSMOM, C/TSREV, D/Payoff
Engineering, E/Cross-Sectional, e as Familias G/F/J da Research Phase
II), foram pre-registradas, implementadas, rodadas com dado real, e
fechadas com disciplina cientifica consistente. **Nenhuma produziu uma
estrategia economicamente viavel sob custo realista.** Isso e um resultado, nao
uma falha de processo -- o valor entregue nesta sessao nao e uma
estrategia, e um metodo de pesquisa reproduzivel, rapido, e resistente
a p-hacking, mais um mapa detalhado de por que este universo (20
perpetuos USD-M liquidos, 2023-06 a 2026-05) nao rende edge facil.

Achado mais importante da fase inteira: **a informacao mais forte
encontrada nao foi direcional -- foi de volatilidade/regime**
(`TASK-ALT-003`, rho ate 0,30), e ela revelou algo nao-obvio sobre o
proprio TSREV (`TASK-ALT-004`): o edge da estrategia esta inteiramente
concentrado no regime de alta volatilidade, nao diluido nele.

## 2. Familias de fatores classicos de preco (OHLCV) -- todas fechadas NAO PASSA

| Familia | Hipotese | Resultado real | Relatorio |
|---|---|---|---|
| A -- Mean Reversion (Kalman/OU) | Reversao estatistica de pares via Kalman+OU | Encerrada (ADR-0010), sem edge liquido exploravel apos 3 tentativas independentes | `signal_diagnostics.md`, `signal_entry_filter_experiment.md` |
| Funding Carry | Cross-sectional carry por funding rate, long/short top/bottom-K | K=5 fase 1: PF 0,840. Fase 2 incremental: PF 1,0904, near-miss de 0,0096 do gate 1,10 | `funding_carry_backtest.md`, `funding_carry_incremental_backtest.md` |
| TSMOM | Donchian breakout 24h + ATR trailing stop | Win rate 34,3% (supera piso), mas PF 1,005 vs gate 1,20; drawdown ~10,5x o lucro liquido | `tsmom_backtest_final.md` |
| C -- TSREV | Reversao simples z=r/sigma, celula primaria 24h | PF 1,0143 vs gate 1,05; win rate estavel 52,7% IS/OOS (sinal real) mas drawdown ~6x o baseline buy-and-hold | `tsrev_backtest_final.md` |
| E -- Cross-Sectional Momentum (CS-001) | Replicacao fiel Liu&Tsyvinski (2021), momentum semanal | PF 0,98; gross tambem negativo -- nem o efeito bruto existe | `cs_momentum_backtest_final.md` |
| E -- Cross-Sectional Mean Reversion (CS-002) | Reversao 24h, horizonte deliberadamente distinto do mirror de CS-001 | PF 0,94 (OOS decisivo), 1,00 (IS), 0,98 (full) -- nunca cruza o gate 1,10 em nenhum corte; gross tambem negativo | `cs_reversion_backtest_final.md` |

Achado transversal: a assimetria **SHORT >> LONG** aparece de forma
independente em pelo menos dois diagnosticos distintos (Z-score
cross-sectional e Payoff Engineering sobre o TSREV) -- SHORT net
+37.938bps/WR 55,2% vs LONG -30.248bps/WR 50,5%. E o unico padrao
direcional que se repete de forma nao-planejada entre familias
diferentes.

## 3. Payoff Engineering (Research Family D) -- diagnostico, nao estrategia

`TASK-PAYOFF-001` (`tsrev_payoff_attribution.md`) decompos as 3.941
trades OOS do TSREV primario:

- Drawdown e **difuso**, nao causado por outliers -- pior trade
  individual so -33,8bps; e preciso 19% das trades perdedoras para
  50% da perda total.
- SHORT >> LONG (ver acima).
- BTCUSDT/ETHUSDT (mais liquidos) sao os 2 piores symbols -- leitura de
  eficiencia de mercado que se repete depois na Familia F (ver abaixo).

`TASK-PAYOFF-002` (SHORT-only, `TASK-PAYOFF-002.md`) esta
pre-registrada e travada, aguardando OOS genuinamente novo (>=500
trades, ~1,5 meses estimados a partir de 2026-06-01).

## 4. Research Phase II -- Alternative Information (nenhuma hipotese so-OHLCV)

| Familia | O que foi medido | Resultado |
|---|---|---|
| G -- Funding Structure | 4 features causais de funding vs retorno futuro 24h | SEM_INFORMACAO. Near-miss notavel: `funding_price_divergence` rho=0,0248 (limiar 0,03), estavel em 3 subperiodos |
| F -- Open Interest | 5 features causais de OI (Binance `metrics`, download real de 21.920 arquivos) | SEM_INFORMACAO. `oi_delta`/`oi_acceleration` mostram DECAIMENTO monotonico (edge historico desaparecendo) |
| J -- Regime Detection | 6 features de volatilidade/contexto vs retorno absoluto futuro | **TEM_INFORMACAO real e forte** -- `realized_vol_168h` rho=0,30, `realized_vol_24h` rho=0,29, consistente em 3 subperiodos |
| J-operacional (ALT-004) | Bloquear entradas TSREV em alta-vol (filtro de risco ingenuo) | NAO_PASSA -- **piorou** a economia (net +7.690 -> -6.110bps) |
| G near-miss em novo OOS (ALT-005) | `funding_price_divergence` em 2026-06 (dado genuinamente novo, nunca visto antes) | NAO_PROMOVE -- sinal **inverteu** (rho=-0,118 vs +0,023/+0,028 originais) |

Decompondo o resultado de `TASK-ALT-004`: as 1.187 trades excluidas
(alta-vol) tinham net +13.800,78bps isoladas -- mais que o lucro
original inteiro da estrategia. As 2.758 mantidas (baixa/media vol) sao
net -6.110,64bps isoladas. **O edge do TSREV esta inteiramente dentro
do regime de alta volatilidade.**

`TASK-ALT-006` (TSREV restrito a alta-vol, o filtro exatamente
inverso) esta pre-registrada e travada, aguardando OOS genuinamente
novo (>=750 trades, ~2,3 meses estimados) -- a hipotese foi construida
diretamente do numero visto em ALT-004, entao nao pode ser testada no
mesmo periodo sem contaminar o resultado.

## 5. Padroes que se repetem entre familias independentes

Tres achados aparecem de forma nao-planejada em mais de uma linha de
pesquisa distinta -- o tipo de coincidencia que vale mais atencao do
que um achado isolado:

1. **SHORT >> LONG**: Z-score cross-sectional (diagnostico informal) e
   Payoff Engineering (TSREV) concordam de forma independente.
2. **Eficiencia crescente com liquidez**: BTCUSDT/ETHUSDT sao os piores
   symbols tanto no Payoff Engineering (TSREV) quanto no decaimento de
   `oi_delta` (Familia F) -- os ativos mais liquidos/mais arbitrados
   erodem edge mais rapido.
3. **Volatilidade concentra edge, nao dilui**: o unico caso onde
   informacao real (regime) foi medida diretamente (Familia J) mostrou
   o oposto da intuicao de risk-off -- confirmado numericamente ao
   decompor `TASK-ALT-004`.

## 6. O que fica bloqueado (por calendario, nao por decisao)

```text
TASK-PAYOFF-002: aguardando >=500 trades novos (~1,5 meses, a partir de 2026-06-01)
TASK-ALT-006:    aguardando >=750 trades novos (~2,3 meses, a partir de 2026-06-01)
```

Ambas reusam o mes de 2026-06 (ja baixado, checksum-verificado por
`TASK-ALT-005`) e so precisam de mais meses completos passarem.

## 7. O que fica formalmente adiado (por decisao, nao por bloqueio tecnico)

```text
Familia H (Order Flow/L2): dado tick-level, ~17,98GB/mes, infraestrutura
    nova -- ultimo avenue nao-explorado da Fase II, deliberadamente
    nao iniciado (custo alto demais para justificar sem esgotar
    alternativas mais baratas primeiro).
Familia I (Liquidation Dynamics): BLOQUEADA -- Binance nao publica mais
    liquidationSnapshot em bulk historico (confirmado via probe real).
    So viavel via captura forward-only (WebSocket forceOrder, sem
    historico) ou fornecedor terceiro, nenhum autorizado.
CS-003/004/005 (Residual Momentum, PCA Stat Arb, Ensemble): backlog nao
    cancelado da Research Family E, usuario ja indicou preferencia por
    nao continuar aprofundando fatores classicos de preco.
Mudanca de universo (small-caps/menor liquidez): adiada para preservar
    comparabilidade com toda a pesquisa ja feita.
```

## 8. O que a sessao construiu como infraestrutura reutilizavel

Alem dos resultados negativos, esta sessao produziu um motor de
pesquisa que reduz o custo de testar a proxima hipotese a dias, nao
semanas:

```text
src/research/info_content.py       -- diagnostico causal de conteudo
                                       informacional (Spearman + 
                                       estabilidade em subperiodos),
                                       reusado em G, F, e no design de J.
src/research/tsrev.py              -- infraestrutura de reversao/momentum
                                       cross-sectional reusada por CS-001/002.
Disciplina de pre-registro         -- ADR + doc de pre-registro travando
                                       hipotese primaria/gate/split ANTES
                                       de qualquer codigo, em 100% das
                                       linhas desta sessao.
Gatilhos de dados explicitos       -- PAYOFF-002 e ALT-006 sao os primeiros
                                       casos deste projeto de "pre-registrar
                                       agora, bloquear execucao ate dado
                                       novo existir" -- um padrao formal
                                       contra reuso de amostra contaminada.
```

## 9. Proxima decisao

Nenhuma acao de codigo esta pendente agora. Quando `TASK-PAYOFF-002`
ou `TASK-ALT-006` atingirem seus gatilhos (a partir de agosto/2026,
estimado), os comandos de retomada exatos ja estao travados em seus
respectivos pre-registros. Ate la, a decisao de reconsiderar Familia H
(Order Flow), investir em captura forward-only para Familia I, ou
encerrar a Research Phase II como um todo pertence ao usuario.
