# Prompt — IBM Bob \| Projeto B6 \| Pipeline LMD\-full

***

## Contexto do projeto

Você está ajudando o grupo **B6** de um projeto acadêmico de **Inteligência Artificial** chamado **SI-PI6-2026-G06**.

O objetivo do projeto é criar uma aplicação que recebe parâmetros do usuário (tonalidade, BPM e duração) e gera automaticamente uma melodia original em formato **MIDI**, usando uma rede neural treinada com dados musicais reais.

A fonte de dados é o **Lakh MIDI Dataset – LMD-full**, que contém aproximadamente 176.581 arquivos MIDI coletados da internet. Esses arquivos são brutos e precisam ser validados, limpos e transformados antes de qualquer treinamento.

**Seu papel nesta etapa é exclusivamente preparar os dados.** Você não deve treinar nenhum modelo agora.

***

## Estrutura atual do repositório

```
SI-PI6-2026-G06/
├── arquivos_brutos/
│   ├── md5_to_paths.json      ← índice MD5 → nomes originais dos arquivos
│   └── lmd_full/              ← ~176 mil arquivos MIDI brutos (NÃO MODIFICAR)
├── .gitattributes
├── Documentação_PI_VI_...docx
├── Documentação_PI_VI_...pdf
└── README.md
```

***

## Estrutura que você deve criar

Crie as pastas e arquivos abaixo **na raiz do projeto**, no mesmo nível de `arquivos_brutos/`:

```
SI-PI6-2026-G06/
├── arquivos_brutos/           ← NÃO TOCAR
│
├── dados_processados/
│   ├── midi_validos/          ← cópias dos MIDIs que passaram na validação
│   ├── melodias_extraidas/    ← arquivos .mid com apenas a faixa melódica
│   ├── sequencias/            ← tokens/eventos serializados (JSON ou CSV)
│   ├── treino/
│   ├── validacao/
│   └── teste/
│
├── relatorios/
│   ├── inventario.csv
│   ├── arquivos_rejeitados.csv
│   ├── faixas_analisadas.csv
│   ├── melodias_selecionadas.csv
│   └── resumo_limpeza.md
│
├── scripts/
│   ├── 00_verificar_dataset.py
│   ├── 01_inventariar_dataset.py
│   ├── 02_validar_midis.py
│   ├── 03_extrair_melodias.py
│   ├── 04_tokenizar.py
│   └── 05_dividir_dataset.py
│
├── configuracao/
│   └── pipeline.yaml
│
├── testes/
├── modelos/
├── requirements.txt
└── .gitignore
```

***

## Regras absolutas (não negociáveis)

1. **Nunca apague, mova ou modifique** nenhum arquivo dentro de `arquivos_brutos/`.
2. **Nunca treine nenhum modelo** nesta etapa.
3. **Toda operação destrutiva deve ser reversível** — salve os rejeitados em CSV, não os delete.
4. **Registre tudo em CSV/relatório** — cada decisão de descarte precisa ter um motivo documentado.
5. **Use semente aleatória fixa** (`random_state=42`) em todas as operações com aleatoriedade.
6. **Processe primeiro um piloto pequeno** antes de rodar o pipeline completo.

***

## Bibliotecas necessárias

Crie o arquivo `requirements.txt` com:

```
pretty_midi
mido
music21
numpy
pandas
scikit-learn
tqdm
pyyaml
```

Instale com:

```bash
pip install -r requirements.txt
```

***

## Arquivo de configuração

Crie `configuracao/pipeline.yaml` com os parâmetros abaixo. **Todos os scripts devem ler os parâmetros deste arquivo**, nunca usar valores fixos no código:

