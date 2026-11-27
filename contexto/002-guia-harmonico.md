# 002. Guia harmônico na geração da melodia

## Problema
A melodia era gerada pelo modelo sem nenhuma informação sobre os acordes escolhidos pelo usuário. A progressão e a melodia eram independentes, então a melodia não "conversava" com a harmonia.

## Causa
O modelo foi treinado só com melodias monofônicas (tokens `NOTE`, `DURATION`, `REST`). Não existe nenhum token de acorde nos dados, então ele não pode aprender a relação melodia–harmonia. Resolver isso na origem exige retreino com tokens de acorde (ver `PENDENCIAS.md`).

## O que foi alterado
- **Novo** `src/harmonia_guia.py`:
  - `criar_guia_harmonico()`: ajusta os logits **antes de cada nota**. Proíbe notas fora da tonalidade e fora da tessitura (MIDI 52 a 88) e soma um bônus às notas que pertencem ao acorde do compasso (+3,0 em tempo forte, +1,5 nos demais).
  - `metricas_melodia()`: mede a fração de notas no acorde, no tempo forte, na escala, alturas distintas, amplitude e repetições.
- `transformer_model.py` e `lstm_model.py`: `gerar()` recebe o parâmetro opcional `ajustar_logits`. O Transformer também passa a contar o tempo em beats (necessário para saber em que compasso a nota cai).
- `src/gerador.py`: `compor(..., guiar_por_harmonia=True)`.
- `app.py`: checkbox **"Guiar melodia pela harmonia"** (ligado por padrão).
- **Novo** `scripts/avaliar_geracao.py`: compara os cenários A (estado original), B (vocabulário corrigido) e C (corrigido + guia).

## Como foi verificado
30 composições, Transformer, Dó Maior, 120 BPM, 20 s, temperatura 0,85:

| Métrica | A) original | B) vocab. certo | C) vocab. certo + guia |
|---|---|---|---|
| Notas no acorde do compasso | 53% | 51% | **65%** |
| Notas em tempo forte no acorde | 100% | 88% | 90% |
| Alturas distintas | 5,2 | 7,6 | **9,2** |
| Repetições consecutivas | 25,7% | 1,3% | 3,7% |

No cenário A, os 100% em tempo forte vêm de poucas notas e não indicam melodia melhor. O usuário relatou melhora grande ao ouvir.

Resultado salvo em `relatorios/avaliacao_geracao_transformer.json`.

## Limitações
- É um **ajuste na amostragem**, não aprendizado. Os pesos (+3,0 e +1,5) foram escolhidos por julgamento, não otimizados.
- O guia só considera a **harmonia** (quais notas). **Não alinha a melodia ao tempo da base** (relato do usuário: "a melodia parece não conversar com o tempo"). Ver `PENDENCIAS.md`.
- Medido só no Transformer.
