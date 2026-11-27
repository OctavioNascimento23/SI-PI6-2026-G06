"""
harmonia_guia.py
Guia harmônico aplicado durante a amostragem (sem retreinar o modelo) e métricas
objetivas de aderência da melodia à harmonia.

Na hora de escolher cada NOTE_x, os logits do modelo são ajustados para:
  - proibir notas fora da tonalidade e fora da tessitura da melodia;
  - favorecer notas do acorde do compasso corrente (mais forte nos tempos fortes).
"""

from typing import Callable, Dict, List

import torch

from src.teoria_musical import ESCALAS

BEATS_POR_COMPASSO = 4.0

# Bônus (em unidades de logit, multiplicado por `peso_ritmo`) conforme o nível da grade onde a
# duração escolhida termina: 3 = no beat, 2 = em meio beat, 1 = em 1/4 de beat, 0 = em 1/8 ímpar.
_BONUS_NIVEL_RITMO = {3: 1.0, 2: 0.5, 1: 0.0, 0: -1.5}


def _beats_exato(valor: str) -> float:
    """O vocabulário grava 0,125 como '0.12' (formato .2f); aqui volta ao valor real."""
    v = float(valor)
    return 0.125 if v == 0.12 else v


def _nivel_grade(oitavos: int) -> int:
    if oitavos % 8 == 0:
        return 3
    if oitavos % 4 == 0:
        return 2
    if oitavos % 2 == 0:
        return 1
    return 0


def _acorde_no_beat(acordes: List[Dict], tempo_beats: float) -> Dict:
    idx = min(int(tempo_beats // BEATS_POR_COMPASSO), len(acordes) - 1)
    return acordes[idx]


def criar_guia_harmonico(
    token_para_id: Dict[str, int],
    acordes: List[Dict],
    tonalidade: str,
    bonus_tempo_forte: float = 3.0,
    bonus_tempo_fraco: float = 1.5,
    pitch_min: int = 52,
    pitch_max: int = 88,
    peso_ritmo: float = 0.0,
) -> Callable:
    """
    Retorna a função `ajustar_logits(logits, tempo_beats, tokens)` usada por `gerar()`.

    Além da harmonia, `peso_ritmo` > 0 ressincroniza o ritmo com a grade dos acordes: ao escolher a
    DURAÇÃO de uma nota, favorece as que terminam no beat / meio beat e penaliza as que terminam em
    1/8 ímpar; ao escolher uma PAUSA, só penaliza as que terminam em 1/8 ímpar. O relógio é
    recalculado aqui a partir dos tokens (com 0.12 = 0,125), ignorando `tempo_beats`.
    """
    escala = set(ESCALAS.get(tonalidade, ESCALAS["Dó Maior"]))
    notas = {
        int(tok.split("_")[1]): idx
        for tok, idx in token_para_id.items()
        if tok.startswith("NOTE_")
    }
    duracoes = {idx: round(_beats_exato(tok.split("_")[1]) * 8)
                for tok, idx in token_para_id.items() if tok.startswith("DURATION_")}
    pausas = {idx: round(_beats_exato(tok.split("_")[1]) * 8)
              for tok, idx in token_para_id.items() if tok.startswith("REST_")}

    def ajustar(logits: torch.Tensor, tempo_beats: float, tokens: List[str]) -> torch.Tensor:
        if peso_ritmo <= 0 and tokens and tokens[-1].startswith("NOTE_"):
            return logits  # sem ajuste de ritmo, o guia só age quando se espera uma nota
        if peso_ritmo > 0:
            pos = round(8 * sum(_beats_exato(t.split("_")[1]) for t in tokens
                                if t.startswith(("DURATION_", "REST_"))))
            if tokens and tokens[-1].startswith("NOTE_"):
                # Esperando a duração da nota: favorece terminar em ponto forte da grade
                novos = logits.clone()
                for idx, d in duracoes.items():
                    novos[idx] += peso_ritmo * _BONUS_NIVEL_RITMO[_nivel_grade(pos + d)]
                return novos
            logits = logits.clone()
            for idx, d in pausas.items():
                if _nivel_grade(pos + d) == 0:
                    logits[idx] += peso_ritmo * _BONUS_NIVEL_RITMO[0]
            tempo_beats = pos / 8.0

        classes_acorde = set(_acorde_no_beat(acordes, tempo_beats)["classes_pitch"])
        forte = abs(tempo_beats % 1.0) < 1e-6 and (tempo_beats % BEATS_POR_COMPASSO) % 2 == 0
        bonus = bonus_tempo_forte if forte else bonus_tempo_fraco

        novos = logits.clone()
        for pitch, idx in notas.items():
            if pitch < pitch_min or pitch > pitch_max or (pitch % 12) not in escala:
                novos[idx] = -float("inf")
            elif (pitch % 12) in classes_acorde:
                novos[idx] += bonus
        return novos

    return ajustar


def metricas_melodia(
    tokens: List[str],
    acordes: List[Dict],
    bpm: int,
    tonalidade: str,
) -> Dict[str, float]:
    """
    Métricas objetivas de uma melodia gerada:
      - frac_notas_no_acorde: fração de notas cuja classe de altura pertence ao acorde do compasso
      - frac_forte_no_acorde: idem, só para notas que começam em tempo forte (beats 1 e 3)
      - frac_notas_na_escala: fração de notas dentro da tonalidade
      - alturas_distintas, amplitude_semitons, pct_repeticoes_consecutivas
    """
    pitches: List[int] = []
    no_acorde: List[bool] = []
    forte_no_acorde: List[bool] = []

    tempo = 0.0
    pitch_pendente = None
    for tok in tokens:
        if tok.startswith("NOTE_"):
            pitch_pendente = int(tok.split("_")[1])
        elif tok.startswith("DURATION_"):
            if pitch_pendente is not None and acordes:
                ok = (pitch_pendente % 12) in _acorde_no_beat(acordes, tempo)["classes_pitch"]
                pitches.append(pitch_pendente)
                no_acorde.append(ok)
                if abs(tempo % 1.0) < 1e-6 and (tempo % BEATS_POR_COMPASSO) % 2 == 0:
                    forte_no_acorde.append(ok)
            tempo += float(tok.split("_")[1])
            pitch_pendente = None
        elif tok.startswith("REST_"):
            tempo += float(tok.split("_")[1])
            pitch_pendente = None

    escala = set(ESCALAS.get(tonalidade, ESCALAS["Dó Maior"]))
    n = len(pitches)
    reps = sum(1 for a, b in zip(pitches, pitches[1:]) if a == b)
    return {
        "n_notas": n,
        "frac_notas_no_acorde": sum(no_acorde) / n if n else 0.0,
        "frac_forte_no_acorde": sum(forte_no_acorde) / len(forte_no_acorde) if forte_no_acorde else 0.0,
        "frac_notas_na_escala": sum(1 for p in pitches if p % 12 in escala) / n if n else 0.0,
        "alturas_distintas": len(set(pitches)),
        "amplitude_semitons": (max(pitches) - min(pitches)) if n else 0,
        "pct_repeticoes_consecutivas": reps / (n - 1) if n > 1 else 0.0,
    }
