# TSMOM Donchian Breakout Backtest (TASK-TSMOM-001) - Final Result

Status: real result for the single pre-registered configuration in `docs/pre_registers/TASK-TSMOM-001.md`. No parameter sweep.

**GATE: NAO_PASSA**

## Configuration

```text
{
  "donchian_window_hours": 24,
  "atr_period_hours": 14,
  "atr_stop_multiplier": 3.0,
  "cost_bps_roundtrip": 12.0,
  "profit_factor_gate": 1.2,
  "min_win_rate": 0.3
}
```

## Aggregate result

| Metric | Value |
|---|---:|
| Total trades | 11149 |
| Resolved trades | 11132 |
| Open at end (excluded) | 17 |
| Win rate | 34.30% |
| Gross PnL (bps) | 141771.26 |
| Cost (bps) | 133584.00 |
| Net PnL (bps) | 8187.26 |
| Net profit factor | 1.01 |
| Max drawdown (bps) | 85654.62 |
| Gate (PF>=1.20 and win_rate>=30%) | NAO_PASSA |

## Per-symbol breakdown

| Symbol | Trades | Resolved | Open at end | Wins | Win rate | Net PnL (bps) |
|---|---:|---:|---:|---:|---:|---:|
| ADAUSDT | 554 | 553 | 1 | 187 | 33.82% | 6019.27 |
| APTUSDT | 557 | 557 | 0 | 183 | 32.85% | -4668.85 |
| ARBUSDT | 557 | 556 | 1 | 192 | 34.53% | 3323.76 |
| ATOMUSDT | 575 | 574 | 1 | 208 | 36.24% | -7722.55 |
| AVAXUSDT | 566 | 566 | 0 | 206 | 36.40% | 6382.40 |
| BCHUSDT | 540 | 539 | 1 | 173 | 32.10% | -19327.62 |
| BNBUSDT | 558 | 558 | 0 | 187 | 33.51% | 5457.98 |
| BTCUSDT | 565 | 564 | 1 | 185 | 32.80% | -1162.28 |
| DOGEUSDT | 527 | 526 | 1 | 186 | 35.36% | 16938.94 |
| DOTUSDT | 548 | 547 | 1 | 191 | 34.92% | -1652.03 |
| ETCUSDT | 567 | 566 | 1 | 176 | 31.10% | -13773.66 |
| ETHUSDT | 542 | 541 | 1 | 188 | 34.75% | 3752.02 |
| LINKUSDT | 567 | 566 | 1 | 202 | 35.69% | 371.48 |
| LTCUSDT | 555 | 554 | 1 | 180 | 32.49% | -15320.52 |
| OPUSDT | 563 | 562 | 1 | 193 | 34.34% | -2610.72 |
| SOLUSDT | 571 | 570 | 1 | 203 | 35.61% | 8520.01 |
| SUIUSDT | 548 | 547 | 1 | 195 | 35.65% | 13788.04 |
| TRXUSDT | 600 | 599 | 1 | 223 | 37.23% | 9038.18 |
| UNIUSDT | 564 | 563 | 1 | 185 | 32.86% | -7714.48 |
| XRPUSDT | 525 | 524 | 1 | 175 | 33.40% | 8547.89 |

## Conclusão

**Gate NAO PASSA, e nao por pouco.** Profit factor liquido de 1,005 esta a
0,195 do limiar de 1,20 -- muito mais distante que o quase-empate da
TASK-FUND-003 (que faltou so 0,0096). O win rate (34,30%) de fato supera o
piso de 30% pre-registrado, confirmando que a assimetria "cortar perdas
rapido, deixar ganhos correrem" esperada de um sistema de trailing stop
realmente se manifestou (nao seria possivel ter apenas 34% de trades
ganhadores e ainda assim terminar com profit factor perto de 1,0 sem essa
assimetria) -- mas a assimetria observada e fraca demais: o PnL bruto
(141.771,26bps) e absorvido quase inteiramente pelo custo acumulado de
11.132 trades a 12bps cada (133.584,00bps), sobrando apenas 8.187,26bps
liquidos ao longo de 3 anos e 20 simbolos.

**O drawdown maximo (85.654,62bps) e ~10,5x o PnL liquido total.** Mesmo
ignorando o gate formal, isto por si so descreveria uma estrategia com
perfil de risco/retorno inaceitavel -- o caminho da equity teria que
suportar uma perda acumulada dez vezes maior que o lucro final antes de
qualquer recuperacao.

**Heterogeneidade por simbolo e real, mas nao e evidencia de um recorte
melhor escondido.** 9 de 20 simbolos terminam com PnL liquido negativo
(BCHUSDT -19.328, LTCUSDT -15.321, ETCUSDT -13.774, ATOMUSDT -7.723,
UNIUSDT -7.714, entre outros), 11 terminam positivos (DOGEUSDT +16.939,
SUIUSDT +13.788, TRXUSDT +9.038, XRPUSDT +8.548, AVAXUSDT +6.382, entre
outros). Isto e variancia esperada entre ~550 trades por simbolo em 3
anos, nao uma segmentacao pre-registrada -- filtrar ex-post para "so os
simbolos que deram lucro" seria exatamente o p-hacking que este projeto
evita desde a ADR-0010.

**Decisao:** aceitar NAO PASSA como resultado final desta hipotese
(Donchian breakout + ATR trailing stop, janela 24h, sem profit target
fixo). Nenhum parametro (janela, multiplicador de stop, custo, limiar de
gate) muda depois de ver este resultado, pela mesma disciplina de
pre-registro que ja governou Signal Iteration 1 (ADR-0010) e Funding
Carry (ADR-0013). Decisao de como prosseguir pertence ao usuario.
