# SI-PI6-2026-G06 — Gerador de Melodias e Progressões Harmônicas com IA

Repositório oficial do **Projeto Integrador VI (PI VI)** do curso de **Sistemas de Informação (2026)**.

---

## 🎵 Visão Geral do Projeto

O objetivo principal deste projeto é desenvolver uma aplicação inteligente capaz de compor e gerar automaticamente **músicas autorais em formato MIDI (.mid)** a partir de parâmetros fornecidos pelo usuário, tais como:
- **Tonalidade** (ex.: Dó Maior, Lá Menor, Sol Maior, etc.)
- **Andamento / BPM** (ex.: 60 a 180 BPM)
- **Duração** da peça musical (em segundos/compassos)
- **Base Harmônica** (Geração automática de progressão de acordes que serve de guia e acompanhamento para a linha melódica principal)

O projeto evoluiu a partir de uma **Prova de Conceito (POC)** probabilística funcional (Cadeia de Markov de 2ª ordem) integrada a uma interface web interativa (Streamlit) e agora avança para a fase de **Deep Learning** (Redes Neurais / Transformers) treinados no dataset musical **LMD-full (Lakh MIDI Dataset)** utilizando aceleração por GPU no **Google Colab**.

---

## 🏗️ Arquitetura do Sistema

```mermaid
flowchart TD
    subgraph Pipeline_de_Dados["1. Pipeline de Dados (LMD-full)"]
        A[Arquivos MIDI Brutos\n~176k arquivos] --> B[Validação e Limpeza\nfiltros de notas, duração, integridade]
        B --> C[Extração Melódica e Harmônica\nfaixa monofônica + acordes]
        C --> D[Tokenização por Eventos\nNOTE, DURATION, REST, CHORD]
        D --> E[Divisão do Dataset\n80% Treino / 10% Validação / 10% Teste]
    end

    subgraph Treinamento_Colab["2. Treinamento na Nuvem (Google Colab GPU)"]
        E --> F[Google Drive / Dataset Zipado]
        F --> G[Treinamento do Modelo de IA\nTransformer Autoregressivo / LSTM]
        G --> H[Checkpoints & Modelo Treinado .pt/.h5]
    end

    subgraph Aplicacao["3. Aplicação & Inferência (Streamlit / API)"]
        I[Entrada do Usuário\nTom, BPM, Duração, Estilo] --> J[Geração de Progressão de Acordes\n(Base Harmônica)]
        J --> K[Inferência Neural da Melodia\n(Condicionada à Harmonia)]
        K --> L[Módulo MIDI Builder\nFaixa 1: Acordes | Faixa 2: Melodia]
        L --> M[Exportação MIDI .mid & Renderização de Áudio .wav]
        M --> N[Interface Web Interativa Streamlit]
    end

    H --> K
```

---

## 🎼 Geração de Progressão de Acordes + Melodia (Arquitetura Harmônica)

Para elevar a qualidade musical das gerações, o sistema adota uma abordagem de **dois níveis (Harmonia Base + Melodia Condicionada)**:

1. **Geração / Seleção da Progressão Harmônica:**
   - O sistema gera ou seleciona progressões de acordes tonais (ex.: $I - V - vi - IV$ ou $ii - V - I$) no tom escolhido pelo usuário.
   - Os acordes são representados por compassos e graus harmônicos (ex.: `CHORD_C_MAJ`, `CHORD_G_MAJ`, `CHORD_A_MIN`, `CHORD_F_MAJ`).

2. **Geração Melódica Condicionada:**
   - A rede neural preditiva recebe os tokens do acorde atual como contexto e seleciona notas que respeitam as notas da tríade/tétrade nos tempos fortes, permitindo tensões e notas de passagem nos tempos fracos.

3. **Reconstrução MIDI Multifaixa:**
   - **Track 1 (Acompanhamento):** Acordes sustentados ou arpejos de piano/base.
   - **Track 2 (Melodia Principal):** Linha de solo/melodia monofônica sincronizada no mesmo BPM e compasso.

---

## 🚀 Status do Projeto e Sprints

| Sprint / Etapa | Descrição | Status |
| :--- | :--- | :---: |
| **Sprint 1: Pipeline de Dados** | Extração, validação, tokenização e split do LMD-full | ✅ Concluído |
| **POC (Markov 2ª Ordem)** | Prova de conceito funcional com interface Streamlit, teoria musical e exportador MIDI | ✅ Concluído |
| **Sprint 2: Treinamento Neural** | Modelagem (Transformer / LSTM) e treinamento no Google Colab com GPU | 🔄 Em Andamento |
| **Sprint 3: Harmonia & Multifaixa** | Integração do gerador de acordes com a melodia condicionada | 📋 Planejado |
| **Sprint 4: Interface & Áudio** | Aperfeiçoamento do front-end com player multimídia e visualização de partitura/piano roll | 📋 Planejado |
| **Sprint 5: Avaliação & Bancada** | Métricas musicais objetivas, testes de validação e documentação final | 📋 Planejado |

---

