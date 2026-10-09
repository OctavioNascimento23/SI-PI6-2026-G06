# Relatório de Limpeza — LMD-full — Projeto B6

**Data de execução:** 2026-10-09
**Modo:** Piloto (5.000 de 178.561 arquivos)

## Números gerais
- Total de arquivos no LMD-full analisados: 5000
- Arquivos corrompidos ou inválidos: 111 (2.2%)
- Arquivos sem notas: 10 (0.2%)
- Arquivos muito curtos (< 15s): 184 (3.7%)
- Arquivos muito longos (> 600s): 49 (1.0%)
- Arquivos abaixo do tamanho mínimo (< 200 bytes): 2 (0.0%)
- MIDIs aprovados na validação: 4644 (92.9%)

## Extração de melodias
- MIDIs sem faixa melódica válida: 22
- MIDIs descartados por filtros de qualidade: 259
- Melodias monofônicas extraídas: 4363

## Tokenização
- Sequências geradas: 4363
- Tamanho médio das sequências (tokens): 1062.3
- Tamanho do vocabulário: 129

## Divisão do dataset
- Treino: 3490 sequências (80.0%)
- Validação: 436 sequências (10.0%)
- Teste: 437 sequências (10.0%)

## Parâmetros utilizados

```yaml
dataset:
  pasta_lmd_full: "arquivos_brutos/lmd_full"
  arquivo_md5_json: "arquivos_brutos/md5_to_paths.json"
  extensoes: [".mid", ".midi"]

piloto:
  ativo: true           # true = processar apenas N arquivos para teste
  quantidade: 5000      # aumentar para 5000 depois de validar o pipeline

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

## Observações
- O modo piloto processou 5.000 dos 178.561 arquivos do LMD-full (2,8% do total).
- 97,8% dos arquivos do piloto abriram sem erros; 2,2% estão corrompidos (erros de parse MIDI).
- O erro mais comum nos corrompidos é `data byte must be in range 0..127`, indicando dados MIDI malformados.
- 3,7% dos arquivos foram descartados por duração < 15s (fragmentos muito curtos).
- O vocabulário de 129 tokens é compacto e cobre todos os pitches com as 5 grades rítmicas definidas.
- Para o pipeline completo (178 mil arquivos), estima-se ~156 mil sequências tokenizadas (~87% de aprovação).