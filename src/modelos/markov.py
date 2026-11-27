"""
markov.py
Cadeia de Markov de ordem N para modelagem probabilística de sequências musicais.
"""

import pickle
import random
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union


class ModeloMarkov:
    def __init__(self, ordem: int = 2):
        self.ordem = ordem
        # { tupla_estado → {proximo_token: contagem} }
        self.transicoes: Dict[Tuple[str, ...], Dict[str, int]] = {}
        # tuplas iniciais (começo de cada sequência de treino)
        self.inicios: List[Tuple[str, ...]] = []

    def treinar(self, lista_de_sequencias: List[List[str]]) -> None:
        """Constrói a matriz de transições empíricas a partir das sequências de treino."""
        for seq in lista_de_sequencias:
            if len(seq) < self.ordem + 1:
                continue

            estado_inicial = tuple(seq[: self.ordem])
            self.inicios.append(estado_inicial)

            for i in range(len(seq) - self.ordem):
                estado = tuple(seq[i : i + self.ordem])
                proximo = seq[i + self.ordem]
                if estado not in self.transicoes:
                    self.transicoes[estado] = {}
                self.transicoes[estado][proximo] = (
                    self.transicoes[estado].get(proximo, 0) + 1
                )

    def gerar(
        self,
        num_tokens: int,
        semente: Optional[int] = None,
        tokens_iniciais: Optional[List[str]] = None,
    ) -> List[str]:
        """Gera uma nova sequência de tokens com base nas transições aprendidas."""
        if not self.transicoes:
            raise RuntimeError("Modelo não treinado. Chame treinar() antes de gerar().")

        rng = random.Random(semente)

        if tokens_iniciais and len(tokens_iniciais) >= self.ordem:
            estado = tuple(tokens_iniciais[-self.ordem :])
            resultado = list(tokens_iniciais)
        else:
            estado = rng.choice(self.inicios)
            resultado = list(estado)

        for _ in range(num_tokens):
            candidatos = self.transicoes.get(estado)
            if not candidatos:
                estado = rng.choice(self.inicios)
                resultado.extend(list(estado))
                continue

            tokens_possiveis = list(candidatos.keys())
            pesos = list(candidatos.values())
            proximo = rng.choices(tokens_possiveis, weights=pesos, k=1)[0]

            resultado.append(proximo)
            estado = tuple(resultado[-self.ordem :])

        return resultado

    def salvar(self, caminho: Union[str, Path]) -> None:
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "wb") as f:
            pickle.dump(
                {
                    "ordem": self.ordem,
                    "transicoes": self.transicoes,
                    "inicios": self.inicios,
                },
                f,
            )

    def carregar(self, caminho: Union[str, Path]) -> None:
        with open(caminho, "rb") as f:
            dados = pickle.load(f)
        self.ordem = dados["ordem"]
        self.transicoes = dados["transicoes"]
        self.inicios = dados["inicios"]
