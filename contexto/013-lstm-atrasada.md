# 013. LSTM atrasada em relação à base de acordes

## Problema
Depois de 012 (durações mais longas), o usuário relatou que a LSTM soa "atrasada" em relação aos acordes.

## Causa (medida com `scripts/medir_tempo.py --modelo lstm --n 20 --duracao 20`)
A LSTM não tinha guia de ritmo (`peso_ritmo = 0`, ver 008). Só 37% das notas começavam no beat e 22,6% começavam fora da grade de 1/4 (colcheia de 1/8 ímpar). Com notas mais longas (012), esse desalinhamento fica audível. Transformer, com guia 3,0: 57% no beat, 0% fora de 1/4.

## O que foi alterado
- `src/gerador.py`, `_gerar_neural()`: `peso_ritmo` da LSTM passou de 0,0 para 1,0 (Transformer segue em 3,0). Pesos altos deixavam tudo em semínimas (008), por isso o valor baixo.

## Resultado (20 gerações, Dó Maior, 120 BPM, 20 s)
| | Antes | Depois |
|---|---|---|
| Notas no beat | 36,9% | **70,6%** |
| Fora da grade de 1/4 | 22,6% | **0,1%** |
| Início de compasso | 10,8% | 18,3% |

Durações (15 gerações): 1/2 beat 55%, 1 beat 35%, 2 beats 9%, 1/4 beat 1%; ~47 notas por geração.

## Limitações
- Medido, **não ouvido**. O peso 2,0 não foi testado (uma tentativa de automatizar o teste falhou).
- A fração de semicolcheias caiu a ~1%: o guia de ritmo e o viés de 012 somam efeitos. Se ficar lento demais, reduzir o viés de `DURATION_0.25` em `VIES_DURACAO_PADRAO`.
- `scripts/avaliar_geracao.py` monta o próprio guia, sem `peso_ritmo`, e por isso não reflete esta mudança. A harmonia foi remedida pelo `compor()` (20 gerações): notas no acorde 80%, tempos fortes 92%, repetições seguidas 5,5%, 10,4 alturas distintas. Não piorou.
- Reiniciar o `streamlit run`.
