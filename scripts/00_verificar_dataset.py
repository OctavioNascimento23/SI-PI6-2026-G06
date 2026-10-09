"""
Script 00 — Verificar o dataset
Confirma que o LMD-full está extraído corretamente, sem modificar nada.
"""

import os
import json
from pathlib import Path
from collections import Counter

import yaml


def carregar_config():
    raiz = Path(__file__).resolve().parent.parent
    with open(raiz / "configuracao" / "pipeline.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f), raiz


def main():
    cfg, raiz = carregar_config()
    pasta_lmd = raiz / cfg["dataset"]["pasta_lmd_full"]
    arquivo_md5 = raiz / cfg["dataset"]["arquivo_md5_json"]
    extensoes = tuple(cfg["dataset"]["extensoes"])
    pasta_relatorios = raiz / cfg["saidas"]["pasta_relatorios"]
    pasta_relatorios.mkdir(parents=True, exist_ok=True)

    linhas = []

    # 1. Localizar todos os MIDIs recursivamente
    print("Varrendo arquivos MIDI em:", pasta_lmd)
    todos_midis = [p for p in pasta_lmd.rglob("*") if p.suffix.lower() in extensoes]
    total = len(todos_midis)

    msg = f"Total de arquivos MIDI encontrados: {total}"
    print(msg)
    linhas.append(msg)

    # 2. Primeiros 10 caminhos
    linhas.append("\nPrimeiros 10 caminhos:")
    for p in todos_midis[:10]:
        rel = p.relative_to(raiz)
        print(" ", rel)
        linhas.append(f"  {rel}")

    # 3. Distribuição por primeiro nível de subpasta
    contagem = Counter()
    for p in todos_midis:
        try:
            partes = p.relative_to(pasta_lmd).parts
            primeiro_nivel = partes[0] if len(partes) > 1 else "(raiz)"
        except ValueError:
            primeiro_nivel = "(desconhecido)"
        contagem[primeiro_nivel] += 1

    linhas.append("\nDistribuição por primeiro nível de subpasta (top 20):")
    for subpasta, qtd in contagem.most_common(20):
        linha = f"  {subpasta}: {qtd}"
        print(linha)
        linhas.append(linha)

    # 4. Tamanho total em disco
    tamanho_total_bytes = sum(p.stat().st_size for p in todos_midis)
    tamanho_mb = tamanho_total_bytes / (1024 ** 2)
    tamanho_gb = tamanho_total_bytes / (1024 ** 3)
    msg_tam = f"\nTamanho total em disco: {tamanho_mb:.1f} MB ({tamanho_gb:.2f} GB)"
    print(msg_tam)
    linhas.append(msg_tam)

    # 5. md5_to_paths.json
    linhas.append("\n--- md5_to_paths.json ---")
    if arquivo_md5.exists():
        with open(arquivo_md5, encoding="utf-8") as f:
            md5_map = json.load(f)

        msg_total_md5 = f"Total de entradas no md5_to_paths.json: {len(md5_map)}"
        print(msg_total_md5)
        linhas.append(msg_total_md5)

        linhas.append("Exemplos das 5 primeiras entradas:")
        for i, (chave, valor) in enumerate(list(md5_map.items())[:5]):
            linha = f"  {chave}: {valor}"
            print(linha)
            linhas.append(linha)

        linhas.append('Estrutura esperada: { "hash_md5": ["caminho/nome.mid"] }')
    else:
        msg_no_md5 = f"AVISO: arquivo md5_to_paths.json não encontrado em {arquivo_md5}"
        print(msg_no_md5)
        linhas.append(msg_no_md5)

    # 6. Salvar relatório
    caminho_relatorio = pasta_relatorios / "verificacao_inicial.txt"
    with open(caminho_relatorio, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    print(f"\nRelatório salvo em: {caminho_relatorio.relative_to(raiz)}")


if __name__ == "__main__":
    main()
