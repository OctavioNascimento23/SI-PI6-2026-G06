# 006. Melodia fora do tempo da base: alinhamento à grade rítmica

## Problema
Relato do usuário: a melodia está boa, mas a base (acordes) e a melodia ficam fora de tempo.

## Causa (encontrada)
Os tokens de duração vêm do treino com o formato `.2f`, então a duração de 1/32 de semibreve (0,125 beat) virou o texto `0.12`. O `midi_builder` lia `0.12` literalmente e somava segundos a cada nota. Cada token `0.12` e `REST_0.12` perde 0,005 beat, e o erro **se acumula** ao longo da peça, deslocando as notas seguintes em relação aos acordes, que estão exatamente nos compassos.

Medição (Transformer, Dó Maior, 120 BPM, 20 s, 20 gerações), posição do início das notas dentro do beat, **antes** da correção: só cerca de 62% das notas caíam em 0, 0,25, 0,5 ou 0,75. O restante ficava em posições intermediárias, como 0,07 a 0,12 e 0,33 a 0,37, que são notas deslocadas.

## O que foi alterado
`src/midi_builder.py`:
- `_beats()`: converte `0.12` de volta para 0,125.
- O tempo da melodia passa a ser acumulado em **beats** e só depois convertido em segundos.
- Início e fim de cada nota são encaixados em uma grade de 1/32 (`grade_beats=0.125`), a mesma menor grade do pipeline de dados.
- Notas que ficariam com duração zero depois do encaixe são descartadas.

`limitar_duracao()` **não foi alterado** e ainda lê `0.12` literalmente; o erro dele é de poucos milissegundos no corte final.

## Como foi verificado
Depois da correção (20 gerações, 811 notas de melodia): o desvio máximo em relação à grade de 1/32 foi de 0,002 beat, que é o arredondamento de ticks do arquivo MIDI. 9 notas (cerca de 1%) foram descartadas pelo encaixe.

Não comparei as duas versões com o mesmo teste automático, só medi o antes e o depois com métodos diferentes. Também **não ouvi** o resultado.

## Limitações
- Não confirmei que esta era a causa do que o usuário ouve. O erro corrigido é de dezenas de milissegundos que se acumulam; pode ser só parte do problema.
- **Outra causa provável, não corrigida:** o modelo não conhece compassos. A melodia começa no tempo 0, mas o modelo aprendeu com MIDIs de qualquer fase rítmica, então pode acentuar notas fora dos tempos fortes da base. A medição acima mostra que as notas se distribuem em todo o beat, não só nos tempos fortes.
- O WAV usa o sintetizador próprio (FluidSynth não foi encontrado nesta máquina). Não verifiquei se o sintetizador adiciona atraso.
- Só o caminho do Transformer foi testado ponta a ponta; Markov e LSTM usam o mesmo `construir_midi_completo`.
