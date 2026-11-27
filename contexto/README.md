# Contexto do projeto: histórico de mudanças

Esta pasta registra, em ordem, **cada mudança feita no projeto**: o que estava errado, por que mudou, o que foi alterado e como foi verificado. Serve para o grupo entender o estado atual sem ter que reler o histórico do git, e para a documentação do PI VI.

## Convenção
- Um arquivo por mudança, numerado em ordem: `NNN-titulo-curto.md`.
- Cada arquivo tem: **Problema**, **Causa**, **O que foi alterado**, **Como foi verificado**, **Limitações / pendências**.
- Tudo que **depende de ação manual** do grupo fica no [`PENDENCIAS.md`](PENDENCIAS.md).

## Índice

| # | Mudança | Resumo |
|---|---|---|
| [001](001-vocabulario-incompativel.md) | Vocabulário incompatível entre app e modelos | Causa das notas repetidas: o app decodificava os IDs com o vocabulário errado |
| [002](002-guia-harmonico.md) | Guia harmônico na geração | Melodia passa a favorecer notas do acorde do compasso, sem retreinar |
| [003](003-cache-streamlit.md) | Cache do Streamlit | Erro `unexpected keyword argument 'guiar_por_harmonia'` após atualizar o código |
| [004](004-notebook-colab-persistente.md) | Notebook do Colab persistente e retomável | Dados e treino sobrevivem à queda da sessão; download final |
| [005](005-script-anti-suspensao.md) | Script anti-suspensão do Windows | Evita que o PC bloqueie e derrube o Colab |
| [006](006-alinhamento-melodia-base.md) | Alinhamento melodia–base | Corrige deriva de tempo causada por `DURATION_0.12` (0,125 beat) e encaixa as notas na grade |
| [007](007-progressao-acordes-coerente.md) | Progressão de acordes coerente | Corrige acordes que não condizem com a progressão escolhida (tônica repetida); modo oposto toca na relativa, com aviso |
| [008](008-ritmo-transformer-alinhado.md) | Ritmo do Transformer alinhado à base | Melodia adiantada/derivando: guia de ritmo na amostragem (só Transformer), notas no beat de 23% para 56% |
| [009](009-geracao-em-do-e-transposicao.md) | Geração em Dó e transposição | Só Dó Maior funcionava bem: a melodia agora é gerada na região de Dó (onde o modelo rende) e transposta para a tonalidade escolhida |
| [010](010-lstm-treinada-integrada.md) | LSTM treinada integrada e validada | LSTM nova (20 épocas) carrega e gera nos 3 motores; quase empata com o Transformer nas métricas, mas é mais repetitiva e pior de ritmo. Limpeza de zips e temporários |
| [011](011-lstm-melodia-curta-e-repetida.md) | LSTM com melodia curta e presa numa nota | A LSTM acabava antes do tempo (cobertura 56%) e repetia a mesma nota (48%); agora cobre 98% e repete 13% |

## Pontos em aberto
Ver [`PENDENCIAS.md`](PENDENCIAS.md).
