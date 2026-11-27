"""Verifica que toda combinação tonalidade x progressão toca acordes coerentes com a escala."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.teoria_musical import (ESCALAS, PROGRESSOES_GRAUS, gerar_progressao_acordes,
                                resolver_progressao)

problemas = 0
total = 0
for ton in ESCALAS:
    for est, graus in PROGRESSOES_GRAUS.items():
        total += 1
        acordes = gerar_progressao_acordes(ton, est, 20.0, 120)
        nomes = [a["nome"] for a in acordes[:len(graus)]]
        escala = set(ESCALAS[ton])
        # raiz de cada acorde deve pertencer à escala da tonalidade escolhida
        fora = [a["nome"] for a in acordes if (a["classes_pitch"][0]) not in escala]
        # progressão não pode colapsar numa única nota (bug antigo: Dó, Dó, Dó, Dó)
        colapsou = len(set(nomes)) < min(3, len(set(graus)))
        aviso = resolver_progressao(ton, est)[3]
        if fora or colapsou:
            problemas += 1
            print("PROBLEMA", ton, "|", est, "|", nomes, "fora:", fora)
        elif aviso:
            print("ok (relativa)", ton, "|", est.split(" (")[0], "->", nomes)

print(f"\n{total} combinações, {problemas} com problema")
sys.exit(1 if problemas else 0)
