# 012. LSTM: ritmo uniforme e corrido (160 notas em 20 s)

## Problema
Relato do usuário, com print (Dó Maior, 120 BPM, 20 s, LSTM): 160 notas em 10 compassos, ou seja, 4 notas por beat o tempo todo, com o mesmo desenho a cada acorde. Soava "estranho".

## Causa (medida, 10 gerações)
Depois de 011, a LSTM passou a cobrir a duração pedida, mas escolhe `DURATION_0.25` (semicolcheia) em ~70% das notas (516 de ~740 durações). Média de ~76 notas por geração (o print teve 160). O Transformer, nas mesmas condições, usa colcheias a mínimas e faz ~40 notas.

## O que foi alterado
- `src/modelos/lstm_model.py`: viés de logit nas durações, aplicado só quando o último token é uma nota (`VIES_DURACAO_PADRAO`): `DURATION_0.25` −0,8 e `DURATION_1.00` +0,2. Parâmetro opcional `vies_duracao` em `gerar()`.
- Tentei antes −1,5 / +0,5: tirou todas as semicolcheias e 53% das notas viraram semínimas (monótono). Por isso a versão suave.

## Resultado (15 gerações, Dó Maior, 120 BPM, 20 s)
| Duração | Fração das notas |
|---|---|
| 1/4 beat | 5% |
| 1/2 beat | 43% |
| 1 beat | 30% |
| 2 beats | 22% |

Notas por geração: ~39. Em `scripts/avaliar_geracao.py --modelo lstm --n 20`: tempos fortes no acorde 95%, repetições seguidas 7%, alturas distintas 9,0. A harmonia não piorou.

## Limitações
- Valores (−0,8 / +0,2) escolhidos por medida, **não de ouvido**. Se ainda soar estranho, ajustar em `VIES_DURACAO_PADRAO`.
- O ritmo continua sem guia de compasso (ver 008).
- Reiniciar o `streamlit run` para recarregar o módulo.
