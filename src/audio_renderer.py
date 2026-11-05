"""
audio_renderer.py
Renderiza arquivos MIDI para WAV:
1. Prioritário: FluidSynth (se soundfont e executável estiverem disponíveis)
2. Fallback nativo: Síntese de áudio aditiva via pretty_midi (100% Python, sem dependências externas)
Garante que o áudio WAV com ambas as faixas (acordes + melodia) seja sempre gerado.
"""

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


def renderizar(caminho_midi: str, caminho_wav: Optional[str] = None, fs: int = 44100) -> Optional[str]:
    """
    Renderiza o arquivo MIDI para WAV.
    Tenta primeiro FluidSynth; se não disponível, utiliza síntese nativa do pretty_midi.
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

    # 2. Fallback Nativo via PrettyMIDI (Sintetizador Aditivo de Áudio)
    try:
        midi = pretty_midi.PrettyMIDI(str(p_midi))
        sinal = midi.synthesize(fs=fs)
        
        # Normalização do volume para evitar clipping
        pico = np.max(np.abs(sinal))
        if pico > 0:
            sinal = sinal / pico * 0.95

        sinal_int16 = (sinal * 32767).astype(np.int16)

        p_wav.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(p_wav), "wb") as f_wav:
            f_wav.setnchannels(1)  # Mono
            f_wav.setsampwidth(2)  # 16-bit
            f_wav.setframerate(fs)
            f_wav.writeframes(sinal_int16.tobytes())

        return str(p_wav) if p_wav.exists() else None
    except Exception as e:
        print(f"Aviso na renderização de áudio: {e}")
        return None
