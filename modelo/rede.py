"""LSTM que prevê o próximo token de uma melodia."""

import torch
from torch import nn


class MelodiaLSTM(nn.Module):
    def __init__(self, vocabulario, embedding, oculto, camadas, dropout, pad_id):
        super().__init__()
        self.vocabulario = vocabulario
        self.pad_id = pad_id
        self.emb = nn.Embedding(vocabulario, embedding, padding_idx=pad_id)
        self.lstm = nn.LSTM(
            embedding,
            oculto,
            num_layers=camadas,
            batch_first=True,
            dropout=dropout if camadas > 1 else 0.0,
        )
        self.drop = nn.Dropout(dropout)
        self.cabeca = nn.Linear(oculto, vocabulario)

    def forward(self, tokens, estado=None):
        saida, estado = self.lstm(self.emb(tokens), estado)
        return self.cabeca(self.drop(saida)), estado


@torch.no_grad()
def gerar(
    modelo,
    token_para_id,
    id_para_token,
    num_tokens,
    temperatura=1.0,
    dispositivo="cpu",
    parar_no_fim=True,
):
    """Gera tokens a partir de <START>. Para em <END> quando parar_no_fim é verdadeiro."""
    modelo.eval()
    if dispositivo == "cpu":
        dispositivo = next(modelo.parameters()).device
    inicio = token_para_id["<START>"]
    fim = token_para_id["<END>"]
    pad = token_para_id["<PAD>"]
    idx = torch.tensor([[inicio]], dtype=torch.long, device=dispositivo)
    estado = None
    gerados = []
    temperatura = max(float(temperatura), 1e-6)

    for _ in range(num_tokens):
        logits, estado = modelo(idx, estado)
        logits = logits[:, -1, :] / temperatura
        logits[:, pad] = float("-inf")
        logits[:, inicio] = float("-inf")
        if not parar_no_fim:
            logits[:, fim] = float("-inf")
        probs = torch.softmax(logits, dim=-1)
        proximo = torch.multinomial(probs, num_samples=1)
        token_id = int(proximo.item())
        if token_id == fim:
            break
        gerados.append(id_para_token[str(token_id)])
        idx = proximo

    return gerados
