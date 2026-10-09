"""
treinar_markov.py
Carrega as sequências tokenizadas do conjunto de treino e treina o modelo Markov.
Salva o modelo em modelos/markov_modelo.pkl.

Uso:
    python poc/treinar_markov.py
"""

import json
import os
import sys
from pathlib import Path

import yaml
from tqdm import tqdm

# Garante que a raiz do projeto está no sys.path
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from poc.markov import ModeloMarkov


def main():
    # Carregar configuração
    with open(RAIZ / "configuracao" / "pipeline.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    pasta_treino = RAIZ / cfg["saidas"]["pasta_treino"]
    caminho_modelo = RAIZ / "modelos" / "markov_modelo.pkl"

    arquivos = [p for p in sorted(pasta_treino.glob("*.json"))
                if p.stem != "vocabulario"]

    if not arquivos:
        print(f"ERRO: Nenhum arquivo .json encontrado em {pasta_treino}")
        print("Execute o pipeline (scripts 01–05) antes de treinar.")
        sys.exit(1)

    print(f"Arquivos de treino encontrados: {len(arquivos)}")

    # Carregar todas as sequências
    todas_sequencias: list[list[str]] = []
    for arq in tqdm(arquivos, desc="Carregando sequências"):
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
            tokens = dados.get("tokens", [])
            if tokens:
                todas_sequencias.append(tokens)
        except Exception as e:
            print(f"  AVISO: erro ao ler {arq.name}: {e}")

    print(f"\nSequências carregadas: {len(todas_sequencias)}")

    # Treinar modelo
    print("Treinando Cadeia de Markov (ordem=2)...")
    modelo = ModeloMarkov(ordem=2)
    modelo.treinar(todas_sequencias)

    estados_unicos = len(modelo.transicoes)
    print(f"Estados únicos aprendidos: {estados_unicos:,}")

    # Salvar
    modelo.salvar(caminho_modelo)
    tamanho_mb = caminho_modelo.stat().st_size / (1024 ** 2)
    print(f"\nModelo salvo em: {caminho_modelo.relative_to(RAIZ)}")
    print(f"   Sequencias usadas  : {len(todas_sequencias):,}")
    print(f"   Estados unicos     : {estados_unicos:,}")
    print(f"   Tamanho do modelo  : {tamanho_mb:.2f} MB")

    # Exemplos de transições
    print("\nExemplo de 3 transições aprendidas:")
    for estado, prox in list(modelo.transicoes.items())[:3]:
        top = sorted(prox.items(), key=lambda x: -x[1])[:3]
        print(f"  {estado} → {top}")


if __name__ == "__main__":
    main()
