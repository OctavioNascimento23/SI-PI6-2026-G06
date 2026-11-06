"""
Gera um MIDI com o midi-model do SkyTNT (Transformer já treinado).
A tonalidade, o BPM e a duração vêm da interface. Os instrumentos vêm do modelo.
"""

import sys
from pathlib import Path

import numpy as np
import pretty_midi
import torch

RAIZ = Path(__file__).resolve().parent.parent
PASTA_CODIGO = RAIZ / "third_party" / "midi-model"
PASTA_PESOS = RAIZ / "modelos" / "skytnt"
_MODELO = None

# sf = acidentes (negativo é bemol), mi = 0 maior / 1 menor. O tokenizer guarda sf + 7.
ASSINATURAS = {
    "Dó Maior": (0, 0),
    "Ré Maior": (2, 0),
    "Mi Maior": (4, 0),
    "Fá Maior": (-1, 0),
    "Sol Maior": (1, 0),
    "Lá Maior": (3, 0),
    "Si Maior": (5, 0),
    "Lá Menor": (0, 1),
    "Mi Menor": (1, 1),
    "Ré Menor": (-1, 1),
    "Sol Menor": (-2, 1),
    "Dó Menor": (-3, 1),
}


def _importar():
    if not PASTA_CODIGO.exists():
        raise FileNotFoundError(
            "Código do SkyTNT não encontrado em third_party/midi-model. "
            "Clone https://github.com/SkyTNT/midi-model nessa pasta."
        )
    caminho = str(PASTA_CODIGO)
    if caminho not in sys.path:
        sys.path.insert(0, caminho)
    from midi_model import MIDIModel, MIDIModelConfig
    import MIDI

    return MIDIModel, MIDIModelConfig, MIDI


def carregar():
    """Carrega o tv2o-medium uma vez e deixa na GPU, se houver."""
    global _MODELO
    if _MODELO is not None:
        return _MODELO

    config_path = PASTA_PESOS / "config.json"
    pesos_path = PASTA_PESOS / "model.safetensors"
    if not config_path.exists() or not pesos_path.exists():
        raise FileNotFoundError(
            "Pesos não encontrados em modelos/skytnt. "
            "Baixe config.json e model.safetensors de skytnt/midi-model-tv2o-medium."
        )

    MIDIModel, MIDIModelConfig, _ = _importar()
    from safetensors.torch import load_file

    config = MIDIModelConfig.from_json_file(str(config_path))
    modelo = MIDIModel(config)
    estado = load_file(str(pesos_path))
    faltando, _ = modelo.load_state_dict(estado, strict=False)
    if len(faltando) > 20:
        raise RuntimeError(f"O checkpoint não encaixou no modelo ({len(faltando)} tensores faltando).")

    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    tipo = torch.bfloat16 if dispositivo == "cuda" else torch.float32
    modelo.to(dispositivo, dtype=tipo).eval()
    _MODELO = modelo
    return modelo


def _prompt(tokenizer, tonalidade: str, bpm: int) -> np.ndarray:
    sf, mi = ASSINATURAS[tonalidade]
    eventos = [
        ["time_signature", 0, 0, 0, 3, 1],
        ["key_signature", 0, 0, 0, sf + 7, mi],
        ["set_tempo", 0, 0, 0, int(bpm)],
    ]
    inicio = [tokenizer.bos_id] + [tokenizer.pad_id] * (tokenizer.max_token_seq - 1)
    sequencia = [inicio] + [tokenizer.event2tokens(evento) for evento in eventos]
    return np.asarray(sequencia, dtype=np.int64)


def _cortar(caminho: Path, duracao_seg: float) -> None:
    midi = pretty_midi.PrettyMIDI(str(caminho))
    for instrumento in midi.instruments:
        instrumento.notes = [n for n in instrumento.notes if n.start < duracao_seg]
        for nota in instrumento.notes:
            if nota.end > duracao_seg:
                nota.end = duracao_seg
    midi.write(str(caminho))


def gerar_midi(
    tonalidade: str,
    bpm: int,
    duracao_seg: float,
    temperatura: float,
    caminho_saida: str,
    max_eventos: int | None = None,
) -> str:
    """Gera o MIDI do modelo e corta na duração pedida."""
    _, _, MIDI = _importar()
    modelo = carregar()
    tokenizer = modelo.tokenizer
    prompt = _prompt(tokenizer, tonalidade, bpm)
    eventos = max_eventos or min(768, max(160, int(duracao_seg * 14)))
    temperatura = float(min(1.2, max(0.5, temperatura)))
    gerador = torch.Generator(modelo.device).manual_seed(int(torch.randint(0, 2**31 - 1, (1,)).item()))

    tokens = modelo.generate(
        prompt=prompt,
        batch_size=1,
        max_len=len(prompt) + eventos,
        temp=temperatura,
        top_p=0.94,
        top_k=20,
        generator=gerador,
    )
    partitura = tokenizer.detokenize(tokens[0])
    caminho = Path(caminho_saida)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(MIDI.score2midi(partitura))
    _cortar(caminho, float(duracao_seg))
    return str(caminho)


def resumir(caminho: str) -> dict:
    """Conta notas e faixas de um MIDI já gravado, para a tela."""
    from pretty_midi.constants import INSTRUMENT_MAP

    midi = pretty_midi.PrettyMIDI(caminho)
    notas = []
    faixas = []
    for instrumento in midi.instruments:
        if instrumento.is_drum:
            nome = "Bateria"
        else:
            nome = INSTRUMENT_MAP[int(instrumento.program) % 128]
        faixas.append(f"{nome} ({len(instrumento.notes)})")
        if not instrumento.is_drum:
            notas.extend(int(n.pitch) for n in instrumento.notes)
    return {
        "notas": sum(len(i.notes) for i in midi.instruments),
        "faixas": ", ".join(faixas) if faixas else "nenhuma",
        "grave": min(notas) if notas else None,
        "aguda": max(notas) if notas else None,
        "duracao": round(float(midi.get_end_time()), 2),
    }
