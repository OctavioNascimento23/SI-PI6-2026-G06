"""
avaliar_geracao.py
Mede, em N composições, a aderência da melodia à harmonia e a diversidade melódica,
comparando: vocabulário antigo (bug) x vocabulário do checkpoint, com e sem guia harmônico.

Uso:
    python scripts/avaliar_geracao.py --modelo transformer --n 30
"""

import argparse
import json
import sys
from pathlib import Path

import torch

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.gerador import GeradorMusical
from src.harmonia_guia import criar_guia_harmonico, metricas_melodia
from src.midi_builder import limitar_duracao
from src.teoria_musical import PROGRESSOES_GRAUS, filtrar_tokens_por_tonalidade, gerar_progressao_acordes

CHAVES = [
    "frac_notas_no_acorde",
    "frac_forte_no_acorde",
    "frac_notas_na_escala",
    "alturas_distintas",
    "amplitude_semitons",
    "pct_repeticoes_consecutivas",
    "n_notas",
]


def rodar(g, modelo, vocab, guiar, n, bpm, duracao, tonalidade, estilo, temperatura, pos_filtro=True):
    t2i, i2t = vocab["token_para_id"], vocab["id_para_token"]
    acordes = gerar_progressao_acordes(tonalidade, estilo, duracao, bpm)
    acc = {k: 0.0 for k in CHAVES}
    for semente in range(n):
        torch.manual_seed(semente)
        guia = criar_guia_harmonico(t2i, acordes, tonalidade) if guiar else None
        toks = modelo.gerar(t2i, i2t, num_tokens=int(duracao * 4) + 8, temperatura=temperatura, ajustar_logits=guia)
        if pos_filtro:  # igual ao que o app faz
            toks = filtrar_tokens_por_tonalidade(toks, tonalidade)
        toks = limitar_duracao(toks, bpm, duracao)
        m = metricas_melodia(toks, acordes, bpm, tonalidade)
        for k in CHAVES:
            acc[k] += m[k] / n
    return {k: round(v, 3) for k, v in acc.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", choices=["transformer", "lstm"], default="transformer")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--bpm", type=int, default=120)
    ap.add_argument("--duracao", type=float, default=20.0)
    ap.add_argument("--tonalidade", default="Dó Maior")
    ap.add_argument("--estilo", default=list(PROGRESSOES_GRAUS)[0])
    ap.add_argument("--temperatura", type=float, default=0.85)
    args = ap.parse_args()

    g = GeradorMusical()
    modelo = g.carregar_transformer() if args.modelo == "transformer" else g.carregar_lstm()
    vocab_ckpt = modelo.vocabulario
    vocab_app_antigo = {"token_para_id": g.token_para_id, "id_para_token": g.id_para_token}

    cenarios = {
        "A) vocab antigo (74), sem guia  [estado original do app]": (vocab_app_antigo, False),
        "B) vocab do checkpoint (140), sem guia": (vocab_ckpt, False),
        "C) vocab do checkpoint (140), com guia harmonico": (vocab_ckpt, True),
    }
    resultados = {}
    for nome, (vocab, guiar) in cenarios.items():
        resultados[nome] = rodar(
            g, modelo, vocab, guiar, args.n, args.bpm, args.duracao, args.tonalidade, args.estilo, args.temperatura
        )
        print(nome)
        for k, v in resultados[nome].items():
            print(f"   {k:30s} {v}")

    saida = RAIZ / "relatorios" / f"avaliacao_geracao_{args.modelo}.json"
    saida.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSalvo em {saida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
