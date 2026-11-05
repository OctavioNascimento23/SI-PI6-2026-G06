"""
treinar_markov.py
Treina o modelo probabilístico de Cadeia de Markov de 2ª ordem com os dados do pipeline.
Salva o modelo em modelos/markov_modelo.pkl.

Uso:
    python scripts/treinar_markov.py
"""

import json
import sys
from pathlib import Path
import yaml
from tqdm import tqdm

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.modelos.markov import ModeloMarkov


def main():
    with open(RAIZ / "configuracao" / "pipeline.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    pasta_treino = RAIZ / cfg["saidas"]["pasta_treino"]
    caminho_modelo = RAIZ / "modelos" / "markov_modelo.pkl"

    arquivos = [p for p in sorted(pasta_treino.glob("*.json")) if p.stem != "vocabulario"]

    if not arquivos:
        print(f"ERRO: Nenhum arquivo .json encontrado em {pasta_treino}")
        sys.exit(1)

    print(f"Arquivos de treino encontrados: {len(arquivos)}")

    todas_sequencias = []
    for arq in tqdm(arquivos, desc="Carregando sequências"):
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
            tokens = dados.get("tokens", [])
            if tokens:
                todas_sequencias.append(tokens)
        except Exception as e:
            print(f"  AVISO: erro ao ler {arq.name}: {e}")

    print(f"\nTotal de sequências válidas: {len(todas_sequencias)}")
    print("Treinando Cadeia de Markov (ordem=2)...")

    modelo = ModeloMarkov(ordem=2)
    modelo.treinar(todas_sequencias)

    estados_unicos = len(modelo.transicoes)
    print(f"Estados únicos aprendidos: {estados_unicos:,}")

    modelo.salvar(caminho_modelo)
    tamanho_mb = caminho_modelo.stat().st_size / (1024 ** 2)
    print(f"\nModelo salvo em: {caminho_modelo.relative_to(RAIZ)}")
    print(f"Tamanho do arquivo: {tamanho_mb:.2f} MB")


if __name__ == "__main__":
    main()
