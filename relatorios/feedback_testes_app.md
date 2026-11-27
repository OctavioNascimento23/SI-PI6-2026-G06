# Feedback de teste do app (não corrigido)

Data do teste: 2026-11-23
Origem: teste manual do app Streamlit (`app.py`), com a arquitetura Transformer.

## Problemas registrados

1. **Notas repetidas.** A melodia gerada repete as mesmas notas em sequência, com pouca variação de alturas e de ritmo.
   - Evidência quantitativa já existente em `relatorios/resultados_transformer.json`: média de 9 alturas distintas por melodia gerada, contra 19 nas melodias reais do teste; repetição consecutiva de 3%, contra 22% nas reais.

2. **Melodia não conversa com a progressão de acordes escolhida.** As notas não seguem a harmonia da progressão selecionada na barra lateral (ex.: I-V-vi-IV).
   - Hipótese a verificar: a geração do Transformer não recebe a progressão de acordes como condicionamento. O motor (`src/gerador.py`) gera a melodia e os acordes separadamente, sem restrição harmônica sobre as notas.

## Status

- Nenhuma correção aplicada nesta rodada.
- Próximo passo sugerido, quando for corrigir: medir a fração de notas da melodia que pertencem aos acordes do compasso correspondente, para ter um número objetivo antes e depois da mudança.
