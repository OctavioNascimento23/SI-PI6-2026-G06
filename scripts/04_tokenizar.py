"""
Script 04 — Tokenizar
Converte cada melodia MIDI em uma sequência de tokens textuais.
"""

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


def carregar_md5_map(arquivo_md5):
    if arquivo_md5.exists():
        with open(arquivo_md5, encoding="utf-8") as f:
            return json.load(f)
    return {}


# ---------------------------------------------------------------------------
# Quantização de duração
# ---------------------------------------------------------------------------

def quantizar(duracao_beats, grades):
    """Retorna o valor da grade mais próximo de duracao_beats."""
    grades_arr = np.array(grades)
    idx = int(np.argmin(np.abs(grades_arr - duracao_beats)))
    return grades_arr[idx]


def formatar_grade(valor):
    """Formata o valor como string com 2 decimais."""
    return f"{valor:.2f}"


# ---------------------------------------------------------------------------
# Tokenização de uma melodia
# ---------------------------------------------------------------------------

def tokenizar_melodia(notas, bpm, grades):
    """
    Converte lista de pretty_midi.Note em tokens textuais.
    Retorna lista de strings: NOTE_<pitch>, DURATION_<grade>, REST_<grade>.
    """
    if not notas:
        return []

    beats_por_segundo = bpm / 60.0
    tokens = []

    notas_ord = sorted(notas, key=lambda n: n.start)

    for i, nota in enumerate(notas_ord):
        # Pausa antes desta nota?
        if i > 0:
            gap = nota.start - notas_ord[i - 1].end
            if gap > 0.01:  # pausa real (> 10 ms)
                gap_beats = gap * beats_por_segundo
                grade = quantizar(gap_beats, grades)
                tokens.append(f"REST_{formatar_grade(grade)}")

        # Nota
        duracao_seg = nota.end - nota.start
        duracao_beats = duracao_seg * beats_por_segundo
        grade = quantizar(duracao_beats, grades)

        tokens.append(f"NOTE_{nota.pitch}")
        tokens.append(f"DURATION_{formatar_grade(grade)}")

    return tokens


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cfg, raiz = carregar_config()
    grades = cfg["normalizacao"]["grades_ritmicas"]
    pasta_melodias = raiz / cfg["saidas"]["pasta_melodias"]
    pasta_sequencias = raiz / cfg["saidas"]["pasta_sequencias"]
    pasta_relatorios = raiz / cfg["saidas"]["pasta_relatorios"]
    arquivo_md5 = raiz / cfg["dataset"]["arquivo_md5_json"]

    pasta_sequencias.mkdir(parents=True, exist_ok=True)
    pasta_relatorios.mkdir(parents=True, exist_ok=True)

    md5_map = carregar_md5_map(arquivo_md5)

    melodias = sorted(pasta_melodias.glob("*.mid")) + sorted(pasta_melodias.glob("*.midi"))
    print(f"Melodias encontradas: {len(melodias)}")

    vocabulario: dict[str, int] = {}
    total_tokens = 0
    total_sequencias = 0

    for caminho_mid in tqdm(melodias, desc="Tokenizando"):
        md5 = caminho_mid.stem
        nome_original_lista = md5_map.get(md5, [])
        nome_original = (
            "; ".join(nome_original_lista)
            if isinstance(nome_original_lista, list)
            else str(nome_original_lista)
        )

        try:
            midi = pretty_midi.PrettyMIDI(str(caminho_mid))
        except Exception as e:
            print(f"  ERRO ao abrir {caminho_mid.name}: {e}")
            continue

        if not midi.instruments:
            continue

        instrumento = midi.instruments[0]
        notas = sorted(instrumento.notes, key=lambda n: n.start)

        tempos = midi.get_tempo_changes()
        bpm = float(tempos[1][0]) if len(tempos[1]) > 0 else 120.0

        tokens = tokenizar_melodia(notas, bpm, grades)
        if not tokens:
            continue

        # Atualizar vocabulário
        for tok in tokens:
            if tok not in vocabulario:
                vocabulario[tok] = len(vocabulario)

        total_tokens += len(tokens)
        total_sequencias += 1

        # Salvar sequência individual
        dados = {
            "md5": md5,
            "nome_original": nome_original,
            "bpm": round(bpm, 2),
            "num_notas": len(notas),
            "duracao_seg": round(midi.get_end_time(), 3),
            "tokens": tokens,
        }
        destino = pasta_sequencias / f"{md5}.json"
        with open(destino, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))

    # Tokens especiais
    tokens_especiais = {"PAD": "<PAD>", "START": "<START>", "END": "<END>"}
    for tok_especial in tokens_especiais.values():
        if tok_especial not in vocabulario:
            vocabulario[tok_especial] = len(vocabulario)

    token_para_id = vocabulario
    id_para_token = {str(v): k for k, v in vocabulario.items()}

    vocab_dados = {
        "token_para_id": token_para_id,
        "id_para_token": id_para_token,
        "tamanho_vocabulario": len(vocabulario),
        "tokens_especiais": tokens_especiais,
    }

    caminho_vocab = pasta_sequencias / "vocabulario.json"
    with open(caminho_vocab, "w", encoding="utf-8") as f:
        json.dump(vocab_dados, f, ensure_ascii=False, indent=2)

    media_tokens = total_tokens / total_sequencias if total_sequencias else 0
    print("\n===== Resultado da Tokenização =====")
    print(f"Sequências geradas         : {total_sequencias}")
    print(f"Tamanho médio (tokens)     : {media_tokens:.1f}")
    print(f"Tamanho do vocabulário     : {len(vocabulario)}")
    print(f"Vocabulário salvo em       : {caminho_vocab.relative_to(raiz)}")


if __name__ == "__main__":
    main()
