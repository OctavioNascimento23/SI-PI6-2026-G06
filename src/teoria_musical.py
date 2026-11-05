"""
teoria_musical.py
Módulo de Teoria Musical, Harmonias, Escalas e Progressões de Acordes.
"""

from typing import List, Dict, Tuple

# Notas base por tonalidade (índices cromáticos 0–11)
ESCALAS: Dict[str, List[int]] = {
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

# Mapeamento de Tônica para cada Tonalidade (índice 0-11)
TONICAS: Dict[str, int] = {
    "Dó Maior": 0, "Ré Maior": 2, "Mi Maior": 4, "Fá Maior": 5,
    "Sol Maior": 7, "Lá Maior": 9, "Si Maior": 11,
    "Lá Menor": 9, "Mi Menor": 4, "Ré Menor": 2,
    "Sol Menor": 7, "Dó Menor": 0,
}

# Tipos de escalas (Maior vs Menor natural)
TIPO_ESCALA: Dict[str, str] = {
    "Dó Maior": "maior", "Ré Maior": "maior", "Mi Maior": "maior", "Fá Maior": "maior",
    "Sol Maior": "maior", "Lá Maior": "maior", "Si Maior": "maior",
    "Lá Menor": "menor", "Mi Menor": "menor", "Ré Menor": "menor",
    "Sol Menor": "menor", "Dó Menor": "menor",
}

# Progressões de Acordes populares (por graus harmônicos)
PROGRESSOES_GRAUS = {
    "Pop / Hits (I - V - vi - IV)": ["I", "V", "vi", "IV"],
    "Balada Emocionante (I - vi - IV - V)": ["I", "vi", "IV", "V"],
    "Cânone / Rápida (I - V - vi - iii - IV - I - IV - V)": ["I", "V", "vi", "iii", "IV", "I", "IV", "V"],
    "Cadência Suave (ii - V - I - vi)": ["ii", "V", "I", "vi"],
    "Rock Enérgico (I - IV - V - IV)": ["I", "IV", "V", "IV"],
    "Sentimental Menor (i - VI - III - VII)": ["i", "VI", "III", "VII"],
    "Blues / Melancolia (i - iv - v - i)": ["i", "iv", "v", "i"],
}

# Mapeamento de Graus para intervalos e qualidade (Maior)
MAPA_GRAUS_MAIOR = {
    "I":   {"offset": 0, "qualidade": "maj", "nome_rel": "I (Tônica)"},
    "ii":  {"offset": 2, "qualidade": "min", "nome_rel": "ii (Super tônica)"},
    "iii": {"offset": 4, "qualidade": "min", "nome_rel": "iii (Mediante)"},
    "IV":  {"offset": 5, "qualidade": "maj", "nome_rel": "IV (Subdominante)"},
    "V":   {"offset": 7, "qualidade": "maj", "nome_rel": "V (Dominante)"},
    "vi":  {"offset": 9, "qualidade": "min", "nome_rel": "vi (Relativa menor)"},
    "vii°":{"offset": 11, "qualidade": "dim", "nome_rel": "vii° (Sensível)"},
}

# Mapeamento de Graus para intervalos e qualidade (Menor natural)
MAPA_GRAUS_MENOR = {
    "i":   {"offset": 0, "qualidade": "min", "nome_rel": "i (Tônica menor)"},
    "ii°": {"offset": 2, "qualidade": "dim", "nome_rel": "ii° (Diminuto)"},
    "III": {"offset": 3, "qualidade": "maj", "nome_rel": "III (Relativa maior)"},
    "iv":  {"offset": 5, "qualidade": "min", "nome_rel": "iv (Subdominante)"},
    "v":   {"offset": 7, "qualidade": "min", "nome_rel": "v (Dominante menor)"},
    "V":   {"offset": 7, "qualidade": "maj", "nome_rel": "V (Dominante maior)"},
    "VI":  {"offset": 8, "qualidade": "maj", "nome_rel": "VI (Submediante)"},
    "VII": {"offset": 10, "qualidade": "maj", "nome_rel": "VII (Subtônica)"},
}


def obter_notas_acorde(tonica_pitch: int, qualidade: str, oitava: int = 4) -> List[int]:
    """
    Retorna os pitches MIDI (tríade) de um acorde em uma oitava específica (padrão C4 = 60).
    """
    raiz = (oitava + 1) * 12 + (tonica_pitch % 12)
    if qualidade == "maj":
        return [raiz, raiz + 4, raiz + 7]  # Fundamental, 3ª maior, 5ª justa
    elif qualidade == "min":
        return [raiz, raiz + 3, raiz + 7]  # Fundamental, 3ª menor, 5ª justa
    elif qualidade == "dim":
        return [raiz, raiz + 3, raiz + 6]  # Fundamental, 3ª menor, 5ª diminuta
    return [raiz, raiz + 4, raiz + 7]


def gerar_progressao_acordes(tonalidade: str, estilo_progressao: str, duracao_seg: float, bpm: int) -> List[Dict]:
    """
    Gera a progressão de acordes estruturada compasso a compasso com tempos de início, fim e notas.
    Cada compasso = 4 beats (fórmula 4/4).
    """
    seg_por_beat = 60.0 / bpm
    seg_por_compasso = seg_por_beat * 4.0
    num_compassos = max(1, int(duracao_seg / seg_por_compasso) + 1)

    tipo = TIPO_ESCALA.get(tonalidade, "maior")
    tonica_base = TONICAS.get(tonalidade, 0)
    mapa = MAPA_GRAUS_MAIOR if tipo == "maior" else MAPA_GRAUS_MENOR

    # Escolhe a progressão padrão se o estilo não for compatível com o tipo de escala
    lista_graus = PROGRESSOES_GRAUS.get(estilo_progressao)
    if not lista_graus:
        lista_graus = ["I", "V", "vi", "IV"] if tipo == "maior" else ["i", "VI", "III", "VII"]

    acordes_gerados = []
    tempo_cursor = 0.0

    for compasso_idx in range(num_compassos):
        grau = lista_graus[compasso_idx % len(lista_graus)]
        info_grau = mapa.get(grau)
        
        # Fallback de grau se houver divergência entre maior/menor
        if not info_grau:
            info_grau = {"offset": 0, "qualidade": "maj" if tipo == "maior" else "min"}

        nota_raiz_idx = (tonica_base + info_grau["offset"]) % 12
        nome_raiz = NOMES_NOTAS[nota_raiz_idx]
        sufixo = "" if info_grau["qualidade"] == "maj" else ("m" if info_grau["qualidade"] == "min" else "°")
        nome_acorde = f"{nome_raiz}{sufixo}"

        duracao_acorde = min(seg_por_compasso, max(0.0, duracao_seg - tempo_cursor))
        if duracao_acorde <= 0:
            break

        notas_midi = obter_notas_acorde(nota_raiz_idx, info_grau["qualidade"], oitava=3)

        acordes_gerados.append({
            "compasso": compasso_idx + 1,
            "grau": grau,
            "nome": nome_acorde,
            "inicio_seg": tempo_cursor,
            "fim_seg": tempo_cursor + duracao_acorde,
            "duracao_seg": duracao_acorde,
            "notas_midi": notas_midi,
            "classes_pitch": [(p % 12) for p in notas_midi],
        })

        tempo_cursor += duracao_acorde
        if tempo_cursor >= duracao_seg:
            break

    return acordes_gerados


def pitches_da_tonalidade(nome_tonalidade: str, pitch_min: int = 36, pitch_max: int = 96) -> List[int]:
    """Retorna todos os pitches MIDI válidos para a tonalidade no intervalo dado."""
    classes = set(ESCALAS.get(nome_tonalidade, ESCALAS["Dó Maior"]))
    return [p for p in range(pitch_min, pitch_max + 1) if p % 12 in classes]


def transpor_pitch(pitch: int, tonalidade: str) -> int:
    """Ajusta o pitch para a nota mais próxima pertencente à escala da tonalidade."""
    classes = set(ESCALAS.get(tonalidade, ESCALAS["Dó Maior"]))
    if pitch % 12 in classes:
        return pitch
    for delta in range(1, 12):
        if (pitch + delta) % 12 in classes:
            return pitch + delta
        if (pitch - delta) % 12 in classes:
            return pitch - delta
    return pitch


def filtrar_tokens_por_tonalidade(tokens: List[str], tonalidade: str) -> List[str]:
    """Garante que todos os tokens NOTE_X pertençam à escala musical selecionada."""
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
    """Converte pitch MIDI (ex: 60) para formato legível (ex: 'Dó4')."""
    nome = NOMES_NOTAS[pitch % 12]
    oitava = (pitch // 12) - 1
    return f"{nome}{oitava}"
