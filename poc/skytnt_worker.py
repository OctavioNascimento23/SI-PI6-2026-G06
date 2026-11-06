"""Processo separado que carrega o SkyTNT na GPU e devolve um MIDI por pedido."""

import json
import sys
import warnings
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
warnings.filterwarnings("ignore")

SAIDA = sys.stdout
sys.stdout = sys.stderr

from poc.skytnt_gerar import carregar, gerar_midi, resumir


def main():
    carregar()
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        pedido = json.loads(linha)
        try:
            gerar_midi(
                pedido["tonalidade"],
                int(pedido["bpm"]),
                float(pedido["duracao"]),
                float(pedido["temperatura"]),
                pedido["caminho"],
                pedido.get("max_eventos"),
            )
            resposta = {"ok": True, "resumo": resumir(pedido["caminho"])}
        except Exception as exc:
            resposta = {"ok": False, "erro": str(exc)}
        SAIDA.write(json.dumps(resposta, ensure_ascii=False) + "\n")
        SAIDA.flush()


if __name__ == "__main__":
    main()
