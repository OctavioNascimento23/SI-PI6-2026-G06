"""
midi_builder.py
Converte uma lista de tokens gerados pelo Markov em um arquivo .mid válido.
"""

from pathlib import Path

import pretty_midi


def limitar_duracao(tokens: list[str], bpm: int, duracao_max_seg: float) -> list[str]:
    """
    Corta a lista de tokens no ponto em que a duração acumulada
    ultrapassaria duracao_max_seg. Retorna a lista truncada.
    """
    seg_por_beat = 60.0 / bpm
    cursor = 0.0
    resultado = []

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok.startswith("NOTE_"):
            # Precisa do DURATION_ seguinte para saber quanto avança
            if i + 1 < len(tokens) and tokens[i + 1].startswith("DURATION_"):
                dur_beats = float(tokens[i + 1].split("_")[1])
                dur_seg = dur_beats * seg_por_beat
                if cursor + dur_seg > duracao_max_seg:
                    break
                resultado.append(tok)
                resultado.append(tokens[i + 1])
                cursor += dur_seg
                i += 2
            else:
                resultado.append(tok)
                i += 1

        elif tok.startswith("REST_"):
            dur_beats = float(tok.split("_")[1])
            dur_seg = dur_beats * seg_por_beat
            if cursor + dur_seg > duracao_max_seg:
                break
            resultado.append(tok)
            cursor += dur_seg
            i += 1

        else:
            resultado.append(tok)
            i += 1

    return resultado


def tokens_para_midi(tokens: list[str], bpm: int, caminho_saida: str | Path) -> str:
    """
    Converte tokens para um arquivo .mid e salva em caminho_saida.
    Retorna o caminho salvo como string.
    """
    caminho_saida = Path(caminho_saida)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)

    seg_por_beat = 60.0 / bpm

    midi = pretty_midi.PrettyMIDI(initial_tempo=float(bpm))
    instrumento = pretty_midi.Instrument(program=0, name="Melodia")  # piano

    cursor = 0.0
    pitch_pendente: int | None = None
    notas = []

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok.startswith("NOTE_"):
            pitch_pendente = int(tok.split("_")[1])
            i += 1

        elif tok.startswith("DURATION_") and pitch_pendente is not None:
            dur_beats = float(tok.split("_")[1])
            dur_seg = dur_beats * seg_por_beat
            nota = pretty_midi.Note(
                velocity=80,
                pitch=pitch_pendente,
                start=cursor,
                end=cursor + dur_seg,
            )
            notas.append(nota)
            cursor += dur_seg
            pitch_pendente = None
            i += 1

        elif tok.startswith("REST_"):
            dur_beats = float(tok.split("_")[1])
            cursor += dur_beats * seg_por_beat
            pitch_pendente = None
            i += 1

        else:
            i += 1

    instrumento.notes = notas
    midi.instruments.append(instrumento)
    midi.write(str(caminho_saida))
    return str(caminho_saida)
