# 007. A progressão escolhida não condizia com os acordes tocados

## Problema
Relato do usuário: a progressão selecionada na tela não corresponde ao que é tocado.

## Causa (encontrada e medida)
`gerar_progressao_acordes` (`src/teoria_musical.py`) escolhia o mapa de graus pelo modo da **tonalidade** (`MAPA_GRAUS_MAIOR` ou `MAPA_GRAUS_MENOR`), sem olhar o modo da **progressão**. Graus sem correspondência no mapa caíam num fallback (offset 0, ou seja, a tônica).

Exemplos (antes da correção):
- Dó Maior + "Sentimental Menor (i - VI - III - VII)": tocava **Dó, Dó, Dó, Dó**.
- Dó Maior + "Blues / Melancolia (i - iv - v - i)": o mesmo.
- Lá Menor + "Pop / Hits (I - V - vi - IV)": tocava Lám, Mi, Lám, Lám.

## O que foi alterado
- `src/teoria_musical.py`: nova função `resolver_progressao(tonalidade, estilo)`, que retorna `(graus, mapa, tônica, aviso)`.
  - O modo da progressão é detectado pelos graus: se algum grau existe só no mapa menor (`i`, `iv`, `v`, `III`, `VI`, `VII`), a progressão é menor; senão, é maior.
  - Se o modo da progressão difere do da tonalidade, ela é tocada na **tonalidade relativa** (tônica +9 semitons para progressão menor; +3 para maior). As notas da escala são as mesmas, então a melodia continua combinando.
  - `gerar_progressao_acordes` passou a usar essa função.
- `src/gerador.py`: `compor()` devolve `aviso_progressao`.
- `app.py`: mostra o aviso (`st.info`) acima da seção "Estrutura Harmônica por Compasso" quando houver.
- `scripts/testar_progressoes.py`: teste novo, percorre as 12 tonalidades × 7 progressões.

Decisão de projeto: tocar na relativa, em vez de forçar os graus no modo errado, mantém acordes musicalmente corretos e a melodia dentro da escala. A consequência é que, por exemplo, em Dó Maior com a progressão menor, o centro tonal soa como Lá menor.

## Como foi verificado
- `python scripts/testar_progressoes.py`: **84 combinações, 0 problemas**. O teste exige que a raiz de todo acorde pertença à escala da tonalidade escolhida e que a progressão não colapse numa nota só.
- Geração completa com os 3 motores (Transformer, LSTM, Markov), Dó Maior + "Sentimental Menor": acordes Lám, Fá, Dó, Sol, repetidos, e aviso retornado.
- `app.py` passa em `ast.parse`.

## Limitações / pendências
- **Não abri o app no navegador**; o aviso na tela não foi visto, só o retorno de `compor()`.
- **Não ouvi** o áudio.
- Combinações em que o modo difere mostram um aviso: a tonalidade escolhida não é a tônica tocada. Se o grupo preferir outro comportamento (por exemplo, esconder progressões do modo oposto no seletor), é uma decisão de interface.
- A raiz dos acordes foi checada contra a escala; a terça e a quinta não foram checadas uma a uma (nas relativas, a escala é a mesma).
- O problema de tempo do Transformer (só ele sai do tempo) **não foi resolvido** aqui.
