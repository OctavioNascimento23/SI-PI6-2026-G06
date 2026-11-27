# 010. LSTM treinada integrada e validada

## Situação
O grupo enviou o `modelos/modelo_lstm.pt` novo, treinado por 20 épocas no Colab (`relatorios/resultados_lstm.json`, `historico_lstm.csv`). Antes não havia LSTM treinada de verdade: a anterior era um checkpoint antigo, sem resultados.

## O que foi verificado
- **Carrega e gera nos 3 motores** (`GeradorMusical.compor`, Mi Menor, 100 BPM, 16 s): LSTM 19 notas, Transformer 32, Markov 29. Sem fallback para Markov.
- **Vocabulário compatível:** 140 tokens, o mesmo do Transformer e de `modelos/vocabulario.json`.
- **Métricas no conjunto de teste** (`relatorios/tabela_comparativa.csv`):

| Modelo | Acurácia | Top-5 | Perplexidade | F1 macro | AUC |
|---|---|---|---|---|---|
| Transformer | 0,644 | 0,918 | 3,22 | 0,417 | 0,982 |
| LSTM | 0,627 | 0,918 | 3,24 | 0,398 | 0,982 |

  Quase empatados. O Transformer leva vantagem de ~1,7 ponto de acurácia; em Top-5 e AUC são iguais.
- **Aderência à harmonia** (`scripts/avaliar_geracao.py --modelo lstm --n 30`, `relatorios/avaliacao_geracao_lstm.json`):

| Configuração | Notas no acorde | Tempos fortes no acorde | Repetições seguidas |
|---|---|---|---|
| vocabulário do checkpoint, sem guia | 47,3% | 54,0% | 46,4% |
| vocabulário do checkpoint, com guia harmônico | 78,4% | 88,5% | 37,5% |

  O guia harmônico (002) funciona na LSTM: +31 pontos de notas no acorde.
- **Diversidade da melodia** (`relatorios/tabela_comparativa.csv`, geração livre): a LSTM repete a mesma nota seguida em **43%** dos casos (real: 22%; Transformer: 3%), com 7,7 alturas distintas (real: 18,8; Transformer: 9,0) e amplitude de 11,8 semitons (real: 31,5). A LSTM é a mais monótona dos três.
- **Ritmo** (`scripts/medir_tempo.py --modelo lstm --n 20`, `relatorios/medida_tempo_lstm.json`): 32,8% das notas caem no beat (antes, com a LSTM antiga: 42,3%, em `medida_tempo_lstm_final.json`). Piora com o modelo novo, em linha com o que 008 já previa: a LSTM não tem guia de ritmo (`peso_ritmo=0`).

## Limpeza feita junto
- Removidos `dados_treino.zip` e `dados_processados_prontos.zip` da raiz (116 MB): tinham os mesmos 17.737 arquivos e ninguém os referenciava. O conteúdo já existe em `dados_processados/`, e o notebook gera seu próprio zip no Drive.
- Removidos `saida_temp/teste.wav` e os arquivos temporários de teste.
- Removidos `relatorios/medida_tempo_*_antes.json` e `medida_tempo_transformer_depois.json`: eram medições intermediárias da 008; ficam os `*_final.json`.
- Apagados os `__pycache__`.

## Limitações / pendências
- **Não foi ouvida.** Os números dizem que a LSTM é mais repetitiva e pior de ritmo; só a escuta confirma se isso incomoda.
- O ritmo da LSTM só pode melhorar com guia de ritmo, e 008 mostrou que pesos ≥ 2 deixam tudo em semínimas. É decisão do grupo.
- Para a apresentação, o Transformer continua sendo o motor mais recomendado.
