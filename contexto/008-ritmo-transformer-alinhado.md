# 008. Melodia do Transformer adiantada e fora do tempo da base

## Problema
Relato do usuário (só no Transformer): a melodia fica **adiantada** em relação à progressão; no começo alinha e depois se afasta. Antes da correção 006, estava desalinhada desde o início.

## Causa (o que medi e o que é hipótese)
Medi com `scripts/medir_tempo.py` (20 gerações, Dó Maior, 120 BPM, 30 s), dividindo cada peça em 4 trechos.

**Medido (Transformer, antes):** notas que começam exatamente num beat: 27% → 20% → 23% → 20% nos 4 trechos (total 22,9%); 18% das notas começam fora da grade de 1/4 de beat. Ou seja, **a fase da melodia em relação ao beat se perde ao longo da peça**, e as notas só caem no começo do compasso em 6,8% dos casos.

**Mecanismo (hipótese bem apoiada, não provada):** os tokens do modelo guardam só *duração* e *pausa*, nunca a posição no compasso. O modelo não "sabe" onde está o beat; qualquer duração fora do padrão (por exemplo 0,125 ou 0,25 seguidos de uma duração longa) muda a fase e nada traz a melodia de volta. A LSTM tem o mesmo problema no começo (32% no beat no 1º quarto), mas, como seu ritmo tende a durações regulares, ela "se acerta" com o tempo (82% no 4º quarto).

**Descartado por medida:** o relógio interno do guia somava `0.12` em vez de 0,125 (bug irmão do 006). Medi: a deriva média ao fim da peça é de 0,03 beat no Transformer (máx 0,11), então **não explica** o problema.

Nos dados reais (300 arquivos de teste) a fase também não é toda no beat (29% → 18%), porque os dados não preservam o compasso; portanto o ritmo "solto" é aprendido do dataset, e não é um defeito de carregamento.

## O que foi alterado
- `src/harmonia_guia.py`: `criar_guia_harmonico(..., peso_ritmo)`. O guia passa a agir também ao escolher a **duração** e a **pausa**:
  - recalcula a posição em beats a partir dos tokens (tratando `0.12` como 0,125);
  - favorece durações que terminam no beat (+1,0 × peso) ou em meio beat (+0,5 × peso) e penaliza as que terminam em 1/8 ímpar (−1,5 × peso);
  - com `peso_ritmo=0` (padrão) o comportamento é o anterior.
- `src/gerador.py`: `_gerar_neural` usa `peso_ritmo=3.0` **só no Transformer**. A LSTM fica em 0.
- `src/modelos/transformer_model.py` e `lstm_model.py`: o guia agora é chamado em todo passo (antes só quando se esperava uma nota); o guia decide pelo último token.
- `scripts/medir_tempo.py`: métrica de alinhamento por trecho da peça.

## Como foi verificado
Mesmo script, mesmas sementes (0–19), antes × depois, Transformer:

| | no beat (4 trechos) | início de compasso | fora de 1/4 |
|---|---|---|---|
| antes | 27 / 20 / 23 / 20 % (total 22,9%) | 6,8% | 18,1% |
| depois (peso 3, final) | 63 / 54 / 52 / 56 % (total 55,9%) | 17,4% | 0,0% |

- A cobertura da duração pedida foi de 93% para 96%.
- A LSTM reproduziu **exatamente** a medida anterior (42,3% no beat), como esperado, pois não mudou.
- Varredura do peso (10 gerações, só ritmo): peso 0 → ~18% no beat; 1 → ~29%; 2 → ~39%; 3 → ~55%; 4 → ~71%. Na LSTM, pesos ≥ 2 colapsam o ritmo em semínimas (77–83% das notas com 1 beat), o que é alinhado, mas monótono; por isso não apliquei o ajuste nela. No Transformer, com peso 4, as durações ficam 0,25: 4%, 0,5: 34%, 1,0: 32%, 2,0: 31%, ainda variadas; escolhi 3 como compromisso. **Essa escolha é minha, não foi validada de ouvido.**
- `avaliar_geracao.py` (cenário C, com guia harmônico): 63% das notas no acorde, 88% nos tempos fortes, 100% na escala. Esse script **não** usa o peso de ritmo (padrão 0), então não mede a combinação final. Numa medida anterior, com 20 gerações, o peso de ritmo 2 e 4 não piorou a aderência ao acorde (61% → 69% e 68%), mas **o peso 3 usado no app não foi medido nessa métrica**.
- `testar_progressoes.py`: 84 combinações, 0 problemas.

## Limitações / pendências
- **Não ouvi o resultado.** As métricas mostram a melodia mais encaixada na grade dos acordes; se soa melhor, só o grupo pode confirmar.
- O ajuste é uma **correção na amostragem**, não no modelo. A causa de fundo (tokens sem posição no compasso) só se resolve retreinando com um token de posição (por exemplo `BAR` / `BEAT_n`), o que o usuário não quer para o Transformer.
- Só 55% das notas ficam no beat (não 100%): é de propósito, para não deixar o ritmo mecânico. Aumentar `peso_ritmo` em `src/gerador.py` deixa mais alinhado e mais regular.
- A menor duração (0,125) praticamente deixa de aparecer no Transformer com o ajuste.
- Os valores do guia (bônus por nível da grade) foram ajustados nos meus testes, só com Dó Maior e a progressão padrão, 120 BPM.
