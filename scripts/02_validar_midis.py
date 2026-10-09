"""
Script 02 — Validar e filtrar MIDIs
Lê o inventario.csv, aplica critérios de rejeição e copia os MIDIs aprovados.
"""

import csv
import shutil
from pathlib import Path
from collections import Counter

import yaml
from tqdm import tqdm


def carregar_config():
    raiz = Path(__file__).resolve().parent.parent
    with open(raiz / "configuracao" / "pipeline.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f), raiz


def motivo_rejeicao(registro, filtros):
    """Retorna (motivo, detalhe) se o registro deve ser rejeitado, ou (None, None)."""
    abre = registro["abre_sem_erro"].strip().lower()
    if abre not in ("true", "1"):
        return "CORROMPIDO", registro.get("erro_leitura", "")

    try:
        num_notas = int(registro["num_notas_total"])
    except (ValueError, KeyError):
        num_notas = 0

    try:
        duracao = float(registro["duracao_seg"])
    except (ValueError, KeyError):
        duracao = 0.0

    try:
        tamanho = int(registro["tamanho_bytes"])
    except (ValueError, KeyError):
        tamanho = 0

    if num_notas == 0:
        return "SEM_NOTAS", f"num_notas={num_notas}"
    if duracao < filtros["duracao_minima_seg"]:
        return "MUITO_CURTO", f"duracao={duracao:.2f}s < {filtros['duracao_minima_seg']}s"
    if duracao > filtros["duracao_maxima_seg"]:
        return "MUITO_LONGO", f"duracao={duracao:.2f}s > {filtros['duracao_maxima_seg']}s"
    if tamanho < 200:
        return "ARQUIVO_MINIMO", f"tamanho={tamanho} bytes"

    return None, None


def main():
    cfg, raiz = carregar_config()
    filtros = cfg["filtros"]
    pasta_lmd = raiz / cfg["dataset"]["pasta_lmd_full"]
    pasta_validos = raiz / cfg["saidas"]["pasta_midi_validos"]
    pasta_relatorios = raiz / cfg["saidas"]["pasta_relatorios"]
    pasta_validos.mkdir(parents=True, exist_ok=True)
    pasta_relatorios.mkdir(parents=True, exist_ok=True)

    caminho_inventario = pasta_relatorios / "inventario.csv"
    if not caminho_inventario.exists():
        raise FileNotFoundError(
            f"inventario.csv não encontrado em {caminho_inventario}. "
            "Execute primeiro o script 01_inventariar_dataset.py."
        )

    campos_rejeitados = ["md5", "caminho", "motivo_rejeicao", "detalhe"]
    caminho_rejeitados = pasta_relatorios / "arquivos_rejeitados.csv"

    total_analisado = 0
    total_aprovado = 0
    total_rejeitado = 0
    contagem_motivos: Counter = Counter()

    with open(caminho_inventario, encoding="utf-8") as fin, \
         open(caminho_rejeitados, "w", newline="", encoding="utf-8") as frej:

        reader = csv.DictReader(fin)
        writer_rej = csv.DictWriter(frej, fieldnames=campos_rejeitados)
        writer_rej.writeheader()

        registros = list(reader)
        for registro in tqdm(registros, desc="Validando"):
            total_analisado += 1
            motivo, detalhe = motivo_rejeicao(registro, filtros)

            if motivo:
                total_rejeitado += 1
                contagem_motivos[motivo] += 1
                writer_rej.writerow({
                    "md5": registro.get("md5", ""),
                    "caminho": registro.get("caminho_relativo", ""),
                    "motivo_rejeicao": motivo,
                    "detalhe": detalhe,
                })
            else:
                # Copiar para midi_validos
                caminho_original = raiz / registro["caminho_relativo"]
                destino = pasta_validos / caminho_original.name
                if caminho_original.exists():
                    shutil.copy2(caminho_original, destino)
                    total_aprovado += 1
                else:
                    # Arquivo não encontrado — registrar como rejeitado
                    total_rejeitado += 1
                    contagem_motivos["ARQUIVO_NAO_ENCONTRADO"] += 1
                    writer_rej.writerow({
                        "md5": registro.get("md5", ""),
                        "caminho": registro.get("caminho_relativo", ""),
                        "motivo_rejeicao": "ARQUIVO_NAO_ENCONTRADO",
                        "detalhe": str(caminho_original),
                    })

    print("\n===== Resultado da Validação =====")
    print(f"Total analisado : {total_analisado}")
    print(f"Total aprovado  : {total_aprovado}")
    print(f"Total rejeitado : {total_rejeitado}")
    print("\nRejeitados por motivo:")
    for motivo, qtd in contagem_motivos.most_common():
        pct = 100 * qtd / total_analisado if total_analisado else 0
        print(f"  {motivo}: {qtd} ({pct:.1f}%)")

    print(f"\nArquivos rejeitados salvos em: {caminho_rejeitados.relative_to(raiz)}")
    print(f"MIDIs válidos copiados para : {pasta_validos.relative_to(raiz)}")


if __name__ == "__main__":
    main()
