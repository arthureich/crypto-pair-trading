# TASK-TSM-006 - Definicao e pre-registro: Linha 6 (execucao) -- encerramento fundamentado

## Status

ACCEPTED (locked) - travado 2026-07-12. Sob ADR-0031 (Programa de Melhoria do
TSM), Linha 6 (ultima). Encerramento FUNDAMENTADO em evidencia ja existente do
projeto (nao um build novo) -- ADR-0031 permite: "apos considerar esgotada cada
linha (com documentacao e justificativa), passe automaticamente para a proxima".

## Revisao de literatura / evidencia

- Melhorias de execucao (limit/maker vs taker, TWAP/VWAP, slicing, reducao de
  slippage/market-impact) rendem quando a estrategia e SENSIVEL a custo:
  alta frequencia, alto turnover, holding curto.
- Evidencia INTERNA que responde a linha:
  1. FC-II-007 (stress de custo do TSM): breakeven ~142 bps/PERNA; Sharpe cai
     so de 1,04 (0 bps) para ~0,90 (15 bps) e ~0,70 (50 bps). Turnover ~0,46
     por rebalance, rebalance de 5 dias. O TSM e ALTAMENTE INSENSIVEL a custo
     -- opera a 6-15 bps realistas, muito abaixo do breakeven.
  2. Sprint 10 Bloco 1: execucao passiva (LIMIT_MAKER_TTL) vs agressiva
     (MARKET_IOC) numa estrategia ANTERIOR nao resgatou o resultado
     (0/13, +27% de exposicao nao-preenchida) -- melhoria de execucao nao
     cria edge e ainda adiciona risco de nao-preenchimento.

## Hipotese e por que se encerra sem build

Hipotese seria: otimizar execucao (maker, slicing) melhora o net do TSM.
Mas o proprio TSM ja tem folga de custo enorme (breakeven 142 vs 6-15 bps
realistas); qualquer economia de execucao move o Sharpe em fracao de decimal
(a curva FC-II-007 mostra ~0,01-0,02 de Sharpe entre 6 e 15 bps). O ganho
POSSIVEL e minusculo e vem com complexidade e risco de nao-preenchimento
(licao Sprint 10). Por ADR-0031 regra 6 (preferir ganhos simples e robustos;
o ganho tem que justificar a complexidade), a linha NAO se justifica: o
ganho maximo teorico e desprezivel para uma estrategia lenta e cost-insensitive.

## Decisao (encerramento)

Linha 6 (execucao) ENCERRADA como NAO-JUSTIFICADA por evidencia existente, sem
novo build. Racional: TSM cost-insensitive (FC-II-007) + execucao passiva ja
mostrou nao resgatar edge (Sprint 10). Nenhuma promocao; nenhuma acao real.

Com isso o Programa de Melhoria do TSM (ADR-0031) cobre as 6 linhas:
1 regime (REJEITADO), 2 sizing (REJEITADO), 3 portfolio/ERC (CARREGADO p/ OOS),
4 meta-labeling (REJEITADO), 5 ensemble (ver TASK-TSM-005), 6 execucao
(encerrada, nao-justificada). Unico candidato vivo: ERC, OOS-gated.

## Fora de escopo

```text
- Qualquer simulador de execucao / microestrutura de ordens novo (nao
  justificado para estrategia lenta cost-insensitive).
- Acao real / live (proibido).
- Reabrir se: o TSM for operado a turnover MUITO maior (ex.: rebalance
  diario) -- ai execucao volta a importar; seria task propria pre-registrada.
```