```yaml
dataset:
  pasta_lmd_full: "arquivos_brutos/lmd_full"
  arquivo_md5_json: "arquivos_brutos/md5_to_paths.json"
  extensoes: [".mid", ".midi"]

piloto:
  ativo: true           # true = processar apenas N arquivos para teste
  quantidade: 500       # aumentar para 5000 depois de validar o pipeline

filtros:
  notas_minimas: 32
  notas_maximas: 2000
  duracao_minima_seg: 15.0
  duracao_maxima_seg: 600.0
  polifonia_maxima_pct: 0.30   # até 30% de notas simultâneas na faixa selecionada
  pitch_minimo: 36              # C2
  pitch_maximo: 96              # C7

normalizacao:
  quantizar_duracao: true
  grades_ritmicas: [0.125, 0.25, 0.5, 1.0, 2.0]  # em beats (1/8, 1/4, 1/2, 1, 2)
  regra_monofonia: "pitch_mais_agudo"              # ou "maior_duracao"

divisao:
  treino: 0.80
  validacao: 0.10
  teste: 0.10
  semente: 42

saidas:
  pasta_midi_validos: "dados_processados/midi_validos"
  pasta_melodias: "dados_processados/melodias_extraidas"
  pasta_sequencias: "dados_processados/sequencias"
  pasta_treino: "dados_processados/treino"
  pasta_validacao: "dados_processados/validacao"
  pasta_teste: "dados_processados/teste"
  pasta_relatorios: "relatorios"
```

***

## Script 00 — Verificar o dataset

**Arquivo:** `scripts/00_verificar_dataset.py`

**Objetivo:** confirmar que o LMD-full está extraído corretamente, sem modificar nada.

**O que deve fazer:**

1. Localizar recursivamente todos os arquivos `.mid` e `.midi` dentro de `arquivos_brutos/lmd_full/`.
2. Imprimir o total de arquivos encontrados.
3. Imprimir os primeiros 10 caminhos.
4. Imprimir a distribuição por primeiro nível de subpasta.
5. Imprimir o tamanho total em disco (MB/GB).
6. Carregar `md5_to_paths.json` e imprimir:
    * total de entradas;
    * exemplo das 5 primeiras entradas;
    * estrutura esperada: `{ "hash_md5": ["caminho/nome.mid"] }`.
7. Salvar um arquivo `relatorios/verificacao_inicial.txt` com esse resumo.

**Não deve:** copiar, mover ou alterar qualquer arquivo MIDI.

***

## Script 01 — Inventariar o dataset

**Arquivo:** `scripts/01_inventariar_dataset.py`

**Objetivo:** percorrer todos os MIDIs e registrar metadados básicos sem nenhuma filtragem ainda.

**Para cada arquivo MIDI, registrar:**

| Campo | Descrição |
| ----- | --------- |
| `caminho_relativo` | Caminho a partir da raiz do projeto |
| `md5` | Nome do arquivo (que é o hash MD5) |
| `nome_original` | Nome(s) obtido(s) do md5\_to\_paths.json, se existir |
| `tamanho_bytes` | Tamanho do arquivo em bytes |
| `abre_sem_erro` | true/false |
| `erro_leitura` | Mensagem de erro, se houver |
| `duracao_seg` | Duração em segundos |
| `num_faixas` | Número de tracks no arquivo |
| `num_instrumentos` | Instrumentos únicos identificados |
| `tem_bateria` | true/false (canal 10 ou is\_drum=True) |
| `num_notas_total` | Total de notas em todas as faixas |
| `bpm_predominante` | BPM principal (primeiro tempo ou mais frequente) |
| `num_mudancas_tempo` | Quantas mudanças de BPM ocorrem |
| `faixas_info` | JSON com lista de faixas: nome, programa, is\_drum, num\_notas |

**Saída:** `relatorios/inventario.csv`

**Comportamento com erros:**

* Se um arquivo não abrir, registrar `abre_sem_erro=false` e o erro, mas **continuar** para o próximo arquivo.
* Usar `try/except` em cada arquivo individualmente.
* Usar `tqdm` para mostrar progresso.

**Modo piloto:** se `piloto.ativo: true` no YAML, processar apenas os primeiros N arquivos.

***

## Script 02 — Validar e filtrar MIDIs

**Arquivo:** `scripts/02_validar_midis.py`

