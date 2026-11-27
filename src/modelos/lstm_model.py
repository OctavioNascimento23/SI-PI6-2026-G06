"""
lstm_model.py
Arquitetura Neural Recorrente (Stacked LSTM) para Modelagem de Sequências Musicais.
"""

from pathlib import Path
from typing import Callable, List, Dict, Optional, Union, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


VIES_DURACAO_PADRAO: Dict[str, float] = {
    "DURATION_0.25": -0.8,
    "DURATION_1.00": 0.2,
}


class MelodyLSTM(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        embed_dim: int = 128,
        hidden_dim: int = 256,
        num_layers: int = 2,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        # Vocabulário usado no treino (preenchido por carregar()); os IDs só são válidos com ele
        self.vocabulario: Optional[dict] = None

        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.lstm = nn.LSTM(
            embed_dim,
            hidden_dim,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, vocab_size)

    def forward(
        self, x: torch.Tensor, hidden: Optional[Tuple[torch.Tensor, torch.Tensor]] = None
    ) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        embeds = self.embedding(x)
        out, hidden = self.lstm(embeds, hidden)
        out = self.dropout(out)
        logits = self.fc(out)
        return logits, hidden

    @torch.no_grad()
    def gerar(
        self,
        token_para_id: Dict[str, int],
        id_para_token: Dict[str, str],
        num_tokens: int = 60,
        temperatura: float = 0.9,
        top_k: int = 10,
        tokens_iniciais: Optional[List[str]] = None,
        device: str = "cpu",
        ajustar_logits: Optional[Callable] = None,
        beats_alvo: Optional[float] = None,
        penalidade_repeticao: float = 1.0,
        vies_duracao: Optional[Dict[str, float]] = None,
    ) -> List[str]:
        """
        Gera sequências de tokens musicais utilizando amostragem com temperatura e Top-K.
        Se `beats_alvo` for dado, continua gerando até a melodia cobrir essa duração
        (`num_tokens` passa a ser só um teto de segurança).
        """
        self.eval()
        self.to(device)

        start_id = token_para_id.get("<START>", 0)
        pad_id = token_para_id.get("<PAD>", 0)
        # Durações de 1/8 de beat (gravadas como "0.12"): sem penalidade o modelo escolhe sequências
        # delas e a melodia termina muito antes da duração pedida (mesma proteção do Transformer)
        id_dur_min = token_para_id.get("DURATION_0.12")
        # A LSTM escolhe 1/4 de beat em ~70% das notas (ritmo uniforme e corrido); o viés espalha as durações
        if vies_duracao is None:
            vies_duracao = VIES_DURACAO_PADRAO
        ids_vies = {token_para_id[t]: v for t, v in vies_duracao.items() if t in token_para_id}

        if tokens_iniciais:
            ids_historico = [token_para_id.get(t, start_id) for t in tokens_iniciais]
        else:
            ids_historico = [start_id]

        input_tensor = torch.tensor([ids_historico], dtype=torch.long, device=device)
        logits, hidden = self.forward(input_tensor)

        tokens_gerados = list(tokens_iniciais) if tokens_iniciais else []
        tempo_beats = 0.0
        ultimo_foi_nota = False
        for t in tokens_gerados:
            if t.startswith(("DURATION_", "REST_")):
                tempo_beats += float(t.split("_")[1])
            ultimo_foi_nota = t.startswith("NOTE_")

        for _ in range(num_tokens):
            if beats_alvo is not None and tempo_beats >= beats_alvo:
                break
            last_logits = logits[:, -1, :].clone()
            if id_dur_min is not None:
                last_logits[0, id_dur_min] -= 2.0
            if tokens_gerados and tokens_gerados[-1].startswith("NOTE_"):
                for idx_dur, v in ids_vies.items():
                    last_logits[0, idx_dur] += v
            # Sem isso a LSTM trava na mesma nota; penaliza só notas recentes (durações ficam intactas)
            if penalidade_repeticao > 0:
                for t in tokens_gerados[-8:]:
                    if t.startswith("NOTE_"):
                        last_logits[0, token_para_id[t]] -= penalidade_repeticao
            # Guia externo (harmonia e ritmo): o guia sabe, pelos tokens, se espera nota ou duração
            if ajustar_logits is not None:
                last_logits[0] = ajustar_logits(last_logits[0], tempo_beats, tokens_gerados)
            last_logits = last_logits / max(temperatura, 0.01)

            # Mascarar tokens especiais para não interromper precocemente
            last_logits[:, pad_id] = -float("Inf")
            last_logits[:, start_id] = -float("Inf")

            # Top-K filtering
            if top_k > 0:
                vals, idxs = torch.topk(last_logits, min(top_k, self.vocab_size))
                probs = F.softmax(vals, dim=-1)
                escolhido_idx = torch.multinomial(probs, num_samples=1)
                proximo_id = idxs.gather(-1, escolhido_idx).item()
            else:
                probs = F.softmax(last_logits, dim=-1)
                proximo_id = torch.multinomial(probs, num_samples=1).item()

            tok_str = id_para_token.get(str(proximo_id), id_para_token.get(proximo_id, f"NOTE_60"))
            if tok_str == "<END>":
                break

            tokens_gerados.append(tok_str)
            if tok_str.startswith(("DURATION_", "REST_")):
                valor = float(tok_str.split("_")[1])
                tempo_beats += 0.125 if valor == 0.12 else valor
            ultimo_foi_nota = tok_str.startswith("NOTE_")


            novo_input = torch.tensor([[proximo_id]], dtype=torch.long, device=device)
            logits, hidden = self.forward(novo_input, hidden)

        return tokens_gerados

    def salvar(self, caminho: Union[str, Path]) -> None:
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": self.state_dict(),
                "vocab_size": self.vocab_size,
                "embed_dim": self.embed_dim,
                "hidden_dim": self.hidden_dim,
                "num_layers": self.num_layers,
            },
            caminho,
        )

    @classmethod
    def carregar(cls, caminho: Union[str, Path], map_location: str = "cpu") -> "MelodyLSTM":
        ckpt = torch.load(caminho, map_location=map_location, weights_only=False)
        modelo = cls(
            vocab_size=ckpt["vocab_size"],
            embed_dim=ckpt["embed_dim"],
            hidden_dim=ckpt["hidden_dim"],
            num_layers=ckpt["num_layers"],
        )
        modelo.load_state_dict(ckpt["state_dict"])
        modelo.eval()
        modelo.vocabulario = ckpt.get("vocabulario")
        return modelo
