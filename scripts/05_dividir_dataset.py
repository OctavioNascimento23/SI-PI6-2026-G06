"""
Script 05 — Dividir as sequências em treino, validação e teste por MD5.
Cada música vai inteira para um único conjunto. A saída é um JSONL por conjunto.
"""

import argparse
import json
import shutil

from sklearn.model_selection import train_test_split

from comum import aplicar_smoke, carregar_config


def argumentos():
    parser = argparse.ArgumentParser(description="Dividir sequências em treino, validação e teste")
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def dividir(md5s, pct_treino, pct_val, semente):
    if len(md5s) < 5:
        n = len(md5s)
        n_treino = max(1, int(round(n * pct_treino)))
        resto = md5s[n_treino:]
        meio = max(1, len(resto) // 2) if resto else 0
        return md5s[:n_treino], resto[:meio], resto[meio:]

    val_teste = 1.0 - pct_treino
    treino, resto = train_test_split(
        md5s, test_size=val_teste, random_state=semente, shuffle=True
    )
    pct_val_do_resto = pct_val / val_teste
    validacao, teste = train_test_split(
        resto,
        test_size=(1.0 - pct_val_do_resto),
        random_state=semente,
        shuffle=True,
    )
    return list(treino), list(validacao), list(teste)


def main():
    args = argumentos()
    cfg, raiz = carregar_config()
    cfg = aplicar_smoke(cfg, args.smoke)
    semente = int(cfg["divisao"]["semente"])
    pct_treino = float(cfg["divisao"]["treino"])
    pct_val = float(cfg["divisao"]["validacao"])

    pasta_sequencias = raiz / cfg["saidas"]["pasta_sequencias"]
    pasta_treino = raiz / cfg["saidas"]["pasta_treino"]
    pasta_validacao = raiz / cfg["saidas"]["pasta_validacao"]
    pasta_teste = raiz / cfg["saidas"]["pasta_teste"]
    pasta_relatorios = raiz / cfg["saidas"]["pasta_relatorios"]
    for pasta in (pasta_treino, pasta_validacao, pasta_teste, pasta_relatorios):
        pasta.mkdir(parents=True, exist_ok=True)

    caminho_jsonl = pasta_sequencias / "sequencias.jsonl"
    if not caminho_jsonl.exists():
        print(f"Nenhuma sequência em {caminho_jsonl}. Execute o script 04 antes.")
        return

    por_md5 = {}
    with open(caminho_jsonl, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            registro = json.loads(linha)
            por_md5[registro["md5"]] = linha

    md5s = sorted(por_md5)
    print(f"Total de sequências: {len(md5s)}")
    if not md5s:
        print("JSONL vazio.")
        return

    md5s_treino, md5s_val, md5s_teste = dividir(md5s, pct_treino, pct_val, semente)
    conjuntos = {
        "treino": (md5s_treino, pasta_treino),
        "validacao": (md5s_val, pasta_validacao),
        "teste": (md5s_teste, pasta_teste),
    }

    for nome, (lista, pasta) in conjuntos.items():
        destino = pasta / "sequencias.jsonl"
        with open(destino, "w", encoding="utf-8") as saida:
            for md5 in lista:
                saida.write(por_md5[md5] + "\n")
        print(f"{nome}: {len(lista)} -> {destino.relative_to(raiz)}")

    caminho_vocab = pasta_sequencias / "vocabulario.json"
    if caminho_vocab.exists():
        for pasta in (pasta_treino, pasta_validacao, pasta_teste):
            shutil.copy2(caminho_vocab, pasta / "vocabulario.json")

    relatorio = {
        "total_sequencias": len(md5s),
        "treino": len(md5s_treino),
        "validacao": len(md5s_val),
        "teste": len(md5s_teste),
        "semente": semente,
        "md5s_treino": md5s_treino,
        "md5s_validacao": md5s_val,
        "md5s_teste": md5s_teste,
    }
    caminho_relatorio = pasta_relatorios / "divisao_dataset.json"
    caminho_relatorio.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nRelatório salvo em: {caminho_relatorio.relative_to(raiz)}")


if __name__ == "__main__":
    main()