**Objetivo:** ler o `inventario.csv` e aplicar os critérios de rejeição. Copiar apenas os MIDIs aprovados para `dados_processados/midi_validos/`.

**Critérios de rejeição (registrar motivo para cada um):**

| Condição | Motivo registrado |
| -------- | ----------------- |
| `abre_sem_erro = false` | `CORROMPIDO` |
| `num_notas_total = 0` | `SEM_NOTAS` |
| `duracao_seg < filtros.duracao_minima_seg` | `MUITO_CURTO` |
| `duracao_seg > filtros.duracao_maxima_seg` | `MUITO_LONGO` |
| `tamanho_bytes < 200` | `ARQUIVO_MINIMO` |

**Saídas:**

* `relatorios/arquivos_rejeitados.csv` — com campos: `md5`, `caminho`, `motivo_rejeicao`, `detalhe`
* `dados_processados/midi_validos/` — cópias dos arquivos aprovados
* Imprimir no console: total analisado, total aprovado, total rejeitado por motivo.

**Importante:** copiar o arquivo, não mover. O original em `arquivos_brutos/lmd_full/` deve permanecer intacto.

***

## Script 03 — Extrair melodias

**Arquivo:** `scripts/03_extrair_melodias.py`

**Objetivo:** para cada MIDI válido, identificar e extrair a faixa mais adequada como melodia monofônica.

### Passo 3.1 — Selecionar a faixa melódica

Para cada MIDI, analisar todas as faixas não-percussivas e calcular uma pontuação:

```
pontuacao = (
    peso_notas    × normalizar(num_notas)
  + peso_registro × normalizar(pitch_medio)        # preferir registro médio/agudo
  + peso_var      × normalizar(variacao_pitch)      # preferir variedade melódica
  - peso_poli     × percentual_polifonia            # penalizar polifonia
  - peso_pausa    × percentual_pausas               # penalizar excesso de silêncio
)
```

Pesos sugeridos inicialmente:

* `peso_notas = 0.3`
* `peso_registro = 0.2`
* `peso_var = 0.3`
* `peso_poli = 0.1`
* `peso_pausa = 0.1`

Selecionar a faixa com **maior pontuação**, desde que atenda aos critérios mínimos:

* `num_notas >= filtros.notas_minimas`
* `duracao_seg >= filtros.duracao_minima_seg`
* `not is_drum`

Se nenhuma faixa atender, registrar como `SEM_FAIXA_VALIDA` no relatório.

### Passo 3.2 — Converter para monofonia

Aplicar a regra definida em `normalizacao.regra_monofonia`:

* `pitch_mais_agudo`: quando há notas simultâneas, manter apenas a de maior pitch.
* `maior_duracao`: quando há notas simultâneas, manter apenas a de maior duração.

"Simultâneas" = notas cujo intervalo de início é menor que 0.05 segundos (50ms).

### Passo 3.3 — Aplicar filtros finais

Descartar a faixa selecionada se:

* `num_notas < filtros.notas_minimas`
* `num_notas > filtros.notas_maximas`
* qualquer nota com pitch fora do intervalo `[pitch_minimo, pitch_maximo]` **em mais de 5% das notas** — nesses casos, descartar apenas as notas fora do intervalo e re-verificar o critério mínimo de notas
* mais de 80% das notas em apenas 1 ou 2 valores de pitch distintos (melodia praticamente plana)

### Passo 3.4 — Salvar

Salvar cada faixa extraída como novo arquivo `.mid` em `dados_processados/melodias_extraidas/`, mantendo o MD5 original como nome do arquivo.

**Saídas:**

* `dados_processados/melodias_extraidas/*.mid`
* `relatorios/faixas_analisadas.csv` — uma linha por faixa analisada (todas as faixas de todos os MIDIs)
* `relatorios/melodias_selecionadas.csv` — uma linha por melodia aprovada

Campos de `melodias_selecionadas.csv`:

