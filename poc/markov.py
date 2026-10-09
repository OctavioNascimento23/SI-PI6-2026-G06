"""
markov.py
Cadeia de Markov de ordem N para geração de sequências de tokens musicais.
"""

import pickle
import random
from pathlib import Path


class ModeloMarkov:
    def __init__(self, ordem: int = 2):
        self.ordem = ordem
        # { tupla_estado → {proximo_token: contagem} }
        self.transicoes: dict[tuple, dict[str, int]] = {}
        # tuplas iniciais (começo de cada sequência de treino)
        self.inicios: list[tuple] = []

    # ------------------------------------------------------------------
    # Treino
    # ------------------------------------------------------------------

    def treinar(self, lista_de_sequencias: list[list[str]]) -> None:
        """Constrói a tabela de transições a partir de uma lista de sequências."""
        for seq in lista_de_sequencias:
            if len(seq) < self.ordem + 1:
                continue

            # Registrar estado inicial
            estado_inicial = tuple(seq[: self.ordem])
            self.inicios.append(estado_inicial)

            # Percorrer janelas deslizantes
            for i in range(len(seq) - self.ordem):
                estado = tuple(seq[i : i + self.ordem])
                proximo = seq[i + self.ordem]
                if estado not in self.transicoes:
                    self.transicoes[estado] = {}
                self.transicoes[estado][proximo] = (
                    self.transicoes[estado].get(proximo, 0) + 1
                )

    # ------------------------------------------------------------------
    # Geração
    # ------------------------------------------------------------------

    def gerar(
        self,
        num_tokens: int,
        semente: int | None = None,
        tokens_iniciais: list[str] | None = None,
    ) -> list[str]:
        """
        Gera uma sequência de tokens usando as probabilidades aprendidas.
        Se não houver transição conhecida, reinicia de um estado aleatório.
        """
        if not self.transicoes:
            raise RuntimeError("Modelo não treinado. Chame treinar() antes de gerar().")

        rng = random.Random(semente)

        # Estado inicial
        if tokens_iniciais and len(tokens_iniciais) >= self.ordem:
            estado = tuple(tokens_iniciais[-self.ordem :])
            resultado = list(tokens_iniciais)
        else:
            estado = rng.choice(self.inicios)
            resultado = list(estado)

        for _ in range(num_tokens):
            candidatos = self.transicoes.get(estado)
            if not candidatos:
                # Estado terminal → reinicia
                estado = rng.choice(self.inicios)
                resultado.extend(list(estado))
                continue

            # Escolha ponderada pelas contagens
            tokens_possiveis = list(candidatos.keys())
            pesos = list(candidatos.values())
            proximo = rng.choices(tokens_possiveis, weights=pesos, k=1)[0]

            resultado.append(proximo)
            estado = tuple(resultado[-self.ordem :])

        return resultado

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def salvar(self, caminho: str | Path) -> None:
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "wb") as f:
            pickle.dump(
                {"ordem": self.ordem,
                 "transicoes": self.transicoes,
                 "inicios": self.inicios},
                f,
            )

    def carregar(self, caminho: str | Path) -> None:
        with open(caminho, "rb") as f:
            dados = pickle.load(f)
        self.ordem = dados["ordem"]
        self.transicoes = dados["transicoes"]
        self.inicios = dados["inicios"]
