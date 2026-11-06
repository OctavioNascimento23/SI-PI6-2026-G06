"""
Script 03 — Extrair melodias monofônicas do recorte.
Transpõe para Dó maior ou Lá menor e grava um MIDI enxuto por melodia.
"""

import argparse
import csv
from collections import Counter

from tqdm import tqdm

from comum import (
    abrir_csv,
    aplicar_smoke,
    carregar_config,
    executar_pool,
    init_melodia,
    md5s_no_csv,
    processar_melodia,
)

CAMPOS_FAIXAS = [
    "md5", "indice_faixa", "nome_faixa", "programa", "is_drum",
    "num_notas", "duracao_seg", "pitch_medio", "variacao_pitch",
    "pct_polifonia", "pct_pausas", "pontuacao", "selecionada", "motivo_descarte",
]
CAMPOS_MELODIAS = [
    "md5", "nome_original", "indice_faixa", "instrumento",
    "num_notas", "duracao_seg", "pitch_min", "pitch_max",
    "pitch_medio", "bpm", "pontuacao_selecao",
    "tonalidade_origem", "modo", "semitons",
]
CAMPOS_ESTADO = ["md5", "status", "motivo"]


def argumentos():
    parser = argparse.ArgumentParser(description="Extrair melodias do recorte")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--limite", type=int, default=None)
    return parser.parse_args()


def main():
    args = argumentos()
    cfg, raiz = carregar_config()
    cfg = aplicar_smoke(cfg, args.smoke)
    filtros = cfg["filtros"]
    pasta_melodias = raiz / cfg["saidas"]["pasta_melodias"]
    pasta_relatorios = raiz / cfg["saidas"]["pasta_relatorios"]
    pasta_melodias.mkdir(parents=True, exist_ok=True)
    pasta_relatorios.mkdir(parents=True, exist_ok=True)

    caminho_recorte = pasta_relatorios / "recorte.csv"
    if not caminho_recorte.exists():
        raise FileNotFoundError(
            f"{caminho_recorte} não encontrado. Execute o script 02 antes."
        )

    retomada = bool(cfg["execucao"]["retomada"])
    trabalhadores = int(cfg["execucao"]["trabalhadores"])
    lote = int(cfg["execucao"]["lote_gravacao"])

    caminho_estado = pasta_relatorios / "extracao_vistos.csv"
    caminho_faixas = pasta_relatorios / "faixas_analisadas.csv"
    caminho_melodias = pasta_relatorios / "melodias_selecionadas.csv"
    vistos = md5s_no_csv(caminho_estado) if retomada else set()

    tarefas = []
    with open(caminho_recorte, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["md5"] in vistos:
                continue
            tarefas.append({
                "md5": row["md5"],
                "caminho": str(raiz / row["caminho_relativo"]),
                "nome_original": row.get("nome_original", ""),
            })
            if args.limite is not None and len(tarefas) >= args.limite:
                break

    print(f"Já extraídos: {len(vistos)}")
    print(f"Pendentes: {len(tarefas)}")
    if not tarefas:
        print("Nada a fazer.")
        return

    ctx = {
        "filtros": filtros,
        "regra_monofonia": cfg["normalizacao"]["regra_monofonia"],
        "transpor": bool(cfg["normalizacao"].get("transpor_para_tonica", True)),
        "pasta_melodias": str(pasta_melodias),
    }

    arquivo_faixas, writer_faixas = abrir_csv(
        caminho_faixas, CAMPOS_FAIXAS, retomada=retomada and bool(vistos)
    )
    arquivo_mel, writer_mel = abrir_csv(
        caminho_melodias, CAMPOS_MELODIAS, retomada=retomada and bool(vistos)
    )
    arquivo_estado, writer_estado = abrir_csv(
        caminho_estado, CAMPOS_ESTADO, retomada=retomada and bool(vistos)
    )

    contagem = Counter()
    gravados = 0
    try:
        for resultado in tqdm(
            executar_pool(
                processar_melodia,
                tarefas,
                trabalhadores,
                inicializador=init_melodia,
                initargs=(ctx,),
            ),
            total=len(tarefas),
            desc="Extraindo melodias",
        ):
            for faixa in resultado["faixas"]:
                writer_faixas.writerow(faixa)
            if resultado["melodia"]:
                writer_mel.writerow(resultado["melodia"])
            writer_estado.writerow({
                "md5": resultado["md5"],
                "status": resultado["status"],
                "motivo": resultado["motivo"],
            })
            contagem[resultado["status"]] += 1
            gravados += 1
            if gravados % lote == 0:
                arquivo_faixas.flush()
                arquivo_mel.flush()
                arquivo_estado.flush()
    finally:
        for arquivo in (arquivo_faixas, arquivo_mel, arquivo_estado):
            arquivo.flush()
            arquivo.close()

    print("\n===== Resultado da Extração =====")
    print(f"Melodias extraídas     : {contagem['ok']}")
    print(f"Sem faixa válida       : {contagem['sem_faixa']}")
    print(f"Descartadas por filtro : {contagem['filtro']}")
    print(f"Erros de leitura       : {contagem['erro']}")
    print(f"Melodias em            : {pasta_melodias.relative_to(raiz)}")


if __name__ == "__main__":
    main()
