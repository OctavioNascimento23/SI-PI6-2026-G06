"""
medir_tempo.py
Mede o alinhamento rítmico da melodia gerada com a grade dos acordes (compasso 4/4), por trecho da peça.

Para cada nota (início exato em beats, 0,125 tratado corretamente):
  - no beat           = início % 1 == 0
  - início de compasso = início % 4 == 0
  - fora de 1/4       = início % 0.25 != 0  (colcheia ímpar de 1/8)
O resultado é separado em 4 trechos consecutivos da peça, para ver se o alinhamento se perde com o tempo.

Uso:
    python scripts/medir_tempo.py --modelo transformer --n 20
"""
import argparse
import json
import sys
from pathlib import Path

import torch

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.gerador import GeradorMusical


def beats(valor: str) -> float:
    v = float(valor)
    return 0.125 if v == 0.12 else v


def inicios(tokens):
    """Lista de (início_em_beats, duração_em_beats) de cada nota e o total em beats."""
    t, pend, out = 0.0, False, []
    for tok in tokens:
        if tok.startswith("NOTE_"):
            pend = True
        elif tok.startswith("DURATION_"):
            d = beats(tok.split("_")[1])
            if pend:
                out.append((t, d))
            t += d
            pend = False
        elif tok.startswith("REST_"):
            t += beats(tok.split("_")[1])
            pend = False
    return out, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", choices=["transformer", "lstm"], default="transformer")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--bpm", type=int, default=120)
    ap.add_argument("--duracao", type=float, default=30.0)
    ap.add_argument("--tonalidade", default="Dó Maior")
    ap.add_argument("--temperatura", type=float, default=0.85)
    ap.add_argument("--rotulo", default="")
    args = ap.parse_args()

    g = GeradorMusical()
    motor = "Transformer (Deep Learning)" if args.modelo == "transformer" else "LSTM (Rede Neural)"

    trechos = [[] for _ in range(4)]
    cobertura = []
    total_beats = args.duracao * args.bpm / 60.0
    for semente in range(args.n):
        torch.manual_seed(semente)
        r = g.compor(tonalidade=args.tonalidade, bpm=args.bpm, duracao_seg=args.duracao, tipo_modelo=motor,
                     temperatura=args.temperatura, caminho_saida_midi=str(RAIZ / "saida_temp" / "_medir.mid"))
        notas, fim = inicios(r["tokens"])
        cobertura.append(fim / total_beats)
        for ini, _ in notas:
            trechos[min(3, int(ini / total_beats * 4))].append(ini)

    def pct(lista, f):
        return round(100 * sum(1 for x in lista if f(x)) / len(lista), 1) if lista else None

    resumo = {"modelo": args.modelo, "rotulo": args.rotulo, "n": args.n,
              "cobertura_media_da_duracao": round(sum(cobertura) / len(cobertura), 3), "trechos": {}}
    todos = [x for t in trechos for x in t]
    for nome, lista in [("1o quarto", trechos[0]), ("2o quarto", trechos[1]), ("3o quarto", trechos[2]),
                        ("4o quarto", trechos[3]), ("TOTAL", todos)]:
        resumo["trechos"][nome] = {
            "notas": len(lista),
            "no_beat_%": pct(lista, lambda x: abs(x % 1) < 1e-6),
            "inicio_compasso_%": pct(lista, lambda x: abs(x % 4) < 1e-6),
            "fora_de_1/4_%": pct(lista, lambda x: abs(x % 0.25) > 1e-6),
        }
    print(json.dumps(resumo, indent=2, ensure_ascii=False))
    sufixo = f"_{args.rotulo}" if args.rotulo else ""
    (RAIZ / "relatorios" / f"medida_tempo_{args.modelo}{sufixo}.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