## 🤖 Modelos de IA Recomendados

Conforme diretriz pedagógica de utilizar arquiteturas estabelecidas e ajustá-las para os dados do projeto:

1. **Transformer Autoregressivo (Recomendado — Estilo GPT-2 / Music Transformer):**
   - **Base:** `GPT2LMHeadModel` da biblioteca `transformers` (Hugging Face) configurado para vocabulário musical ou implementação de Music Transformer.
   - **Vantagens:** Atenção global (Self-Attention) captura estruturas rítmicas e motivos melódicos de longo alcance com alta coerência musical.
   - **Treinamento:** Rápido e estável em GPU T4 no Google Colab.

2. **Stacked LSTM com Embedding de Acorde (Estilo Google Magenta Melody RNN):**
   - **Base:** Rede Recorrente de 2 a 3 camadas LSTM (ex.: 256–512 unidades) com Dropout e camada de projeção Linear.
   - **Vantagens:** Simples de depurar, baixo consumo de memória, excelente para continuidade sequencial nota-a-nota.

---

## ☁️ Guia de Treinamento no Google Colab (Passo a Passo)

Como o treinamento de modelos neurais em larga escala exige aceleração computacional por GPU:

1. **Compactar os dados tokenizados:**
   ```bash
   # Compactar os dados processados para upload
   tar -czvf dados_treino.tar.gz dados_processados/treino dados_processados/validacao dados_processados/sequencias/vocabulario.json
   ```

2. **Configurar o Google Colab:**
   - Criar um novo notebook no [Google Colab](https://colab.research.google.com).
   - Alterar o ambiente de execução para GPU: **Ambiente de Execução > Alterar tipo de ambiente de execução > Acelerador de hardware: T4 GPU**.

3. **Montar o Google Drive e Carregar os Dados:**
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   
   # Descompactar os dados no ambiente do Colab
   !tar -xzvf /content/drive/MyDrive/SI-PI6-2026-G06/dados_treino.tar.gz -C /content/
   ```

4. **Executar o Treinamento com PyTorch/TensorFlow:**
   - Instalar dependências: `!pip install transformers torch pretty_midi pyyaml tqdm`
   - O treinamento salvará os pesos periódicos (`checkpoints/modelo_epoch_X.pt`) diretamente no Google Drive.

5. **Exportação para a Aplicação Local:**
   - Baixar o arquivo de pesos treinado (`.pt` ou `.keras`) e colocá-lo na pasta `modelos/` do repositório local para inferência na aplicação Streamlit.

---

## 💻 Estrutura do Repositório

```
SI-PI6-2026-G06/
├── arquivos_brutos/          # Dataset original LMD-full e índices
├── configuracao/
│   └── pipeline.yaml         # Parâmetros centrais do pipeline e filtros
├── dados_processados/        # MIDIs válidos, sequências e splits de treino
│   ├── treino/
│   ├── validacao/
│   ├── teste/
│   └── sequencias/           # Vocabulário e tokens JSON
├── modelos/                  # Modelos treinados (.pkl, .pt, .pth)
├── poc/                      # Prova de Conceito funcional (Markov + Streamlit)
│   ├── app.py                # Interface gráfica Streamlit
│   ├── markov.py             # Implementação do modelo de Markov
│   ├── teoria_musical.py     # Regras de harmonia, escalas e transposição
│   ├── midi_builder.py       # Conversor de tokens para arquivo MIDI
│   ├── audio_renderer.py     # Renderizador de áudio WAV via FluidSynth
│   └── treinar_markov.py     # Script de treinamento do modelo da POC
├── relatorios/               # Relatórios de limpeza e inventário do dataset
├── scripts/                  # Scripts modulares do pipeline de dados (00 a 05)
├── Documentação_PI_VI_G06.docx # Documento de especificação acadêmica
├── requirements.txt          # Dependências do projeto
└── README.md                 # Esta documentação
```

---

## 🛠️ Como Executar a POC Localmente

1. **Criar e ativar o ambiente virtual Python:**
   ```bash
   python -m venv .venv
   # No Windows:
   .venv\Scripts\activate
   # No Linux/Mac:
   source .venv/bin/activate
   ```

2. **Instalar as dependências:**
   ```bash
   pip install -r poc/requirements_poc.txt
   ```

3. **Treinar o modelo da POC (se necessário):**
   ```bash
   python poc/treinar_markov.py
   ```

4. **Iniciar a aplicação web:**
   ```bash
   streamlit run poc/app.py
   ```
   Acesse `http://localhost:8501` no navegador.

---

## 👥 Integrantes do Grupo B6

- **Eduardo de Almeida Freitas** — RA: 24008082
- **Guilherme Henrique Alves Santos** — RA: 24015942
- **Hector Lopes** — RA: 25013988
- **Mariana Assis Ferreira** — RA: 21943527
- **Octávio Augusto dos Santos Nascimento** — RA: 24015129

**Orientador:** Prof. Dimas Augusto  
**Instituição:** Pontifícia Universidade Católica de Campinas — PUC-Campinas  
**Ano:** 2026
