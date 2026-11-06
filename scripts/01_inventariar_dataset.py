"""
Script 01 — Inventariar o dataset
Percorre os MIDIs e registra metadados. Retoma do CSV se a execução anterior parou.
"""

import argparse
import time
from pathlib import Path

from tqdm import tqdm

from comum import (
    analisar_midi,
    abrir_csv,
    carregar_config,
    carregar_md5_map,
    executar_pool,
    md5s_no_csv,
    primeiro_nome,
)

CAMPOS = [
    "caminho_relativo", "md5", "nome_original", "tamanho_bytes",
    "abre_sem_erro", "erro_leitura", "duracao_seg", "num_faixas",
    "num_instrumentos", "tem_bateria", "num_notas_total",
    "bpm_predominante", "num_mudancas_tempo", "faixas_info",
]


def argumentos():
    parser = argparse.ArgumentParser(description="Inventariar MIDIs do LMD-full")
    parser.add_argument("--limite", type=int, default=None, help="Processa só N arquivos novos")
    return parser.parse_args()


def main():
    args = argumentos()
    cfg, raiz = carregar_config()
    pasta_lmd = raiz / cfg["dataset"]["pasta_lmd_full"]
    arquivo_md5 = raiz / cfg["dataset"]["arquivo_md5_json"]
    extensoes = tuple(cfg["dataset"]["extensoes"])
    pasta_relatorios = raiz / cfg["saidas"]["pasta_relatorios"]
    pasta_relatorios.mkdir(parents=True, exist_ok=True)

    trabalhadores = int(cfg["execucao"]["trabalhadores"])
    retomada = bool(cfg["execucao"]["retomada"])
    lote = int(cfg["execucao"]["lote_gravacao"])
    piloto_ativo = bool(cfg["piloto"]["ativo"])
    piloto_qtd = int(cfg["piloto"]["quantidade"])

    print("Carregando mapa MD5...")
    md5_map = carregar_md5_map(arquivo_md5)
    print(f"md5_map carregado: {len(md5_map)} entradas")

    print(f"Listando MIDIs em {pasta_lmd}...")
    todos = sorted(
        p for p in pasta_lmd.rglob("*") if p.suffix.lower() in extensoes
    )
    if piloto_ativo:
        todos = todos[:piloto_qtd]
        print(f"[PILOTO] Universo limitado a {len(todos)} arquivos.")
    else:
        print(f"Arquivos encontrados: {len(todos)}")

    caminho_csv = pasta_relatorios / "inventario.csv"
    feitos = md5s_no_csv(caminho_csv) if retomada else set()
    pendentes = [p for p in todos if p.stem not in feitos]
    if args.limite is not None:
        pendentes = pendentes[: args.limite]

    print(f"Já inventariados: {len(feitos)}")
    print(f"Pendentes nesta execução: {len(pendentes)}")
    if not pendentes:
        print(f"Nada a fazer. Inventário em {caminho_csv.relative_to(raiz)}")
        return

    raiz_str = str(raiz)
    tarefas = ((str(p), raiz_str) for p in pendentes)
    arquivo, writer = abrir_csv(caminho_csv, CAMPOS, retomada=retomada and bool(feitos))

    inicio = time.perf_counter()
    gravados = 0
    try:
        for registro in tqdm(
            executar_pool(analisar_midi, tarefas, trabalhadores),
            total=len(pendentes),
            desc="Inventariando",
        ):
            registro["nome_original"] = primeiro_nome(md5_map, registro["md5"])
            writer.writerow(registro)
            gravados += 1
            if gravados % lote == 0:
                arquivo.flush()
            if gravados % 5000 == 0:
                decorrido = time.perf_counter() - inicio
                taxa = gravados / decorrido if decorrido else 0
                print(
                    f"\n{gravados} novos | {len(feitos) + gravados} no total | {taxa:.1f} arquivos/s",
                    flush=True,
                )
    finally:
        arquivo.flush()
        arquivo.close()

    elapsed = time.perf_counter() - inicio
    taxa = gravados / elapsed if elapsed else 0
    print(f"\nInventário atualizado: {caminho_csv.relative_to(raiz)}")
    print(f"Novos registros: {gravados} em {elapsed:.1f}s ({taxa:.1f} arquivos/s)")
    print(f"Total no CSV: {len(feitos) + gravados}")


if __name__ == "__main__":
    main()
