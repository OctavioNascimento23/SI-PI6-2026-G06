# 009. Só Dó Maior funcionava bem: melodia gerada na região de Dó e transposta

## Problema
Relato do usuário: com a configuração anterior ficou "perfeito" em Dó Maior, mas ao mudar a tonalidade a qualidade se perdeu. Também disse que mudar BPM/progressão "não afetou".

## Causa (medida)
Os dados de treino **não foram transpostos** para uma tonalidade comum (nenhuma transposição em `scripts/03` e `04`; nas 400 melodias de treino que medi, a classe de altura mais comum é Mi/Sol, e as notas de Dó Maior cobrem 74% do total). Os modelos aprenderam padrões ligados à região de Dó / Lá menor.

Para comparar sem depender da tonalidade, medi o quanto o Transformer "estranha" (NLL por nota) as próprias melodias geradas, **depois de levá-las de volta a Dó**:

| Tonalidade | NLL por nota (menor é melhor) |
|---|---|
| Dó Maior / Lá Menor | 0,96 |
| Sol Maior / Mi Menor | 1,09 |
| Si Maior | 1,14 |
| Fá, Mi Maior, Dó Menor | 1,18 a 1,19 |
| Ré Maior | 1,21 |

Também medi a fração da probabilidade do modelo que cai dentro da escala escolhida: 98% em Dó Maior, mas 85% a 90% em Ré, Mi e Si Maior. Ou seja, o guia e o filtro precisam "forçar" a escala nas outras tonalidades, o que gera notas que o modelo não considerava naturais.

## O que foi alterado
- `src/teoria_musical.py`: `deslocamento_para_do(tonalidade)` e `transpor_tokens(tokens, semitons)`.
- `src/gerador.py` (`compor`): a melodia (Transformer e LSTM) agora é **gerada em Dó Maior**, com os acordes e a guia harmônica levados para essa região (`classes_pitch` deslocadas), e só depois **transposta** para a tonalidade escolhida. O filtro de escala roda antes e depois. Tonalidades menores usam a relativa maior (Lá Menor = 0 de deslocamento), coerente com a 007.
- Markov: não foi mexido (não usa acordes).

## Como foi verificado
- Repeti a medida de NLL depois da mudança: **0,96 em todas as 9 tonalidades testadas** (igual a Dó Maior). Isso é esperado, porque o modelo passa a ver sempre a mesma região; mostra que a transposição está consistente, não que soa melhor.
- Transformer, 12 tonalidades, 6 gerações cada, progressão padrão: 100% das notas na escala; notas no acorde 68% e 84% nos tempos fortes em todas as tonalidades (Dó Maior mostrou 72% / 87%; a primeira geração de um processo saiu diferente da mesma semente repetida depois; Dó Maior repetida deu os mesmos tokens que Lá Menor. Não investiguei a causa dessa diferença na primeira chamada, provavelmente algo aleatório na carga inicial do modelo, mas é hipótese).
- Acordes das progressões: `scripts/testar_progressoes.py` segue em 84 combinações, 0 problemas.

## Sobre "BPM e progressão não afetaram" (medido, sem mudança de código)
- **BPM afeta**: MIDI gravado em 60, 120 e 180 BPM; o 1º acorde dura 4,0 s, 2,0 s e 1,33 s; número de notas da melodia 22, 35 e 45; a duração do WAV é a mesma (20,5 s), pois a duração em segundos é fixa.
- **Progressão afeta os acordes e atrai a melodia**: nas 7 progressões, as notas caem nos acordes certos em 69% a 76% dos casos, contra 43% a 61% quando comparadas aos acordes de outra progressão. A atração é **moderada**: é um bônus no guia, não uma regra rígida. Se a diferença não é audível, o motivo provável é esse (hipótese, não ouvi).

## Limitações / pendências
- **Não ouvi o áudio** nem abri o app. Só medi pelas métricas acima.
- A **LSTM** continua gerando às vezes uma altura só (mínimo de 1 altura distinta em gerações, inclusive em Dó Maior **sem** a transposição; não é efeito da mudança). Não investiguei a causa. O treino da LSTM está em `PENDENCIAS.md`.
- A transposição muda o registro da melodia (pitch médio de ~59 a ~69 conforme a tonalidade). Não verifiquei se alguma tonalidade fica desconfortável de ouvir.
- Se o grupo quiser resolver pela raiz, falta **transpor os dados para uma tonalidade comum no treino** e retreinar, o que não foi feito.
