# 011. LSTM "bugada": melodia curta e presa em uma nota

## Problema
Relato do usuário, com print: com a LSTM (Mi Menor, 110 BPM, 16 s) a melodia tinha 24 notas, todas **Mi5**, todas muito curtas, e acabava em ~4 s dos 16 s pedidos. O resto do tempo ficava em silêncio.

## Causa (medida, 30 gerações, mesmos parâmetros do print)
Dois defeitos independentes na `gerar()` da LSTM, que o Transformer já tratava:

1. **Melodia curta.** O número de tokens gerados era fixo (`duracao * 4 + 8`). A LSTM escolhe muitas vezes `DURATION_0.12` (1/8 de beat). Com notas tão curtas, os tokens acabavam antes da duração pedida. Em **13 de 30 gerações** a melodia cobria menos de 50% do tempo; a cobertura média era **56%** (Transformer: 98%). O Transformer evita isso penalizando `DURATION_0.12` em 2,0 no logit.
2. **Nota repetida.** A LSTM não tinha penalidade de repetição (o Transformer tem, 1,35). Média de **48%** das notas repetindo a anterior (Transformer: 4%).

## O que foi alterado
- `src/modelos/lstm_model.py`, em `gerar()`:
  - penalidade de −2,0 no logit de `DURATION_0.12` (mesma proteção do Transformer);
  - penalidade de repetição de −1,0 nos logits das notas dos últimos 8 tokens (`penalidade_repeticao`, só afeta notas, nunca durações);
  - parâmetro opcional `beats_alvo`: continua gerando até a melodia cobrir a duração pedida (`num_tokens` vira só teto de segurança);
  - o relógio interno passou a tratar `0.12` como 0,125 beat.
- `src/gerador.py`: para a LSTM, passa `beats_alvo = duração × bpm / 60` e um teto de tokens 8 vezes maior. Transformer e Markov não mudaram.

## Como foi verificado (30 gerações, Mi Menor, 110 BPM, 16 s)

| | Antes | Depois | Transformer |
|---|---|---|---|
| Cobertura média da duração | 56% | **98%** | 98% |
| Gerações com menos de 50% | 13/30 | **0/30** | 0/30 |
| Notas repetidas em sequência | 48% | **13%** | 4% |

Com `scripts/avaliar_geracao.py --modelo lstm --n 20` (Dó Maior, 120 BPM, 20 s, com guia harmônico):

| | Antes (010) | Depois |
|---|---|---|
| Notas no acorde | 78,4% | **79,5%** |
| Tempos fortes no acorde | 88,5% | **93,9%** |
| Repetições seguidas | 37,5% | **4,9%** |
| Alturas distintas | 5,2 | **10,1** |

A harmonia não piorou. O app roda com LSTM selecionada sem erros.

## Limitações / pendências
- **Ritmo da LSTM não mudou:** continua em ~32% das notas no beat (`medir_tempo.py`), pelo motivo de 008 (sem guia de ritmo; pesos altos deixam tudo em semínimas). Não mexi nisso.
- Os números de 010 sobre repetição e diversidade da LSTM (43%, 7,7 alturas) eram do modelo **sem** estas correções; `relatorios/avaliacao_geracao_lstm.json` foi regravado com os valores novos. Em `relatorios/tabela_comparativa.csv` continuam os números do treino, que refletem o modelo cru.
- As penalidades (−2,0 e −1,0) são escolha minha, validadas por medida e **não de ouvido**.
