# Relatório de Limpeza — LMD-full — Projeto B6

**Data de execução:** 2026-10-26
**Modo:** Inventário de 178561 arquivos; recorte de treino com 25000 MIDIs

## Números gerais
- Total de arquivos no LMD-full analisados: 178561
- Arquivos corrompidos ou inválidos: 4140 (2.3%)
- Arquivos sem notas: 206 (0.1%)
- Arquivos muito curtos (< 15s): 6367 (3.6%)
- Arquivos muito longos (> 600s): 1597 (0.9%)
- Arquivos abaixo do tamanho mínimo (< 200 bytes): 28 (0.0%)
- MIDIs aprovados na validação: 166223 (93.1%)
- MIDIs no recorte de treino: 25000

## Extração de melodias
- MIDIs sem faixa melódica válida: 3194
- MIDIs descartados por filtros de qualidade: 1982
- Erros de leitura na extração: 0
- Melodias monofônicas extraídas: 19824

## Tokenização
- Sequências geradas: 19824
- Tamanho médio das sequências (tokens): 898.1
- Tamanho do vocabulário: 74

## Divisão do dataset
- Treino: 15859 sequências (80.0%)
- Validação: 1982 sequências (10.0%)
- Teste: 1983 sequências (10.0%)

## Parâmetros utilizados

```yaml
dataset:
  pasta_lmd_full: "arquivos_brutos/lmd_full"
  arquivo_md5_json: "arquivos_brutos/md5_to_paths.json"
  extensoes: [".mid", ".midi"]

piloto:
  ativo: false
  quantidade: 500

execucao:
  trabalhadores: 6
  retomada: true
  lote_gravacao: 200

recorte:
  ativo: true
  quantidade: 25000
  semente: 42

filtros:
  notas_minimas: 32
  notas_maximas: 2000
  duracao_minima_seg: 15.0
  duracao_maxima_seg: 600.0
  polifonia_maxima_pct: 0.30
  pitch_minimo: 36              # C2
  pitch_maximo: 96              # C7

normalizacao:
  quantizar_duracao: true
  grades_ritmicas: [0.125, 0.25, 0.5, 1.0, 2.0]
  regra_monofonia: "pitch_mais_agudo"
  transpor_para_tonica: true   # maior -> Do, menor -> La

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
  copiar_midi_validos: false
```

## Observações
- O inventário percorre o LMD-full e pode ser retomado se a execução parar.
- Os MIDIs aprovados não são copiados. A extração lê o arquivo original em arquivos_brutos.
- O recorte de treino é uma amostra estratificada por pasta do hash, com semente 42.
- Cada melodia é transposta para Dó maior ou Lá menor antes da tokenização.
- As sequências ficam em JSONL, um arquivo por conjunto, sem um JSON por música.
- Semente da divisão: 42.
