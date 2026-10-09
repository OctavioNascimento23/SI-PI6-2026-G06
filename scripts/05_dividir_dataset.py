"""
Script 05 — Dividir o dataset
Divide os arquivos de sequências em treino, validação e teste por MD5.
"""

import json
import shutil
from pathlib import Path

import yaml
from sklearn.model_selection import train_test_split
from tqdm import tqdm


def carregar_config():
    raiz = Path(__file__).resolve().parent.parent
    with open(raiz / "configuracao" / "pipeline.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f), raiz


def main():
    cfg, raiz = carregar_config()
    semente = cfg["divisao"]["semente"]
    pct_treino = cfg["divisao"]["treino"]
    pct_val = cfg["divisao"]["validacao"]
    # pct_teste = cfg["divisao"]["teste"]  # implícito pelo restante

    pasta_sequencias = raiz / cfg["saidas"]["pasta_sequencias"]
    pasta_treino = raiz / cfg["saidas"]["pasta_treino"]
    pasta_validacao = raiz / cfg["saidas"]["pasta_validacao"]
    pasta_teste = raiz / cfg["saidas"]["pasta_teste"]
    pasta_relatorios = raiz / cfg["saidas"]["pasta_relatorios"]

    for pasta in (pasta_treino, pasta_validacao, pasta_teste, pasta_relatorios):
        pasta.mkdir(parents=True, exist_ok=True)

    # 1. Listar todos os .json (excluir vocabulario.json)
    todos_jsons = [
        p for p in sorted(pasta_sequencias.glob("*.json"))
        if p.stem != "vocabulario"
    ]
    md5s = [p.stem for p in todos_jsons]
    print(f"Total de sequências: {len(md5s)}")

    if len(md5s) == 0:
        print("Nenhuma sequência encontrada. Execute primeiro o script 04_tokenizar.py.")
        return

    # 2. Divisão: treino / (validação + teste)
    val_teste_pct = 1.0 - pct_treino
    md5s_treino, md5s_resto = train_test_split(
        md5s, test_size=val_teste_pct, random_state=semente, shuffle=True
    )

    # Dividir o restante em validação e teste (proporções iguais)
    pct_val_do_resto = pct_val / val_teste_pct
    md5s_val, md5s_teste = train_test_split(
        md5s_resto, test_size=0.5, random_state=semente, shuffle=True
    )
    # Se pct_val != pct_teste, ajustar:
    # pct_val_do_resto pode não ser exatamente 0.5 em outros cenários — re-split correto:
    md5s_val, md5s_teste = train_test_split(
        md5s_resto,
        test_size=(1.0 - pct_val_do_resto),
        random_state=semente,
        shuffle=True,
    )

    conjuntos = {
        "treino": (md5s_treino, pasta_treino),
        "validacao": (md5s_val, pasta_validacao),
        "teste": (md5s_teste, pasta_teste),
    }

    # 3. Copiar arquivos para cada conjunto
    caminho_vocab = pasta_sequencias / "vocabulario.json"

    for nome, (md5s_lista, pasta_dest) in conjuntos.items():
        print(f"Copiando {len(md5s_lista)} arquivos para {nome}...")
        for md5 in tqdm(md5s_lista, desc=nome):
            origem = pasta_sequencias / f"{md5}.json"
            if origem.exists():
                shutil.copy2(origem, pasta_dest / origem.name)
        # Copiar vocabulário para cada pasta
        if caminho_vocab.exists():
            shutil.copy2(caminho_vocab, pasta_dest / "vocabulario.json")

    # 4. Relatório divisao_dataset.json
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
    with open(caminho_relatorio, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)

    print("\n===== Resultado da Divisão =====")
    print(f"Total de sequências : {len(md5s)}")
    print(f"Treino              : {len(md5s_treino)} ({100*len(md5s_treino)/len(md5s):.1f}%)")
    print(f"Validação           : {len(md5s_val)} ({100*len(md5s_val)/len(md5s):.1f}%)")
    print(f"Teste               : {len(md5s_teste)} ({100*len(md5s_teste)/len(md5s):.1f}%)")
    print(f"\nRelatório salvo em: {caminho_relatorio.relative_to(raiz)}")


if __name__ == "__main__":
    main()
