# 001. Vocabulário incompatível entre o app e os modelos

## Problema
As melodias geradas pelo app tinham poucas alturas distintas, muitas notas repetidas em sequência e amplitude artificial (relatado em `relatorios/feedback_testes_app.md`).

## Causa
O Transformer e a LSTM foram treinados no Colab com um vocabulário de **140 tokens**. O app (`GeradorMusical`) carregava outro arquivo, `modelos/vocabulario.json`, com **74 tokens**. O modelo prevê um **ID**; o app o traduzia para texto com o mapa errado. Cada ID virava uma nota ou duração diferente da pretendida, o que deixava a melodia repetitiva e sem relação com o que o modelo aprendeu.

Os dois vocabulários têm a mesma "forma" (`NOTE_x`, `DURATION_x`, `REST_x`), então nenhum erro foi levantado: o problema era silencioso.

## O que foi alterado
- `src/modelos/transformer_model.py` e `src/modelos/lstm_model.py`: `carregar()` agora guarda o vocabulário embutido no checkpoint em `modelo.vocabulario`.
- `src/gerador.py`: novo método `_gerar_neural()`, que usa o vocabulário do próprio checkpoint (e só recorre ao arquivo se o checkpoint não tiver um).

O checkpoint já continha o vocabulário correto (`vocabulario` dentro do `.pt`); só não era usado.

## Como foi verificado
`scripts/avaliar_geracao.py` (30 composições, Dó Maior, 120 BPM, 20 s, temperatura 0,85), Transformer:

| Métrica | Antes (vocab. errado) | Depois (vocab. do checkpoint) |
|---|---|---|
| Repetições consecutivas | 25,7% | 1,3% |
| Alturas distintas | 5,2 | 7,6 |
| Amplitude (semitons) | 26 | 15,6 |

Para referência, as melodias reais do conjunto de teste têm 22% de repetição consecutiva.

## Limitações
- Vale para o Transformer. A LSTM usa o mesmo caminho de código, mas não foi medida com este script.
- Os arquivos `modelos/vocabulario.json` e `dados_processados/sequencias/vocabulario.json` continuam divergentes entre si. Não foi alterado porque o app agora ignora o primeiro quando há checkpoint.

## Efeito colateral encontrado
O `.gitignore` tem `modelos/`, que também ignora `src/modelos/` (o código de Markov, LSTM e Transformer). Esses arquivos nunca foram versionados. Ver [`PENDENCIAS.md`](PENDENCIAS.md).
