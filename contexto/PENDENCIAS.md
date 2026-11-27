# Pendências (precisam de ação do grupo ou de decisão)

## Para o treino no Colab
- [ ] Antes de iniciar o treino: dar duplo clique em `scripts\manter_acordado.bat` e deixar a janela aberta.
- [ ] No Colab: **Ambiente de execução > Alterar tipo > T4 GPU**, enviar o `.ipynb` novo e rodar todas as células.
- [ ] Conferir na célula 6 qual foi o "Estado dos dados": `importar_legado` (reaproveitou os dados antigos) ou `processar` (vai rodar o pipeline). Se aparecer `processar` e você esperava reaproveitar, leia a linha entre parênteses logo abaixo: ela diz por quê.
- [ ] Decidir se "armazenar os 100.000 arquivos no Drive" significa apenas o resultado do pipeline (como está) ou também copiar os `.mid` aprovados. Ver `004`, limitações.
- [ ] Depois do download, extrair o `.zip` na raiz do projeto (cria `modelos/` e `relatorios/`) e **reiniciar o `streamlit run`**.
- [ ] Relatar se o Colab de verdade se comportou como o teste local (principalmente a velocidade ao ler/gravar no Drive).

## Para o git
- [x] `.gitignore`: a regra `modelos/` ignorava também `src/modelos/`. Você removeu a regra, e `src/modelos/` já pode ser versionado (`git add src/modelos`).
- [ ] **Efeito colateral da remoção:** a pasta `modelos/` da raiz (checkpoints `.pt`, vários MB) também deixou de ser ignorada e aparece como não rastreada. Para ignorar só ela, adicione ao `.gitignore` a linha `/modelos/` (com a barra inicial). Se o grupo quiser versionar o modelo final de propósito, ignore este item. (As ferramentas do assistente não conseguem editar o `.gitignore`.)

## Qualidade da música (próximos passos)
- [ ] **Melodia fora do tempo da base:** corrigida a deriva por `0.12` (ver `006`), mas **falta ouvir** e confirmar. Se ainda estiver fora, a causa provável é que o modelo não conhece compassos (não acentua os tempos fortes); aí é preciso guiar as notas pela posição no compasso, não só pela harmonia.
- [ ] Escuta manual com e sem "Guiar melodia pela harmonia" e ajuste dos pesos (+3,0 / +1,5).
- [ ] Retreino com tokens de acorde (`CHORD_x`) intercalados na melodia, para o modelo aprender a harmonia em vez de ser guiado por regra. Exige reprocessar os dados e treinar em GPU.
- [x] Medir a LSTM com `scripts/avaliar_geracao.py --modelo lstm` (feito, ver `010`).
- [ ] Ouvir a LSTM depois da correção `011` (repetição caiu de 48% para 13%, cobertura da duração de 56% para 98%). O que sobra: ritmo fora do beat (~32%); se incomodar, avaliar guia de ritmo (ver `008`).

## Documentação
- [ ] Atualizar `README.md` (cita uma pasta `poc/` que não existe e descreve geração condicionada à harmonia, o que só é verdade agora, via guia).
- [ ] Atualizar `relatorios/feedback_testes_app.md` com os resultados de `002`.
- [ ] Investigar a diferença entre os dados do notebook e os de `scripts/03` e `04` (ver `004`, limitações).

## Treino da LSTM
- [x] Concluído: 20 épocas, resultados em `relatorios/resultados_lstm.json` (ver `010`). Cada época levou 3.100 a 4.100 s no Colab.
- [ ] Causa da lentidão da LSTM (~3x o Transformer por época) **não diagnosticada**. Só importa se for retreinar.

