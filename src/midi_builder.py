"""
midi_builder.py
Construtor de arquivos MIDI (.mid) multifaixa:
- Faixa 1: Acompanhamento Harmônico (Progressão de Acordes)
- Faixa 2: Linha Melódica Principal
"""

from pathlib import Path
from typing import List, Dict, Union, Optional
import pretty_midi


# Programas General MIDI populares:
# 0: Acoustic Grand Piano, 4: Electric Piano 1, 19: Church Organ, 24: Acoustic Guitar (nylon),
# 40: Violin, 48: String Ensemble 1, 56: Trumpet, 73: Flute, 80: Lead 1 (square)
PROGRAMAS_GM = {
    "Piano Acústico": 0,
    "Piano Elétrico": 4,
    "Violão Nylon": 24,
    "Cordas / Strings": 48,
    "Flauta": 73,
    "Sintetizador Lead": 80,
}


def limitar_duracao(tokens: List[str], bpm: int, duracao_max_seg: float) -> List[str]:
    """
    Trunca a lista de tokens para que a duração acumulada não ultrapasse duracao_max_seg.
    """
    seg_por_beat = 60.0 / bpm
    cursor = 0.0
    resultado = []

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok.startswith("NOTE_"):
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


def construir_midi_completo(
    tokens_melodia: List[str],
    acordes_base: List[Dict],
    bpm: int,
    caminho_saida: Union[str, Path],
    programa_melodia: int = 0,
    programa_acordes: int = 4,
    volume_melodia: int = 95,
    volume_acordes: int = 70,
) -> str:
    """
    Gera um arquivo MIDI multifaixa completo com Faixa de Harmonia (Acordes) e Faixa de Melodia.
    """
    caminho_saida = Path(caminho_saida)
    caminho_saida.parent.mkdir(parents=True, exist_ok=True)

    seg_por_beat = 60.0 / bpm
    midi = pretty_midi.PrettyMIDI(initial_tempo=float(bpm))

    # -------------------------------------------------------------
    # 1. FAIXA DE ACOMPANHAMENTO (PROGRESSÃO DE ACORDES)
    # -------------------------------------------------------------
    faixa_acordes = pretty_midi.Instrument(
        program=programa_acordes,
        name="Acompanhamento (Acordes)"
    )

    for ac in acordes_base:
        t_inicio = ac["inicio_seg"]
        t_fim = ac["fim_seg"]
        notas_acorde = ac.get("notas_midi", [])

        # Para cada nota da tríade/tétrade do acorde
        for pitch in notas_acorde:
            nota = pretty_midi.Note(
                velocity=volume_acordes,
                pitch=pitch,
                start=t_inicio,
                end=t_fim,
            )
            faixa_acordes.notes.append(nota)

    midi.instruments.append(faixa_acordes)

    # -------------------------------------------------------------
    # 2. FAIXA DA MELODIA PRINCIPAL
    # -------------------------------------------------------------
    faixa_melodia = pretty_midi.Instrument(
        program=programa_melodia,
        name="Melodia Principal"
    )

    cursor = 0.0
    pitch_pendente: Optional[int] = None
    notas_melodia = []

    i = 0
    while i < len(tokens_melodia):
        tok = tokens_melodia[i]

        if tok.startswith("NOTE_"):
            try:
                pitch_pendente = int(tok.split("_")[1])
            except ValueError:
                pitch_pendente = None
            i += 1

        elif tok.startswith("DURATION_") and pitch_pendente is not None:
            try:
                dur_beats = float(tok.split("_")[1])
                dur_seg = dur_beats * seg_por_beat
                nota = pretty_midi.Note(
                    velocity=volume_melodia,
                    pitch=pitch_pendente,
                    start=cursor,
                    end=cursor + dur_seg,
                )
                notas_melodia.append(nota)
                cursor += dur_seg
            except ValueError:
                pass
            pitch_pendente = None
            i += 1

        elif tok.startswith("REST_"):
            try:
                dur_beats = float(tok.split("_")[1])
                cursor += dur_beats * seg_por_beat
            except ValueError:
                pass
            pitch_pendente = None
            i += 1

        else:
            i += 1

    faixa_melodia.notes = notas_melodia
    midi.instruments.append(faixa_melodia)

    midi.write(str(caminho_saida))
    return str(caminho_saida)


def tokens_para_midi(tokens: List[str], bpm: int, caminho_saida: Union[str, Path]) -> str:
    """Compatibilidade legada com melodia monofônica simples."""
    return construir_midi_completo(
        tokens_melodia=tokens,
        acordes_base=[],
        bpm=bpm,
        caminho_saida=caminho_saida,
    )
