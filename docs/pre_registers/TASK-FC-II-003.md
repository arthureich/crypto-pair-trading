# TASK-FC-II-003 - Definicao e pre-registro: Microestrutura em HORIZONTE CURTO (book imbalance da Familia H vs retorno 1h/4h)

## Status

ACCEPTED (locked) - travado em 2026-07-10 antes de qualquer resultado.
Sob ADR-0027. Diagnostico de conteudo informacional (estilo Fase II),
sem gate economico. "Tem informacao" ou "nao tem".

## Motivacao

Toda a Research Phase II fixou o horizonte de retorno futuro em 24h
(ADR-0019). Isso e longo para microestrutura: a teoria diz que o
desbalanceamento do livro (order book imbalance) preve retorno de CURTO
prazo, nao de um dia. O pre-registro da Familia H (TASK-ALT-007)
registrou explicitamente horizonte curto como candidato de FUTURA task,
nao testado. Alem disso, `imbalance_price_divergence` foi o near-miss da
Familia H em 24h (rho=0,0208, o unico com trajetoria CRESCENTE nos 3
subperiodos). Prior mais alto que a basis. Custo ~zero (dado ja
normalizado: `sprint_alt_book_depth_202306_202605.csv.gz`).

## Metodologia (reusa ADR-0019; muda SO o horizonte-alvo)

```text
Features: as 5 MESMAS da Familia H, VERBATIM (mesma construcao/codigo):
  book_imbalance_1pct, book_imbalance_5pct, depth_concentration,
  depth_change_24h, imbalance_price_divergence.
Nenhuma feature nova; nenhum ajuste de construcao. A UNICA mudanca em
relacao a TASK-ALT-007 e o horizonte do TARGET.

Target: forward_return_h[t] = log_price[t+h] - log_price[t], para
  h in {1h, 4h} (grid pequeno e pre-comprometido; 5 features x 2
  horizontes = 10 celulas declaradas antes do resultado).

3 subperiodos e limiar identicos a Fase II (2023-06/2024-05, 2024-06/
2025-05, 2025-06/2026-05; |rho|>=0,03 E sinal consistente nos 3).
A consistencia de sinal nos 3 subperiodos e a defesa contra
multiple-testing: um sinal espurio raramente mantem o sinal em 3
janelas independentes de 12 meses.
```

## Universo e amostra

```text
20 symbols; painel empilhado; join bookDepth-normalizado x bars por
(symbol, open_time), identico a TASK-ALT-007.
```

## Invariantes

```text
- Features causais (mesma construcao da Familia H; depth_change e
  imbalance_price_divergence ja usam shift/lag). Target e o unico dado
  posterior a t.
- Subperiodos e limiar 0,03 nao reparticionados/re-tunados.
- Sem gate economico, estrategia, execucao ou acao real.
- Grid de 10 celulas fixo antes do resultado; qualquer feature/horizonte
  que passe e CANDIDATO a validacao OOS separada, NUNCA um veredito aqui.
- Sem novo download.
```

## Fora de escopo

```text
- Desenhar estrategia sobre um hit (task separada, pre-registrada, com OOS).
- Novas features de book alem das 5 da Familia H.
- Horizontes alem de {1h,4h} (varrer muitos horizontes seria
  multiple-testing; o grid fica travado em 2).
- Mutual information / nao-linear.
```
