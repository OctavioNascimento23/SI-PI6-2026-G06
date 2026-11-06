"""
Arranjo em cima da melodia da LSTM.
Acrescenta acorde, baixo e bateria em 4/4, presos na tonalidade e no BPM.
"""

from pathlib import Path

import pretty_midi

from poc.midi_builder import notas_da_melodia
from poc.teoria_musical import ESCALAS

KICK = 36
SNARE = 38
HAT = 42

ESTILOS = {
    "Pop": {
        "baixo": 33,
        "acorde": 0,
        "compassos_acorde": 1,
        "vel_baixo": 96,
        "vel_acorde": 52,
        "vel_kick": 110,
        "vel_snare": 96,
        "vel_hat": 58,
        "oitavas_chimbal": True,
        "kicks": (0, 4),
        "snares": (2, 6),
        "kick_extra": False,
    },
    "Rock": {
        "baixo": 34,
        "acorde": 4,
        "compassos_acorde": 1,
        "vel_baixo": 108,
        "vel_acorde": 64,
        "vel_kick": 120,
        "vel_snare": 112,
        "vel_hat": 70,
        "oitavas_chimbal": True,
        "kicks": (0, 4),
        "snares": (2, 6),
        "kick_extra": True,
    },
    "Balada": {
        "baixo": 32,
        "acorde": 89,
        "compassos_acorde": 2,
        "vel_baixo": 78,
        "vel_acorde": 42,
        "vel_kick": 80,
        "vel_snare": 70,
        "vel_hat": 40,
        "oitavas_chimbal": False,
        "kicks": (0,),
        "snares": (4,),
        "kick_extra": False,
    },
}


def _pitch_perto(classe: int, centro: int, minimo: int = 28, maximo: int = 84) -> int:
    volta = round((centro - classe) / 12)
    pitch = classe + 12 * volta
    while pitch < minimo:
        pitch += 12
    while pitch > maximo:
        pitch -= 12
    return int(pitch)


def _triade(tonalidade: str) -> tuple[int, int, int]:
    escala = ESCALAS[tonalidade]
    return escala[0], escala[2], escala[4]


def _vozes_do_acorde(tonalidade: str) -> list[int]:
    raiz, terca, quinta = _triade(tonalidade)
    raiz_p = _pitch_perto(raiz, 60, 48, 72)
    terca_p = _pitch_perto(terca, raiz_p + 4, 48, 84)
    if terca_p <= raiz_p:
        terca_p += 12
    quinta_p = _pitch_perto(quinta, terca_p + 3, 48, 88)
    if quinta_p <= terca_p:
        quinta_p += 12
    return [raiz_p, terca_p, quinta_p]


def _adicionar(inst, pitch, inicio, duracao, velocidade):
    if duracao <= 0.02 or inicio < 0:
        return
    inst.notes.append(
        pretty_midi.Note(
            velocity=int(velocidade),
            pitch=int(pitch),
            start=float(inicio),
            end=float(inicio + duracao),
        )
    )


def _bateria(cfg, beat, duracao):
    inst = pretty_midi.Instrument(program=0, is_drum=True, name="Bateria")
    passo = beat / 2
    n = int(duracao / passo + 0.001)
    dur_hit = min(0.12, passo * 0.8)
    dur_hat = min(0.06, passo * 0.7)
    for i in range(n):
        inicio = i * passo
        if inicio >= duracao - 0.01:
            break
        pos = i % 8
        hat = pos % 2 == 0 or cfg["oitavas_chimbal"]
        if hat:
            _adicionar(inst, HAT, inicio, dur_hat, cfg["vel_hat"])
        if pos in cfg["kicks"]:
            _adicionar(inst, KICK, inicio, dur_hit, cfg["vel_kick"])
        if pos == 5 and cfg["kick_extra"]:
            _adicionar(inst, KICK, inicio, dur_hit, cfg["vel_kick"] - 8)
        if pos in cfg["snares"]:
            _adicionar(inst, SNARE, inicio, dur_hit, cfg["vel_snare"])
    return inst


def _baixo(cfg, tonalidade, beat, duracao):
    inst = pretty_midi.Instrument(program=cfg["baixo"], name="Baixo")
    raiz, _, quinta = _triade(tonalidade)
    notas = (
        _pitch_perto(raiz, 40, 28, 52),
        _pitch_perto(quinta, 43, 28, 55),
    )
    n = int(duracao / beat + 0.001)
    for i in range(n):
        inicio = i * beat
        if inicio >= duracao - 0.01:
            break
        pitch = notas[0] if i % 2 == 0 else notas[1]
        _adicionar(inst, pitch, inicio, beat * 0.85, cfg["vel_baixo"])
    return inst


def _acordes(cfg, tonalidade, beat, duracao):
    inst = pretty_midi.Instrument(program=cfg["acorde"], name="Acordes")
    vozes = _vozes_do_acorde(tonalidade)
    compasso = 4 * beat * cfg["compassos_acorde"]
    t = 0.0
    while t < duracao - 0.05:
        dur = min(compasso * 0.96, duracao - t)
        for pitch in vozes:
            _adicionar(inst, pitch, t, dur, cfg["vel_acorde"])
        t += compasso
    return inst


def salvar_musica(tokens, tonalidade, bpm, duracao_seg, estilo, caminho_saida) -> str:
    """Grava melodia, acordes, baixo e bateria num único MIDI."""
    if estilo not in ESTILOS:
        estilo = "Pop"
    cfg = ESTILOS[estilo]
    caminho = Path(caminho_saida)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    midi = pretty_midi.PrettyMIDI(initial_tempo=float(bpm))
    melodia = pretty_midi.Instrument(program=0, name="Melodia")
    melodia.notes = notas_da_melodia(tokens, bpm)
    midi.instruments.append(melodia)
    beat = 60.0 / float(bpm)
    midi.instruments.append(_acordes(cfg, tonalidade, beat, float(duracao_seg)))
    midi.instruments.append(_baixo(cfg, tonalidade, beat, float(duracao_seg)))
    midi.instruments.append(_bateria(cfg, beat, float(duracao_seg)))
    midi.write(str(caminho))
    return str(caminho)
