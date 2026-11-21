# Instruções para atualizar o `Documentação_PI_VI_G06.docx`

Este documento é o roteiro para quem for editar o docx (outro modelo de IA ou pessoa). Ele não contém resultados. Todo valor marcado como `[PREENCHER: ...]` deve vir de uma execução real do notebook `notebooks/treinamento_google_colab.ipynb` ou de `relatorios/*.json`.

**Regra principal:** não escrever número que não tenha sido medido. Se um valor não existir, manter o campo marcado e registrar o motivo.

## 1. Feedback do professor a atender

Texto recebido (resumo fiel):

1. Faltam resultados dos outros modelos após as evoluções: **LSTM** e **modelo de Markov**.
2. Usar as **métricas específicas do tipo de problema** para avaliação numérica, em vez de julgamento por ouvido ("bom" ou "ruim").
3. Treinar com **mais padrões** (dados). Cinco horas de treino é pouco para resultados consistentes. Usar o máximo de padrões possível.

## 2. Tipo de problema e métricas aplicáveis

O sistema gera melodias token a token. Isso é **modelagem de linguagem autorregressiva**: a cada passo, o modelo escolhe o próximo token entre as classes do vocabulário. Por isso, as métricas de classificação multiclasse e a perplexidade são as aplicáveis.

| Categoria do professor | Aplica-se? | Justificativa |
|---|---|---|
| Classificação | **Sim** | Previsão do próximo token é uma classificação multiclasse. |
| Detecção de anomalias | Não | Não há rótulo de anomalia nem tarefa de detecção. |
| Regressão | Não | A saída é categórica (token), não contínua. |
| Clusterização | Não | Não há agrupamento não supervisionado como objetivo. |
| Sistemas de recomendação | Não | Não há ranking de itens para usuário. |
| Visão computacional | Não | Não há imagens. |
| PLN / Fala | Parcial | O domínio é texto simbólico musical (tokens), não linguagem natural nem áudio. Usar **perplexidade** como métrica de modelagem de linguagem. |

**Métricas de classificação (Transformer, LSTM e Markov, nos três conjuntos):**
- Matriz de confusão (classes agregadas; o vocabulário tem 129 tokens, então a matriz completa não cabe no documento. Apresentar as 10 classes mais frequentes e a matriz completa em anexo CSV).
- Acurácia, Precisão (macro), Recall (macro), F1-Score (macro).
- Curva AUC-ROC (one-vs-rest, macro).
- Top-5 (acurácia top-5) e perplexidade, como métricas complementares de linguagem.

**Métricas NÃO aplicáveis (não listar como resultado):** Jaccard, R2, MSE, RMSE, MAE, Elbow, Silhouette, Davies-Bouldin, Calinski-Harabasz, Precision@K, Recall@K, NDCG@K, IoU, AP, mAP. Se o docx já citar alguma delas como resultado, remover e explicar em uma linha por que não se aplicam.

## 3. Onde atualizar no docx

Manter a estrutura atual (seções 5 a 10). Alterar só o conteúdo.

### 3.1 Seção 9 (Modelos de IA e métricas)

Adicionar ou atualizar as subseções para **Transformer, LSTM e Markov**.

Para cada modelo, incluir uma tabela com as colunas **Treino | Validação | Teste** e as linhas:

| Métrica | Treino | Validação | Teste |
|---|---|---|---|
| Loss (cross-entropy) | [PREENCHER] | [PREENCHER] | [PREENCHER] |
| Perplexidade | [PREENCHER] | [PREENCHER] | [PREENCHER] |
| Acurácia | [PREENCHER] | [PREENCHER] | [PREENCHER] |
| Top-5 | [PREENCHER] | [PREENCHER] | [PREENCHER] |
| Precisão (macro) | [PREENCHER] | [PREENCHER] | [PREENCHER] |
| Recall (macro) | [PREENCHER] | [PREENCHER] | [PREENCHER] |
| F1-Score (macro) | [PREENCHER] | [PREENCHER] | [PREENCHER] |
| AUC-ROC (macro) | [PREENCHER] | [PREENCHER] | [PREENCHER] |

