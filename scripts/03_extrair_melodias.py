"""
Script 03 — Extrair melodias
Para cada MIDI válido, identifica e extrai a faixa mais adequada como melodia monofônica.
"""

import csv
import json
from pathlib import Path

import numpy as np
import pretty_midi
import yaml
from tqdm import tqdm


def carregar_config():
    raiz = Path(__file__).resolve().parent.parent
    with open(raiz / "configuracao" / "pipeline.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f), raiz


# ---------------------------------------------------------------------------
# Passo 3.1 — Selecionar a faixa melódica
# ---------------------------------------------------------------------------

def calcular_pontuacao(instrumento, filtros):
    """Calcula a pontuação de um instrumento (faixa) para seleção melódica."""
    notas = instrumento.notes
    if not notas:
        return -1.0, {}

    num_notas = len(notas)
    pitches = [n.pitch for n in notas]
    pitch_medio = np.mean(pitches)
    variacao_pitch = np.std(pitches)

    # Polifonia: percentual de notas que se sobrepõem (início < fim da anterior)
    notas_ord = sorted(notas, key=lambda n: n.start)
    sobrepostos = 0
    for i in range(1, len(notas_ord)):
        if notas_ord[i].start < notas_ord[i - 1].end - 0.001:
            sobrepostos += 1
    pct_polifonia = sobrepostos / num_notas if num_notas else 0

    # Pausas: tempo total sem notas / duração total
    duracao_total = notas_ord[-1].end - notas_ord[0].start
    tempo_com_nota = sum(n.end - n.start for n in notas_ord)
    pct_pausas = max(0.0, 1.0 - (tempo_com_nota / duracao_total)) if duracao_total > 0 else 1.0

    # Normalização simples 0-1 (baseada em limites razoáveis)
    norm_notas = min(num_notas / 500.0, 1.0)
    norm_registro = min(max((pitch_medio - 36) / 60.0, 0.0), 1.0)   # C2–C7
    norm_var = min(variacao_pitch / 12.0, 1.0)                        # até 1 oitava de desvio

    peso_notas = 0.3
    peso_registro = 0.2
    peso_var = 0.3
    peso_poli = 0.1
    peso_pausa = 0.1

    pontuacao = (
        peso_notas * norm_notas
        + peso_registro * norm_registro
        + peso_var * norm_var
        - peso_poli * pct_polifonia
        - peso_pausa * pct_pausas
    )

    detalhes = {
        "num_notas": num_notas,
        "pitch_medio": round(pitch_medio, 2),
        "variacao_pitch": round(variacao_pitch, 2),
        "pct_polifonia": round(pct_polifonia, 4),
        "pct_pausas": round(pct_pausas, 4),
        "pontuacao": round(pontuacao, 6),
    }
    return pontuacao, detalhes


def selecionar_faixa(midi, filtros):
    """Retorna (instrumento, índice, detalhes) da melhor faixa, ou (None, -1, {})."""
    melhor_score = -999.0
    melhor_inst = None
    melhor_idx = -1
    melhor_det = {}

    duracao_total = midi.get_end_time()

    for idx, instrumento in enumerate(midi.instruments):
        if instrumento.is_drum:
            continue
        num_notas = len(instrumento.notes)
        if num_notas < filtros["notas_minimas"]:
            continue
        if duracao_total < filtros["duracao_minima_seg"]:
            continue

        score, det = calcular_pontuacao(instrumento, filtros)
        if score > melhor_score:
            melhor_score = score
            melhor_inst = instrumento
            melhor_idx = idx
            melhor_det = det

    return melhor_inst, melhor_idx, melhor_det


# ---------------------------------------------------------------------------
# Passo 3.2 — Converter para monofonia
# ---------------------------------------------------------------------------

THRESHOLD_SIMULTANEO = 0.05  # 50 ms


def converter_monofonia(notas, regra):
    """Remove polifonia, mantendo apenas uma nota por janela simultânea."""
    if not notas:
        return []

    notas_ord = sorted(notas, key=lambda n: n.start)
    resultado = []
    grupo = [notas_ord[0]]

    for nota in notas_ord[1:]:
        # É simultânea com a última do grupo?
        if nota.start - grupo[-1].start < THRESHOLD_SIMULTANEO:
            grupo.append(nota)
        else:
            # Resolver o grupo
            if regra == "pitch_mais_agudo":
                escolhida = max(grupo, key=lambda n: n.pitch)
            else:  # maior_duracao
                escolhida = max(grupo, key=lambda n: n.end - n.start)
            resultado.append(escolhida)
            grupo = [nota]

    # Último grupo
    if grupo:
        if regra == "pitch_mais_agudo":
            escolhida = max(grupo, key=lambda n: n.pitch)
        else:
            escolhida = max(grupo, key=lambda n: n.end - n.start)
        resultado.append(escolhida)

    return resultado


# ---------------------------------------------------------------------------
# Passo 3.3 — Filtros finais
# ---------------------------------------------------------------------------

def aplicar_filtros_finais(notas, filtros):
    """
    Aplica filtros de qualidade. Retorna (notas_filtradas, motivo_descarte | None).
    """
    if not notas:
        return [], "SEM_NOTAS_APOS_MONOFONIA"

    # Notas fora do range de pitch
    pitch_min = filtros["pitch_minimo"]
    pitch_max = filtros["pitch_maximo"]
    fora_range = [n for n in notas if not (pitch_min <= n.pitch <= pitch_max)]
    pct_fora = len(fora_range) / len(notas)

    if pct_fora > 0.05:
        # Descartar apenas as notas fora do intervalo
        notas = [n for n in notas if pitch_min <= n.pitch <= pitch_max]

    if len(notas) < filtros["notas_minimas"]:
        return [], f"NOTAS_INSUFICIENTES_APOS_FILTRO ({len(notas)})"

    if len(notas) > filtros["notas_maximas"]:
        return [], f"NOTAS_EXCESSIVAS ({len(notas)})"

    # Melodia praticamente plana: >80% das notas em apenas 1 ou 2 pitches distintos
    pitches_distintos = {}
    for n in notas:
        pitches_distintos[n.pitch] = pitches_distintos.get(n.pitch, 0) + 1

    top2 = sum(sorted(pitches_distintos.values(), reverse=True)[:2])
    if top2 / len(notas) > 0.80:
        return [], "MELODIA_PLANA"

    return notas, None


# ---------------------------------------------------------------------------
# Salvar melodia como novo arquivo MIDI
# ---------------------------------------------------------------------------

def salvar_melodia(notas, bpm, destino):
    """Cria um novo PrettyMIDI com apenas as notas fornecidas e salva."""
    midi_out = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst = pretty_midi.Instrument(program=0, name="Melodia")
    inst.notes = list(notas)
    midi_out.instruments.append(inst)
    midi_out.write(str(destino))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cfg, raiz = carregar_config()
    filtros = cfg["filtros"]
    regra_monofonia = cfg["normalizacao"]["regra_monofonia"]
    pasta_validos = raiz / cfg["saidas"]["pasta_midi_validos"]
    pasta_melodias = raiz / cfg["saidas"]["pasta_melodias"]
    pasta_relatorios = raiz / cfg["saidas"]["pasta_relatorios"]
    pasta_melodias.mkdir(parents=True, exist_ok=True)
    pasta_relatorios.mkdir(parents=True, exist_ok=True)

    # Carregar md5_to_paths para nome_original
    arquivo_md5 = raiz / cfg["dataset"]["arquivo_md5_json"]
    md5_map: dict = {}
    if arquivo_md5.exists():
        with open(arquivo_md5, encoding="utf-8") as f:
            md5_map = json.load(f)

    midis_validos = sorted(pasta_validos.glob("*.mid")) + sorted(pasta_validos.glob("*.midi"))
    print(f"MIDIs válidos encontrados: {len(midis_validos)}")

    campos_faixas = [
        "md5", "indice_faixa", "nome_faixa", "programa", "is_drum",
        "num_notas", "duracao_seg", "pitch_medio", "variacao_pitch",
        "pct_polifonia", "pct_pausas", "pontuacao", "selecionada", "motivo_descarte",
    ]
    campos_melodias = [
        "md5", "nome_original", "indice_faixa", "instrumento",
        "num_notas", "duracao_seg", "pitch_min", "pitch_max",
        "pitch_medio", "bpm", "pontuacao_selecao",
    ]

    caminho_faixas = pasta_relatorios / "faixas_analisadas.csv"
    caminho_melodias = pasta_relatorios / "melodias_selecionadas.csv"

    total_sem_faixa = 0
    total_descartados_filtro = 0
    total_melodias = 0

    with open(caminho_faixas, "w", newline="", encoding="utf-8") as ff, \
         open(caminho_melodias, "w", newline="", encoding="utf-8") as fm:

        writer_faixas = csv.DictWriter(ff, fieldnames=campos_faixas)
        writer_melodias = csv.DictWriter(fm, fieldnames=campos_melodias)
        writer_faixas.writeheader()
        writer_melodias.writeheader()

        for caminho_midi in tqdm(midis_validos, desc="Extraindo melodias"):
            md5 = caminho_midi.stem
            nome_original_lista = md5_map.get(md5, [])
            nome_original = (
                "; ".join(nome_original_lista)
                if isinstance(nome_original_lista, list)
                else str(nome_original_lista)
            )

            try:
                midi = pretty_midi.PrettyMIDI(str(caminho_midi))
            except Exception as e:
                total_sem_faixa += 1
                continue

            duracao_total = midi.get_end_time()
            tempos = midi.get_tempo_changes()
            bpm = float(tempos[1][0]) if len(tempos[1]) > 0 else 120.0

            # Registrar todas as faixas
            for idx, instrumento in enumerate(midi.instruments):
                score, det = calcular_pontuacao(instrumento, filtros)
                writer_faixas.writerow({
                    "md5": md5,
                    "indice_faixa": idx,
                    "nome_faixa": instrumento.name,
                    "programa": instrumento.program,
                    "is_drum": instrumento.is_drum,
                    "num_notas": len(instrumento.notes),
                    "duracao_seg": round(duracao_total, 3),
                    "pitch_medio": det.get("pitch_medio", ""),
                    "variacao_pitch": det.get("variacao_pitch", ""),
                    "pct_polifonia": det.get("pct_polifonia", ""),
                    "pct_pausas": det.get("pct_pausas", ""),
                    "pontuacao": det.get("pontuacao", ""),
                    "selecionada": False,
                    "motivo_descarte": "",
                })

            # Selecionar melhor faixa
            melhor_inst, melhor_idx, melhor_det = selecionar_faixa(midi, filtros)
            if melhor_inst is None:
                total_sem_faixa += 1
                continue

            # Monofonia
            notas_mono = converter_monofonia(melhor_inst.notes, regra_monofonia)

            # Filtros finais
            notas_finais, motivo = aplicar_filtros_finais(notas_mono, filtros)
            if motivo:
                total_descartados_filtro += 1
                continue

            # Salvar melodia
            destino = pasta_melodias / f"{md5}.mid"
            salvar_melodia(notas_finais, bpm, destino)

            pitches = [n.pitch for n in notas_finais]
            writer_melodias.writerow({
                "md5": md5,
                "nome_original": nome_original,
                "indice_faixa": melhor_idx,
                "instrumento": melhor_inst.name,
                "num_notas": len(notas_finais),
                "duracao_seg": round(duracao_total, 3),
                "pitch_min": min(pitches),
                "pitch_max": max(pitches),
                "pitch_medio": round(np.mean(pitches), 2),
                "bpm": round(bpm, 2),
                "pontuacao_selecao": melhor_det.get("pontuacao", ""),
            })
            total_melodias += 1

    print("\n===== Resultado da Extração =====")
    print(f"MIDIs sem faixa válida     : {total_sem_faixa}")
    print(f"Descartados por filtro     : {total_descartados_filtro}")
    print(f"Melodias extraídas         : {total_melodias}")
    print(f"\nRelatório de faixas : {caminho_faixas.relative_to(raiz)}")
    print(f"Melodias selecionadas: {caminho_melodias.relative_to(raiz)}")


if __name__ == "__main__":
    main()
