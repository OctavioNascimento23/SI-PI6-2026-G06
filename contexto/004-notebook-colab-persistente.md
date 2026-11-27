# 004. Notebook do Colab: dados persistentes, treino retomável e download final

Arquivo: `notebooks/treinamento_google_colab.ipynb` (reescrito; a versão anterior está no git).

## Problema
1. Quando a sessão do Colab caía, o notebook precisava refazer o pipeline de dados (100.000 MIDIs, horas de processamento), e o treino recomeçava da época 1.
2. O pipeline só gravava no Drive no fim, como ~87 mil arquivos pequenos (lento e frágil no Drive).
3. Não havia um download único dos modelos e relatórios ao final.

## Causa
- O pipeline guardava tudo em memória e só escrevia depois de processar os 100.000 arquivos. Uma queda no meio perdia tudo.
- O treino só salvava o "melhor modelo" (pesos), sem otimizador, scheduler nem histórico. Isso não permite retomar de verdade.
- Não havia marcador de "dados prontos" nem checagem de configuração; a célula de pipeline rodava sempre.

## O que foi alterado
**Pipeline de dados (células 6 a 10)**
- Processa em **blocos de 2.000 MIDIs** e grava cada bloco no Drive ao terminar (`dados_processados/blocos/bloco_NNNN.jsonl.gz`). Cada bloco tem **uma linha por arquivo de entrada**: aprovado (com tokens, BPM e duração) ou descartado (com o motivo). Os 100.000 arquivos ficam registrados no Drive. Se a sessão cair, os blocos prontos são pulados.
- Marcador `pipeline_concluida.json` com um hash da configuração. Com dados prontos, o notebook **não descompacta o `.tar.gz` nem reprocessa nada**. Se você mudar um parâmetro do pipeline sem pedir para reprocessar, ele **recusa** em vez de misturar dados de configurações diferentes.
- Gravação **atômica** no Drive (arquivo temporário + renomear): uma queda nunca deixa um arquivo pela metade.
- **Importação dos dados antigos**: se o Drive já tem as pastas `treino/`, `validacao/`, `teste/` da versão anterior com `resumo_pipeline.json` coerente, elas são convertidas para o formato novo **sem reler nenhum MIDI**. Mesma divisão e mesmo vocabulário (140 tokens), então o modelo Transformer antigo continua compatível.
- Saída consolidada em `.jsonl.gz` (3 arquivos), `manifesto_pipeline.csv` (uma linha por arquivo de entrada) e `dados_processados_lmd_100k.zip` (formato do repositório, um `.json` por sequência).
- As janelas de treino (`.npy`) são calculadas uma vez e guardadas no Drive.

**Treino (células 11 a 13)**
- A cada época grava `modelos/ultimo_<modelo>.pt` com modelo, otimizador, scheduler e histórico. Se cair, retoma da última época concluída.
- Modelo já completo (e seus resultados) não é treinado nem avaliado de novo. Um modelo da execução antiga (com `resultados_*.json` de 15 épocas e o mesmo vocabulário) é **reaproveitado**.
- Chaves na célula de configuração: `REPROCESSAR_DADOS` e `NOVO_TREINO`. O que existia é **arquivado** em `_arquivo/`, nunca apagado.
- Recusa treinar em CPU (a menos que `PERMITIR_CPU=True`) e recusa retomar se vocabulário ou número de épocas mudaram.

**Final (célula 16)**
- Gera `pi6_resultados_<data>.zip` com `modelos/modelo_*.pt` e **todos** os arquivos de `relatorios/`, guarda uma cópia em `Drive/downloads/` e chama `files.download`.

**Outros**
- Não reinstala `torch`, `numpy`, `scikit-learn` (já vêm no Colab); só instala `pretty_midi`.
- A lógica de filtros, tokenização, divisão e arquitetura dos modelos **não foi alterada**.

## Como foi verificado
Executei as células de código do notebook **localmente**, com o Drive e o SSD simulados em pastas temporárias, `google.colab` simulado e parâmetros reduzidos (60 MIDIs reais do projeto, blocos de 20, modelos minúsculos, CPU):

| Cenário | Resultado |
|---|---|
| Pipeline interrompido no meio do bloco 1 | bloco 0 ficou no Drive; bloco 1 incompleto não foi gravado |
| Rodar de novo (sessão nova) | retomou do bloco 1, terminou, 52 aprovados de 60 |
| Rodar com dados prontos | pulou o `.tar.gz` e o pipeline |
| Treino interrompido na época 2 | retomou na época 2 e terminou |
| Rodar com tudo treinado | não treinou nem reavaliou |
| Célula final | gerou o `.zip` com modelos e 8 relatórios e chamou o download |
| Modelo antigo (15 épocas, vocab. 140) | reaproveitado, sem retreinar |
| Importação de dados antigos | convertidos sem reler MIDIs (simulada com os 4.363 arquivos locais) |

## Limitações (importante)
- **Não foi testado no Colab de verdade**: Drive FUSE, GPU, `drive.mount`, `files.download` e a velocidade com 100.000 arquivos. O que foi provado é a **lógica** de retomada.
- Importar ~87 mil `.json` pequenos do Drive (caso dos dados antigos) pode demorar vários minutos; é o gargalo esperado, mas não foi medido.
- "Armazenar os 100.000 arquivos" foi interpretado como **registrar o resultado do pipeline para os 100.000** (aprovados com tokens e descartados com motivo). Os `.mid` brutos continuam só no `lmd_full.tar.gz`. Se a intenção era copiar os `.mid` aprovados para o Drive, isso **não** foi feito.
- Os dados processados pelo notebook **não são idênticos** aos produzidos localmente por `scripts/03` e `04`: em um teste com 52 arquivos, **26 sequências diferiram** (BPM igual; algumas durações/pausas quantizadas diferentes). Hipótese, **não confirmada**: o script local grava a melodia em MIDI e a relê, o que arredonda os tempos. Essa diferença já existia (a lógica do notebook é a mesma de antes).
- A queda por **inatividade do próprio Colab** (aba fechada, limite de sessão) não é evitada; só se **recupera** dela com esta retomada.