Fonte dos valores:
- Transformer e LSTM: `relatorios/resultados_transformer.json` e `relatorios/resultados_lstm.json` (chave `teste`) e `relatorios/historico_*.csv` para treino e validação.
- Markov: não há script de avaliação no repositório. Criar antes de preencher (ver seção 4).

Incluir também a **matriz de confusão** do teste (top-10 classes) e a **curva AUC-ROC** como figura, se gerada.

Incluir uma tabela de **estatísticas das melodias geradas** (alturas distintas, participação da nota dominante, intervalo médio, repetições consecutivas), comparando geração e real. Fonte: `relatorios/resultados_*.json` (chaves `geracao` e `real_teste`).

**Ajuste obrigatório:** a subseção 9.5 atual afirma "boa separação" entre conjuntos. Substituir por uma descrição quantitativa, por exemplo: "A diferença de loss entre treino e validação foi de [PREENCHER], indicando [PREENCHER: sem sinal de sobreajuste / sinal de sobreajuste]."

### 3.2 Seção 9.x (Resultados com volume de dados)

Adicionar uma tabela de **desempenho por volume de dados**, por exigência do professor. Usar execuções reais com tamanhos diferentes do piloto:

| Registros processados | Sequências aprovadas | Épocas | Loss val | Acurácia teste | F1 macro teste | Tempo total |
|---|---|---|---|---|---|---|
| 20.000 | [PREENCHER] | [PREENCHER] | [PREENCHER] | [PREENCHER] | [PREENCHER] | [PREENCHER] |
| 100.000 | [PREENCHER] | [PREENCHER] | [PREENCHER] | [PREENCHER] | [PREENCHER] | [PREENCHER] |

Se só o piloto de 100.000 for executado, manter a linha de 20.000 como `[NÃO EXECUTADO]` e informar isso no texto. Não estimar valores.

Texto a incluir: "O piloto processa 100.000 arquivos MIDI de entrada. O número de sequências aprovadas é [PREENCHER] (ver `relatorios/resumo_pipeline.json`), após os descartes por motivo."

### 3.3 Seção 10 (Evolução do projeto)

Adicionar uma subseção **"Revisão após feedback do professor"** com:
- Data do feedback (o e-mail não traz data; usar "[PREENCHER]").
- Pedido 1: inclusão de resultados de LSTM e Markov. Status: [PREENCHER].
- Pedido 2: uso de métricas específicas do tipo de problema. Status: métricas definidas na seção 2 deste roteiro.
- Pedido 3: aumento do volume de treino. Status: [PREENCHER com o número real de registros].
- Mudança de escopo: a avaliação passou de escuta subjetiva para métricas numéricas.

### 3.4 Seções 5 a 8

Não alterar, exceto se o pipeline mudou: o banco continua baseado em arquivos (sem SGBD), e o notebook de Colab substitui a execução local no treino.

## 4. Pendências técnicas antes de preencher

1. **Markov não tem avaliação.** Criar um script (`scripts/avaliar_markov.py`) que calcule loss, perplexidade, acurácia, top-5, precisão, recall, F1 e AUC-ROC sobre treino, validação e teste, usando o mesmo vocabulário e as mesmas janelas do notebook.
2. **LSTM sem métricas no repositório.** As métricas estão no notebook; reaproveitá-las em um script local, se o docx precisar de reprodução fora do Colab.
3. **Colab incompleto.** A execução atual não terminou. Não há números finais do Transformer treinado com 100.000 registros nem da LSTM. Preencher somente após execução completa.
4. **Matriz de confusão completa** (129 classes) não cabe no docx. Gerar CSV e incluir só o resumo no texto.

## 5. Regras de redação

- Português, tom técnico e direto.
- Todo número deve citar a fonte (arquivo e execução).
- Não usar "bom" ou "ruim" como avaliação. Usar a métrica.
- Não citar métricas não aplicáveis como resultado.
- Manter estilos de título existentes. Editar com `office_edit` ou ferramenta equivalente, de forma serial, e informar que houve backup.

## 6. Critério de conclusão

- Todos os `[PREENCHER]` foram substituídos por valor real, ou marcados como `[NÃO EXECUTADO]` com justificativa.
- LSTM e Markov aparecem com a mesma tabela do Transformer.
- A subseção 9.5 não contém "boa separação" sem número.
- O docx passa na validação do `office_read` (mode `validate`).
