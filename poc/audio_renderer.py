"""
audio_renderer.py
Converte um arquivo .mid para .wav usando FluidSynth (se disponível).
Retorna None se FluidSynth não estiver instalado — o app usa o player JS como fallback.
"""

from pathlib import Path


def midi_para_wav(caminho_mid: str, caminho_wav: str) -> str:
    from midi2audio import FluidSynth  # levanta ImportError se não instalado
    fs = FluidSynth()
    fs.midi_to_audio(caminho_mid, caminho_wav)
    return caminho_wav


def renderizar(caminho_mid: str) -> str | None:
    """
    Tenta converter .mid → .wav.
    Retorna o caminho do WAV gerado, ou None se não for possível.
    """
    try:
        caminho_wav = str(Path(caminho_mid).with_suffix(".wav"))
        return midi_para_wav(caminho_mid, caminho_wav)
    except ImportError:
        return None  # midi2audio / FluidSynth não instalado
    except Exception:
        return None