| Campo | Descrição |
| ----- | --------- |
| `md5` | Hash do arquivo original |
| `nome_original` | Nome do arquivo original, se disponível |
| `indice_faixa` | Índice da faixa no MIDI original |
| `instrumento` | Nome do instrumento (General MIDI) |
| `num_notas` | Total de notas na melodia monofônica |
| `duracao_seg` | Duração em segundos |
| `pitch_min` | Menor nota |
| `pitch_max` | Maior nota |
| `pitch_medio` | Pitch médio |
| `bpm` | BPM usado |
| `pontuacao_selecao` | Score calculado para seleção |

***

## Script 04 — Tokenizar

**Arquivo:** `scripts/04_tokenizar.py`

**Objetivo:** converter cada melodia MIDI em uma sequência de tokens que o modelo de IA poderá consumir.

### Formato dos tokens

Usar representação por eventos textuais. Cada nota gera dois tokens:

```
NOTE_<pitch>
DURATION_<grade>
```

E cada pausa gera:

```
REST_<grade>
```

Onde `<grade>` é o valor quantizado mais próximo de `normalizacao.grades_ritmicas`, convertido para string com dois decimais (ex: `0.25`, `0.50`, `1.00`).

Exemplo de saída para uma frase curta:

```json
["NOTE_60", "DURATION_0.50", "REST_0.25", "NOTE_62", "DURATION_0.25", "NOTE_64", "DURATION_1.00"]
```

### Quantização de durações

Para quantizar uma duração `d` em beats:

1. Converter duração em segundos para beats usando o BPM.
2. Encontrar o valor em `grades_ritmicas` mais próximo.
3. Usar esse valor como token.

### Saída por arquivo

Para cada melodia, salvar em `dados_processados/sequencias/<md5>.json`:

```json
{
  "md5": "abc123...",
  "nome_original": "Artist - Song.mid",
  "bpm": 120,
  "num_notas": 128,
  "duracao_seg": 32.5,
  "tokens": ["NOTE_60", "DURATION_0.50", ...]
}
```

### Vocabulário

Ao final, gerar `dados_processados/sequencias/vocabulario.json`:

```json
{
  "token_para_id": {"NOTE_60": 0, "DURATION_0.50": 1, ...},
  "id_para_token": {"0": "NOTE_60", "1": "DURATION_0.50", ...},
  "tamanho_vocabulario": 256,
  "tokens_especiais": {
    "PAD": "<PAD>",
    "START": "<START>",
    "END": "<END>"
  }
}
```

Incluir os tokens especiais `<PAD>`, `<START>` e `<END>` no vocabulário.

***

## Script 05 — Dividir o dataset

**Arquivo:** `scripts/05_dividir_dataset.py`

**Objetivo:** dividir os arquivos de sequências em treino, validação e teste **por arquivo de origem** (não por token ou nota individual).

**Regras:**

* Usar `sklearn.model_selection.train_test_split` com `random_state=42`.
* A divisão é feita na lista de MD5s, não nos tokens.
* Cada MD5 vai para exatamente um conjunto.
* **Nunca dividir trechos da mesma música entre conjuntos diferentes.**

**Processo:**

1. Listar todos os arquivos `.json` em `dados_processados/sequencias/` (excluir `vocabulario.json`).
2. Embaralhar com semente 42.
3. Dividir: 80% treino, 10% validação, 10% teste.
4. Copiar os arquivos `.json` para as respectivas pastas em `dados_processados/`.
5. Também copiar o vocabulário para as três pastas.

**Saída adicional:** `relatorios/divisao_dataset.json`:

```json
{
  "total_sequencias": 4500,
  "treino": 3600,
  "validacao": 450,
  "teste": 450,
  "semente": 42,
  "md5s_treino": ["abc...", "def...", ...],
  "md5s_validacao": [...],
  "md5s_teste": [...]
}
```

***

## Relatório final de limpeza

Ao final de todos os scripts, criar `relatorios/resumo_limpeza.md` com:

