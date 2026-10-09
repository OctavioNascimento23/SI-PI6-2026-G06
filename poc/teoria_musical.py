"""
teoria_musical.py
Mapeamento de tonalidades, pitches de escala e transposição de tokens.
"""

# Notas base por tonalidade (índices cromáticos 0–11)
ESCALAS = {
    "Dó Maior":  [0, 2, 4, 5, 7, 9, 11],
    "Ré Maior":  [2, 4, 6, 7, 9, 11, 1],
    "Mi Maior":  [4, 6, 8, 9, 11, 1, 3],
    "Fá Maior":  [5, 7, 9, 10, 0, 2, 4],
    "Sol Maior": [7, 9, 11, 0, 2, 4, 6],
    "Lá Maior":  [9, 11, 1, 2, 4, 6, 8],
    "Si Maior":  [11, 1, 3, 4, 6, 8, 10],
    "Lá Menor":  [9, 11, 0, 2, 4, 5, 7],
    "Mi Menor":  [4, 6, 7, 9, 11, 0, 2],
    "Ré Menor":  [2, 4, 5, 7, 9, 10, 0],
    "Sol Menor": [7, 9, 10, 0, 2, 3, 5],
    "Dó Menor":  [0, 2, 3, 5, 7, 8, 10],
}

NOMES_NOTAS = ["Dó", "Dó#", "Ré", "Ré#", "Mi", "Fá",
               "Fá#", "Sol", "Sol#", "Lá", "Lá#", "Si"]


def pitches_da_tonalidade(nome_tonalidade: str,
                          pitch_min: int = 36,
                          pitch_max: int = 96) -> list[int]:
    """Retorna todos os pitches MIDI válidos para a tonalidade no intervalo dado."""
    classes = set(ESCALAS[nome_tonalidade])
    return [p for p in range(pitch_min, pitch_max + 1) if p % 12 in classes]


def transpor_pitch(pitch: int, tonalidade: str) -> int:
    """
    Se o pitch não pertencer à escala, retorna o pitch mais próximo que pertença.
    """
    classes = set(ESCALAS[tonalidade])
    if pitch % 12 in classes:
        return pitch

    # Procura o vizinho mais próximo (sobe e desce simultaneamente)
    for delta in range(1, 12):
        if (pitch + delta) % 12 in classes:
            return pitch + delta
        if (pitch - delta) % 12 in classes:
            return pitch - delta

    return pitch  # nunca deve chegar aqui com escala de 7 notas


def filtrar_tokens_por_tonalidade(tokens: list[str], tonalidade: str) -> list[str]:
    """
    Percorre a lista de tokens e substitui NOTE_X cujo pitch não está na escala
    pelo pitch mais próximo dentro da escala.
    """
    resultado = []
    for tok in tokens:
        if tok.startswith("NOTE_"):
            pitch_original = int(tok.split("_")[1])
            pitch_corrigido = transpor_pitch(pitch_original, tonalidade)
            resultado.append(f"NOTE_{pitch_corrigido}")
        else:
            resultado.append(tok)
    return resultado


def pitch_para_nome(pitch: int) -> str:
    """Converte pitch MIDI (ex: 60) para nome musical (ex: 'Dó4')."""
    nome = NOMES_NOTAS[pitch % 12]
    oitava = (pitch // 12) - 1
    return f"{nome}{oitava}"
