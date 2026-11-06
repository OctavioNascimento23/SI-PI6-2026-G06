"""
Script 02 — Validar MIDIs e montar o recorte de treino.
Não copia os arquivos. O original em arquivos_brutos permanece no lugar.
"""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from tqdm import tqdm

from comum import aplicar_smoke, carregar_config


def argumentos():
    parser = argparse.ArgumentParser(description="Validar inventário e amostrar o recorte")
    parser.add_argument("--limite", type=int, default=None, help="Lê só as N primeiras linhas do inventário")
    parser.add_argument("--smoke", action="store_true", help="Grava relatórios em relatorios/smoke")
    return parser.parse_args()


def motivo_rejeicao(registro, filtros):
    abre = str(registro.get("abre_sem_erro", "")).strip().lower()
    if abre not in ("true", "1"):
        return "CORROMPIDO", registro.get("erro_leitura", "")

    try:
        num_notas = int(float(registro["num_notas_total"]))
    except (ValueError, KeyError, TypeError):
        num_notas = 0
    try:
        duracao = float(registro["duracao_seg"])
    except (ValueError, KeyError, TypeError):
        duracao = 0.0
    try:
        tamanho = int(float(registro["tamanho_bytes"]))
    except (ValueError, KeyError, TypeError):
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


def amostrar(aprovados, quantidade, semente):
    """Amostra proporcional por pasta do hash (0-9, a-f), com semente fixa."""
    if quantidade >= len(aprovados):
        return list(aprovados)

    grupos = defaultdict(list)
    for linha in aprovados:
        pasta = Path(linha["caminho_relativo"]).parent.name
        grupos[pasta].append(linha)

    rng = np.random.RandomState(semente)
    chaves = sorted(grupos)
    total = len(aprovados)
    quotas = {}
    restos = []
    alocado = 0
    for chave in chaves:
        exato = quantidade * len(grupos[chave]) / total
        base = int(np.floor(exato))
        quotas[chave] = min(base, len(grupos[chave]))
        restos.append((exato - base, chave))
        alocado += quotas[chave]

    for _, chave in sorted(restos, reverse=True):
        if alocado >= quantidade:
            break
        if quotas[chave] < len(grupos[chave]):
            quotas[chave] += 1
            alocado += 1

    escolhidos = []
    for chave in chaves:
        itens = grupos[chave]
        n = quotas[chave]
        if n <= 0:
            continue
        indices = rng.choice(len(itens), size=n, replace=False)
        for indice in indices:
            escolhidos.append(itens[int(indice)])
    rng.shuffle(escolhidos)
    return escolhidos


def main():
    args = argumentos()
    cfg, raiz = carregar_config()
    cfg = aplicar_smoke(cfg, args.smoke)
    filtros = cfg["filtros"]
    pasta_relatorios = raiz / cfg["saidas"]["pasta_relatorios"]
    pasta_relatorios.mkdir(parents=True, exist_ok=True)
    copiar = bool(cfg["saidas"].get("copiar_midi_validos", False))

    caminho_inventario = raiz / "relatorios" / "inventario.csv"
    if not caminho_inventario.exists():
        raise FileNotFoundError(
            "relatorios/inventario.csv não encontrado. Execute o script 01 antes."
        )

    campos_rejeitados = ["md5", "caminho", "motivo_rejeicao", "detalhe"]
    campos_aprovados = [
        "md5", "caminho_relativo", "nome_original", "tamanho_bytes",
        "duracao_seg", "num_notas_total", "bpm_predominante",
        "num_faixas", "tem_bateria",
    ]

    caminho_rejeitados = pasta_relatorios / "arquivos_rejeitados.csv"
    caminho_aprovados = pasta_relatorios / "aprovados.csv"
    caminho_recorte = pasta_relatorios / "recorte.csv"

    total = 0
    contagem = Counter()
    aprovados = []

    with open(caminho_inventario, encoding="utf-8", newline="") as fin, \
         open(caminho_rejeitados, "w", encoding="utf-8", newline="") as frej, \
         open(caminho_aprovados, "w", encoding="utf-8", newline="") as fapr:

        reader = csv.DictReader(fin)
        writer_rej = csv.DictWriter(frej, fieldnames=campos_rejeitados)
        writer_apr = csv.DictWriter(fapr, fieldnames=campos_aprovados)
        writer_rej.writeheader()
        writer_apr.writeheader()

        for registro in tqdm(reader, desc="Validando"):
            if args.limite is not None and total >= args.limite:
                break
            total += 1
            motivo, detalhe = motivo_rejeicao(registro, filtros)
            if motivo:
                contagem[motivo] += 1
                writer_rej.writerow({
                    "md5": registro.get("md5", ""),
                    "caminho": registro.get("caminho_relativo", ""),
                    "motivo_rejeicao": motivo,
                    "detalhe": detalhe,
                })
                continue

            caminho_original = raiz / registro["caminho_relativo"]
            if not caminho_original.exists():
                contagem["ARQUIVO_NAO_ENCONTRADO"] += 1
                writer_rej.writerow({
                    "md5": registro.get("md5", ""),
                    "caminho": registro.get("caminho_relativo", ""),
                    "motivo_rejeicao": "ARQUIVO_NAO_ENCONTRADO",
                    "detalhe": str(caminho_original),
                })
                continue

            if copiar:
                import shutil
                destino_dir = raiz / cfg["saidas"]["pasta_midi_validos"]
                destino_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(caminho_original, destino_dir / caminho_original.name)

            linha = {campo: registro.get(campo, "") for campo in campos_aprovados}
            writer_apr.writerow(linha)
            aprovados.append(linha)

    recorte_ativo = bool(cfg["recorte"]["ativo"])
    quantidade = int(cfg["recorte"]["quantidade"])
    if args.limite is not None:
        quantidade = min(quantidade, len(aprovados))
    semente = int(cfg["recorte"]["semente"])
    escolhidos = amostrar(aprovados, quantidade, semente) if recorte_ativo else list(aprovados)

    with open(caminho_recorte, "w", encoding="utf-8", newline="") as frec:
        writer = csv.DictWriter(frec, fieldnames=campos_aprovados)
        writer.writeheader()
        writer.writerows(escolhidos)

    print("\n===== Resultado da Validação =====")
    print(f"Total analisado : {total}")
    print(f"Total aprovado  : {len(aprovados)}")
    print(f"Total rejeitado : {sum(contagem.values())}")
    print(f"Recorte         : {len(escolhidos)}")
    print("\nRejeitados por motivo:")
    for motivo, qtd in contagem.most_common():
        pct = 100 * qtd / total if total else 0
        print(f"  {motivo}: {qtd} ({pct:.1f}%)")
    print(f"\nAprovados: {caminho_aprovados.relative_to(raiz)}")
    print(f"Recorte  : {caminho_recorte.relative_to(raiz)}")
    if not copiar:
        print("MIDIs aprovados não foram copiados. O pipeline usa o arquivo original.")


if __name__ == "__main__":
    main()