```markdown
# Relatório de Limpeza — LMD-full — Projeto B6

**Data de execução:** YYYY-MM-DD

## Números gerais
- Total de arquivos no LMD-full analisados: X
- Arquivos corrompidos ou inválidos: X (X%)
- Arquivos sem notas: X (X%)
- Arquivos muito curtos: X (X%)
- Arquivos muito longos: X (X%)
- MIDIs aprovados na validação: X

## Extração de melodias
- MIDIs sem faixa melódica válida: X
- MIDIs descartados por filtros de qualidade: X
- Melodias monofônicas extraídas: X

## Tokenização
- Sequências geradas: X
- Tamanho médio das sequências (tokens): X
- Tamanho do vocabulário: X

## Divisão do dataset
- Treino: X sequências
- Validação: X sequências
- Teste: X sequências

## Parâmetros utilizados
(copiar o conteúdo do pipeline.yaml aqui)

## Observações
(registrar qualquer comportamento inesperado, anomalias encontradas ou decisões tomadas durante o processo)
```

***

## .gitignore

Crie ou atualize o `.gitignore` na raiz:

```gitignore
# Dataset bruto — não versionar
arquivos_brutos/lmd_full/

# Dados processados — não versionar
dados_processados/

# Modelos — não versionar
modelos/

# Python
*.pyc
__pycache__/
.venv/
venv/
*.egg-info/
dist/
build/

# Sistema
.DS_Store
Thumbs.db
```

***

## Ordem de execução

Execute os scripts **nesta sequência**, um por vez, verificando a saída antes de prosseguir:

```bash
python scripts/00_verificar_dataset.py
python scripts/01_inventariar_dataset.py
python scripts/02_validar_midis.py
python scripts/03_extrair_melodias.py
python scripts/04_tokenizar.py
python scripts/05_dividir_dataset.py
```

**Antes de rodar cada script**, confirme:

* O script anterior terminou sem erros críticos.
* O CSV/relatório gerado tem conteúdo plausível.
* A quantidade de arquivos aprovados faz sentido.

***

## Critérios de sucesso desta etapa

A etapa de preparação de dados está concluída quando:

* [ ] `relatorios/inventario.csv` existe e tem pelo menos 10.000 linhas (modo completo).
* [ ] `relatorios/arquivos_rejeitados.csv` lista todos os MIDIs descartados com motivo.
* [ ] `relatorios/melodias_selecionadas.csv` lista as melodias aprovadas.
* [ ] `dados_processados/sequencias/` contém os arquivos `.json` tokenizados.
* [ ] `dados_processados/sequencias/vocabulario.json` existe e tem tokens `NOTE_*`, `DURATION_*`, `REST_*` e tokens especiais.
* [ ] `dados_processados/treino/`, `validacao/` e `teste/` estão preenchidos.
* [ ] `relatorios/resumo_limpeza.md` está preenchido com os números reais.
* [ ] `relatorios/divisao_dataset.json` registra quais MD5s foram para cada conjunto.
* [ ] Nenhum arquivo em `arquivos_brutos/` foi modificado.

***

## O que você NÃO deve fazer nesta etapa

* Não treinar nenhum modelo.
* Não criar nenhuma interface ou API.
* Não criar código de geração de melodias.
* Não baixar arquivos adicionais da internet sem autorização.
* Não apagar arquivos de `arquivos_brutos/`.
* Não usar arquivos do LMD-matched ou LMD-aligned (não fazem parte do repositório atual).
* Não armazenar todos os 176 mil MIDIs em memória ao mesmo tempo — processar em lotes ou um por vez com `tqdm`.

***

## Entrega esperada

Ao concluir, o grupo B6 deve receber:

1. Todos os scripts funcionando e documentados.
2. Os relatórios CSV e Markdown preenchidos com dados reais.
3. O dataset dividido em treino/validação/teste, pronto para o próximo sprint.
4. Um breve comentário sobre o que foi encontrado: anomalias, instrumentos mais comuns, distribuição de BPM, proporção de arquivos descartados.

***

*Projeto B6 — SI-PI6-2026-G06 — Projeto Integrador VI — Geração de Melodias com IA*