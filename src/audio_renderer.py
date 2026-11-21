"""
audio_renderer.py
Renderiza arquivos MIDI para WAV com alta qualidade sonora:
1. Prioritário: FluidSynth (se soundfont e executável estiverem disponíveis no sistema)
2. Sintetizador Físico-Harmônico Nativo em Python (com Envelope ADSR de Piano, Harmônicos e Espacialização Estéreo)
"""

import math
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Optional
import numpy as np
import pretty_midi


def soundfont_padrao() -> Optional[Path]:
    """Procura por soundfonts instalados no sistema operacional."""
    candidatos = [
        Path("/usr/share/sounds/sf2/FluidR3_GM.sf2"),
        Path("/usr/share/sounds/sf2/default.sf2"),
        Path("/usr/share/soundfonts/default.sf2"),
        Path("C:/soundfonts/default.sf2"),
        Path("C:/Program Files/FluidSynth/sf2/default.sf2"),
    ]
    for c in candidatos:
        if c.exists():
            return c
    return None


def sintetizar_nota(
    freq: float,
    duracao_seg: float,
    velocity: int,
    fs: int = 44100,
    tipo: str = "melodia",
) -> np.ndarray:
    """
    Gera o sinal de áudio de uma nota individual com harmônicos de piano e envelope ADSR orgânico.
    """
    num_samples = int(duracao_seg * fs)
    if num_samples <= 0:
        return np.zeros(0, dtype=np.float32)

    t = np.linspace(0, duracao_seg, num_samples, endpoint=False, dtype=np.float32)

    # 1. Geração de Harmônicos de Piano (Fundamental + 2º, 3º e 4º harmônicos com decaimento)
    if tipo == "acordes":
        # Timbre mais aveludado e suave para os acordes de base
        onda = (
            1.0 * np.sin(2 * np.pi * freq * t)
            + 0.35 * np.sin(2 * np.pi * 2 * freq * t)
            + 0.12 * np.sin(2 * np.pi * 3 * freq * t)
            + 0.04 * np.sin(2 * np.pi * 4 * freq * t)
        )
        taxa_decaimento = 1.2
    else:
        # Timbre brilhante e definido para o solo melódico
        onda = (
            1.0 * np.sin(2 * np.pi * freq * t)
            + 0.45 * np.sin(2 * np.pi * 2 * freq * t)
            + 0.20 * np.sin(2 * np.pi * 3 * freq * t)
            + 0.08 * np.sin(2 * np.pi * 4 * freq * t)
        )
        taxa_decaimento = 2.0

    # 2. Envelope ADSR (Attack suave de 12ms para eliminar estalos + Decay Exponencial + Release)
    t_attack = min(0.015, duracao_seg * 0.1)
    samples_attack = int(t_attack * fs)

    envelope = np.exp(-taxa_decaimento * t)
    if samples_attack > 0:
        ramp = np.linspace(0, 1, samples_attack)
        envelope[:samples_attack] *= ramp

    # Fade out suave nos últimos 15ms para evitar cliques
    samples_release = min(int(0.02 * fs), num_samples // 4)
    if samples_release > 0:
        fade = np.linspace(1, 0, samples_release)
        envelope[-samples_release:] *= fade

    amp = (velocity / 127.0) * 0.5
    return (onda * envelope * amp).astype(np.float32)


def sintetizar_midi_harmonico(midi: pretty_midi.PrettyMIDI, fs: int = 44100) -> np.ndarray:
    """
    Sintetiza todas as faixas do MIDI (harmonia + melodia) em áudio estéreo harmonizado.
    """
    duracao_total = midi.get_end_time() + 0.5
    total_samples = int(duracao_total * fs) + 1000

    canal_esq = np.zeros(total_samples, dtype=np.float32)
    canal_dir = np.zeros(total_samples, dtype=np.float32)

    for i, inst in enumerate(midi.instruments):
        # Diferenciação de canal estéreo e timbre:
        # Faixa 0 (Acordes): Espacializada nas laterais para abrir o campo sonoro
        # Faixa 1 (Melodia): Centralizada com destaque
        is_acordes = (i == 0) or ("acorde" in inst.name.lower()) or ("acompanhamento" in inst.name.lower())
        tipo_timbre = "acordes" if is_acordes else "melodia"
        pan_esq = 0.7 if is_acordes else 0.5
        pan_dir = 0.7 if is_acordes else 0.5

        for note in inst.notes:
            freq = pretty_midi.note_number_to_hz(note.pitch)
            dur = max(0.05, note.end - note.start)
            sinal_nota = sintetizar_nota(
                freq=freq,
                duracao_seg=dur,
                velocity=note.velocity,
                fs=fs,
                tipo=tipo_timbre,
            )

            idx_inicio = int(note.start * fs)
            idx_fim = idx_inicio + len(sinal_nota)

            if idx_fim <= total_samples:
                canal_esq[idx_inicio:idx_fim] += sinal_nota * pan_esq
                canal_dir[idx_inicio:idx_fim] += sinal_nota * pan_dir
            elif idx_inicio < total_samples:
                tamanho_parcial = total_samples - idx_inicio
                canal_esq[idx_inicio:total_samples] += sinal_nota[:tamanho_parcial] * pan_esq
                canal_dir[idx_inicio:total_samples] += sinal_nota[:tamanho_parcial] * pan_dir

    # Normalização
    pico = max(np.max(np.abs(canal_esq)), np.max(np.abs(canal_dir)), 1e-5)
    canal_esq = (canal_esq / pico * 0.90)
    canal_dir = (canal_dir / pico * 0.90)

    # Combina em estéreo intercalado [L, R, L, R, ...]
    estereo = np.vstack((canal_esq, canal_dir)).T
    return (estereo * 32767).astype(np.int16)


def renderizar(caminho_midi: str, caminho_wav: Optional[str] = None, fs: int = 44100) -> Optional[str]:
    """
    Renderiza o arquivo MIDI para WAV.
    Tenta FluidSynth; se não disponível, utiliza o sintetizador harmônico nativo com ADSR.
    """
    p_midi = Path(caminho_midi)
    if not p_midi.exists():
        return None

    if caminho_wav is None:
        p_wav = p_midi.with_suffix(".wav")
    else:
        p_wav = Path(caminho_wav)

    # 1. Tentativa via FluidSynth
    fluidsynth = shutil.which("fluidsynth")
    sf2 = soundfont_padrao()

    if fluidsynth and sf2:
        cmd = [
            fluidsynth,
            "-ni",
            str(sf2),
            str(p_midi),
            "-F",
            str(p_wav),
            "-r",
            str(fs),
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if p_wav.exists() and p_wav.stat().st_size > 1000:
                return str(p_wav)
        except Exception:
            pass

    # 2. Sintetizador Harmônico Orgânico Nativo em Python
    try:
        midi = pretty_midi.PrettyMIDI(str(p_midi))
        audio_int16 = sintetizar_midi_harmonico(midi, fs=fs)

        p_wav.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(p_wav), "wb") as f_wav:
            f_wav.setnchannels(2)  # Estéreo
            f_wav.setsampwidth(2)  # 16-bit
            f_wav.setframerate(fs)
            f_wav.writeframes(audio_int16.tobytes())

        return str(p_wav) if p_wav.exists() else None
    except Exception as e:
        print(f"Aviso na renderização de áudio: {e}")
        return None
