"""
transformer_model.py
Arquitetura Transformer Autoregressivo (Decoder-Only / GPT-like) para Composição Musical.
Utiliza Mecanismo de Atenção Causal (Masked Self-Attention) e Embeddings Posicionais.
"""

import math
from pathlib import Path
from typing import Callable, List, Dict, Optional, Union, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 2048):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [batch_size, seq_len, d_model]
        return x + self.pe[:, : x.size(1)]


class MusicTransformer(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        d_model: int = 256,
        nhead: int = 4,
        num_layers: int = 4,
        dim_feedforward: int = 512,
        dropout: float = 0.1,
        max_seq_len: int = 1024,
    ):
        super().__init__()
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.nhead = nhead
        self.num_layers = num_layers
        self.dim_feedforward = dim_feedforward
        self.max_seq_len = max_seq_len

        self.embedding = nn.Embedding(vocab_size, d_model)
        self.pos_encoder = PositionalEncoding(d_model, max_len=max_seq_len)
        # Vocabulário usado no treino (preenchido por carregar()); os IDs só são válidos com ele
        self.vocabulario: Optional[dict] = None

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.fc_out = nn.Linear(d_model, vocab_size)

    def _generate_square_subsequent_mask(self, sz: int, device: torch.device) -> torch.Tensor:
        mask = torch.triu(torch.full((sz, sz), float("-inf"), device=device), diagonal=1)
        return mask

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        seq_len = x.size(1)
        mask = self._generate_square_subsequent_mask(seq_len, x.device)
        
        embeds = self.embedding(x) * math.sqrt(self.d_model)
        x_pos = self.pos_encoder(embeds)
        out = self.transformer(x_pos, mask=mask, is_causal=True)
        logits = self.fc_out(out)
        return logits

    @torch.no_grad()
    def gerar(
        self,
        token_para_id: Dict[str, int],
        id_para_token: Dict[str, str],
        num_tokens: int = 60,
        temperatura: float = 0.80,
        top_k: int = 12,
        top_p: float = 0.88,
        repetition_penalty: float = 1.35,
        tokens_iniciais: Optional[List[str]] = None,
        device: str = "cpu",
        ajustar_logits: Optional[Callable] = None,
    ) -> List[str]:
        """
        Gera tokens musicais autoregressivamente com amostragem inteligente:
        - Penalidade de repetição (evita loops e trilos estáticos)
        - Regra de gramática musical (NOTE -> DURATION -> NOTE/REST)
        - Suavização melódica
        """
        self.eval()
        self.to(device)

        start_id = token_para_id.get("<START>", 72 if "<START>" in token_para_id else 0)
        pad_id = token_para_id.get("<PAD>", 71 if "<PAD>" in token_para_id else 0)
        end_id = token_para_id.get("<END>", 73 if "<END>" in token_para_id else 0)

        # Mapeia categorias de tokens
        ids_notas = [id_ for tok, id_ in token_para_id.items() if tok.startswith("NOTE_")]
        ids_duracoes = [id_ for tok, id_ in token_para_id.items() if tok.startswith("DURATION_")]
        ids_pausas = [id_ for tok, id_ in token_para_id.items() if tok.startswith("REST_")]

        # Identifica token de duração mínima para evitar excesso de micro-notas (0.12)
        id_dur_min = token_para_id.get("DURATION_0.12", None)

        if tokens_iniciais:
            seq_ids = [token_para_id.get(t, start_id) for t in tokens_iniciais]
        else:
            # Inicia com uma nota central agradável (ex: Dó central pitch 60 ou Sol 67)
            id_nota_inicial = token_para_id.get("NOTE_60", token_para_id.get("NOTE_64", 29))
            seq_ids = [start_id, id_nota_inicial]

        tokens_gerados = []
        if tokens_iniciais:
            tokens_gerados.extend(tokens_iniciais)
        else:
            tok_init = id_para_token.get(str(id_nota_inicial), id_para_token.get(id_nota_inicial, "NOTE_60"))
            tokens_gerados.append(tok_init)

        ultimo_tipo = "NOTE"
        tempo_beats = 0.0  # posição atual da melodia, em beats (para guiar pela harmonia)

        for _ in range(num_tokens):
            ctx = seq_ids[-self.max_seq_len :]
            input_tensor = torch.tensor([ctx], dtype=torch.long, device=device)
            logits = self.forward(input_tensor)

            next_token_logits = logits[0, -1, :].clone()

            # 1. Penalidade de repetição para tokens recentes
            for prev_id in set(seq_ids[-8:]):
                if prev_id < len(next_token_logits):
                    if next_token_logits[prev_id] > 0:
                        next_token_logits[prev_id] /= repetition_penalty
                    else:
                        next_token_logits[prev_id] *= repetition_penalty

            # 2. Gramática Musical Rígida (Alternância Nota <-> Duração)
            if ultimo_tipo == "NOTE":
                # Após uma nota, OBRIGATORIAMENTE deve vir uma duração
                for i in range(self.vocab_size):
                    if i not in ids_duracoes:
                        next_token_logits[i] = -float("Inf")
                # Penaliza durações microscópicas repetidas
                if id_dur_min is not None and id_dur_min < len(next_token_logits):
                    next_token_logits[id_dur_min] -= 2.0
            else:
                # Após uma duração ou pausa, deve vir uma NOTA ou uma PAUSA
                for i in range(self.vocab_size):
                    if i in ids_duracoes:
                        next_token_logits[i] = -float("Inf")

            # 2.1 Guia externo (harmonia e ritmo): o guia sabe, pelos tokens, se espera nota ou duração
            if ajustar_logits is not None:
                next_token_logits = ajustar_logits(next_token_logits, tempo_beats, tokens_gerados)

            # 3. Evitar tokens especiais indesejados
            next_token_logits[pad_id] = -float("Inf")
            next_token_logits[start_id] = -float("Inf")
            next_token_logits[end_id] = -float("Inf")

            # 4. Aplicação de Temperatura
            next_token_logits = next_token_logits / max(temperatura, 0.01)

            # 5. Filtro Top-K
            if top_k > 0:
                indices_to_remove = next_token_logits < torch.topk(next_token_logits, min(top_k, self.vocab_size))[0][..., -1, None]
                next_token_logits[indices_to_remove] = -float("Inf")

            # 6. Filtro Top-P (Nucleus Sampling)
            if 0.0 < top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(next_token_logits, descending=True)
                cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                sorted_indices_to_remove = cumulative_probs > top_p
                sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                sorted_indices_to_remove[..., 0] = 0
                indices_to_remove = sorted_indices[sorted_indices_to_remove]
                next_token_logits[indices_to_remove] = -float("Inf")

            probs = F.softmax(next_token_logits, dim=-1)
            proximo_id = torch.multinomial(probs, num_samples=1).item()

            tok_str = id_para_token.get(str(proximo_id), id_para_token.get(proximo_id, "NOTE_60"))
            if tok_str == "<END>":
                break

            tokens_gerados.append(tok_str)
            seq_ids.append(proximo_id)

            if tok_str.startswith("NOTE_"):
                ultimo_tipo = "NOTE"
            elif tok_str.startswith("DURATION_"):
                ultimo_tipo = "DURATION"
                tempo_beats += float(tok_str.split("_")[1])
            else:
                ultimo_tipo = "REST"
                tempo_beats += float(tok_str.split("_")[1])

        return tokens_gerados

    def salvar(self, caminho: Union[str, Path], vocabulario: Optional[dict] = None) -> None:
        caminho = Path(caminho)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": self.state_dict(),
                "vocab_size": self.vocab_size,
                "d_model": self.d_model,
                "nhead": self.nhead,
                "num_layers": self.num_layers,
                "dim_feedforward": self.dim_feedforward,
                "max_seq_len": self.max_seq_len,
                "vocabulario": vocabulario,
            },
            caminho,
        )

    @classmethod
    def carregar(cls, caminho: Union[str, Path], map_location: str = "cpu") -> "MusicTransformer":
        ckpt = torch.load(caminho, map_location=map_location, weights_only=False)
        modelo = cls(
            vocab_size=ckpt["vocab_size"],
            d_model=ckpt["d_model"],
            nhead=ckpt["nhead"],
            num_layers=ckpt["num_layers"],
            dim_feedforward=ckpt["dim_feedforward"],
            max_seq_len=ckpt.get("max_seq_len", 1024),
        )
        modelo.load_state_dict(ckpt["state_dict"])
        modelo.eval()
        modelo.vocabulario = ckpt.get("vocabulario")
        return modelo
