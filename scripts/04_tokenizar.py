"""
Script 04 — Tokenizar melodias em um único JSONL e gerar o vocabulário.
"""

import argparse
import csv
import json

import pretty_midi
from tqdm import tqdm

from comum import aplicar_smoke, carregar_config, tokenizar_notas

TOKENS_ESPECIAIS = {"PAD": "<PAD>", "START": "<START>", "END": "<END>"}


def argumentos():
    parser = argparse.ArgumentParser(description="Tokenizar melodias extraídas")
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def carregar_meta(caminho_csv):
    meta = {}
    if not caminho_csv.exists():
        return meta
    with open(caminho_csv, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            meta[row["md5"]] = row
    return meta


def main():
    args = argumentos()
    cfg, raiz = carregar_config()
    cfg = aplicar_smoke(cfg, args.smoke)
    grades = cfg["normalizacao"]["grades_ritmicas"]
    pasta_melodias = raiz / cfg["saidas"]["pasta_melodias"]
    pasta_sequencias = raiz / cfg["saidas"]["pasta_sequencias"]
    pasta_relatorios = raiz / cfg["saidas"]["pasta_relatorios"]
    pasta_sequencias.mkdir(parents=True, exist_ok=True)

    meta = carregar_meta(pasta_relatorios / "melodias_selecionadas.csv")
    melodias = sorted(pasta_melodias.glob("*.mid")) + sorted(pasta_melodias.glob("*.midi"))
    print(f"Melodias encontradas: {len(melodias)}")

    caminho_jsonl = pasta_sequencias / "sequencias.jsonl"
    vocabulario = {}
    total_tokens = 0
    total_sequencias = 0

    with open(caminho_jsonl, "w", encoding="utf-8") as saida:
        for caminho_mid in tqdm(melodias, desc="Tokenizando"):
            md5 = caminho_mid.stem
            info = meta.get(md5, {})
            try:
                midi = pretty_midi.PrettyMIDI(str(caminho_mid))
            except Exception as exc:
                print(f"  ERRO ao abrir {caminho_mid.name}: {exc}")
                continue
            if not midi.instruments or not midi.instruments[0].notes:
                continue

            notas = midi.instruments[0].notes
            tempos = midi.get_tempo_changes()
            bpm = float(tempos[1][0]) if len(tempos[1]) > 0 else float(info.get("bpm") or 120)
            tokens = tokenizar_notas(notas, bpm, grades)
            if not tokens:
                continue

            for tok in tokens:
                if tok not in vocabulario:
                    vocabulario[tok] = len(vocabulario)

            registro = {
                "md5": md5,
                "nome_original": info.get("nome_original", ""),
                "bpm": round(bpm, 2),
                "num_notas": len(notas),
                "duracao_seg": round(float(midi.get_end_time()), 3),
                "tonalidade_origem": info.get("tonalidade_origem", ""),
                "modo": info.get("modo", ""),
                "semitons": int(info["semitons"]) if str(info.get("semitons", "")).lstrip("-").isdigit() else 0,
                "tokens": tokens,
            }
            saida.write(json.dumps(registro, ensure_ascii=False, separators=(",", ":")) + "\n")
            total_tokens += len(tokens)
            total_sequencias += 1

    for tok in TOKENS_ESPECIAIS.values():
        if tok not in vocabulario:
            vocabulario[tok] = len(vocabulario)

    vocab_dados = {
        "token_para_id": vocabulario,
        "id_para_token": {str(v): k for k, v in vocabulario.items()},
        "tamanho_vocabulario": len(vocabulario),
        "tokens_especiais": TOKENS_ESPECIAIS,
    }
    caminho_vocab = pasta_sequencias / "vocabulario.json"
    caminho_vocab.write_text(json.dumps(vocab_dados, ensure_ascii=False, indent=2), encoding="utf-8")

    media = total_tokens / total_sequencias if total_sequencias else 0
    print("\n===== Resultado da Tokenização =====")
    print(f"Sequências geradas     : {total_sequencias}")
    print(f"Tamanho médio (tokens) : {media:.1f}")
    print(f"Tamanho do vocabulário : {len(vocabulario)}")
    print(f"JSONL                  : {caminho_jsonl.relative_to(raiz)}")
    print(f"Vocabulário            : {caminho_vocab.relative_to(raiz)}")


if __name__ == "__main__":
    main()
