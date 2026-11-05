"""
treinar_neural.py
Script para treinamento de Modelos Neurais Profundos (Transformer ou LSTM)
em ambiente local ou Google Colab com suporte a GPU/CUDA.

Uso:
    python scripts/treinar_neural.py --modelo transformer --epochs 15 --batch_size 32
    python scripts/treinar_neural.py --modelo lstm --epochs 20 --batch_size 32
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.modelos.transformer_model import MusicTransformer
from src.modelos.lstm_model import MelodyLSTM


class DatasetSequenciasMusicais(Dataset):
    def __init__(self, pasta_dados: Path, token_para_id: dict, seq_len: int = 128):
        self.seq_len = seq_len
        self.token_para_id = token_para_id
        self.pad_id = token_para_id.get("<PAD>", 0)
        self.start_id = token_para_id.get("<START>", 0)
        self.end_id = token_para_id.get("<END>", 0)

        self.amostras: List[List[int]] = []
        arquivos = [p for p in sorted(pasta_dados.glob("*.json")) if p.stem != "vocabulario"]

        print(f"Carregando {len(arquivos)} arquivos de {pasta_dados.name}...")
        for arq in arquivos:
            try:
                dados = json.loads(arq.read_text(encoding="utf-8"))
                tokens = dados.get("tokens", [])
                if len(tokens) >= 8:
                    ids = [self.start_id] + [self.token_para_id.get(t, self.pad_id) for t in tokens] + [self.end_id]
                    # Cria janelas deslizantes se a sequência for longa
                    for i in range(0, max(1, len(ids) - seq_len), max(1, seq_len // 2)):
                        janela = ids[i : i + seq_len + 1]
                        if len(janela) > 4:
                            self.amostras.append(janela)
            except Exception:
                pass

    def __len__(self) -> int:
        return len(self.amostras)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        seq = self.amostras[idx]
        if len(seq) < self.seq_len + 1:
            seq = seq + [self.pad_id] * (self.seq_len + 1 - len(seq))
        else:
            seq = seq[: self.seq_len + 1]

        x = torch.tensor(seq[:-1], dtype=torch.long)
        y = torch.tensor(seq[1:], dtype=torch.long)
        return x, y


def treinar(args):
    device = torch.device("cuda" if torch.cuda.is_available() and args.device == "cuda" else "cpu")
    print(f"Utilizando dispositivo: {device}")

    caminho_vocab = RAIZ / "dados_processados" / "sequencias" / "vocabulario.json"
    if not caminho_vocab.exists():
        print(f"ERRO: Arquivo de vocabulário não encontrado em {caminho_vocab}")
        return

    vocab_data = json.loads(caminho_vocab.read_text(encoding="utf-8"))
    token_para_id = vocab_data["token_para_id"]
    id_para_token = vocab_data["id_para_token"]
    vocab_size = len(token_para_id)
    print(f"Tamanho do vocabulário: {vocab_size}")

    pasta_treino = RAIZ / "dados_processados" / "treino"
    pasta_val = RAIZ / "dados_processados" / "validacao"

    ds_treino = DatasetSequenciasMusicais(pasta_treino, token_para_id, seq_len=args.seq_len)
    ds_val = DatasetSequenciasMusicais(pasta_val, token_para_id, seq_len=args.seq_len)

    dl_treino = DataLoader(ds_treino, batch_size=args.batch_size, shuffle=True, drop_last=True)
    dl_val = DataLoader(ds_val, batch_size=args.batch_size, shuffle=False)

    print(f"Amostras de treino: {len(ds_treino):,} | Amostras de validação: {len(ds_val):,}")

    if args.modelo == "transformer":
        modelo = MusicTransformer(
            vocab_size=vocab_size,
            d_model=args.d_model,
            nhead=args.nhead,
            num_layers=args.num_layers,
            dim_feedforward=args.d_ff,
            dropout=0.1,
            max_seq_len=args.seq_len,
        ).to(device)
        caminho_salvar = RAIZ / "modelos" / "modelo_transformer.pt"
    else:
        modelo = MelodyLSTM(
            vocab_size=vocab_size,
            embed_dim=args.d_model,
            hidden_dim=args.d_ff,
            num_layers=args.num_layers,
            dropout=0.2,
        ).to(device)
        caminho_salvar = RAIZ / "modelos" / "modelo_lstm.pt"

    criterio = nn.CrossEntropyLoss(ignore_index=token_para_id.get("<PAD>", 0))
    otimizador = torch.optim.AdamW(modelo.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(otimizador, T_max=args.epochs)

    print(f"\nIniciando treinamento ({args.modelo.upper()}) por {args.epochs} épocas...")
    melhor_val_loss = float("inf")

    for epoca in range(1, args.epochs + 1):
        inicio_ep = time.time()
        modelo.train()
        total_loss = 0.0

        pbar = tqdm(dl_treino, desc=f"Época {epoca}/{args.epochs} [Treino]")
        for x, y in pbar:
            x, y = x.to(device), y.to(device)
            otimizador.zero_grad()

            if args.modelo == "transformer":
                logits = modelo(x)
            else:
                logits, _ = modelo(x)

            loss = criterio(logits.view(-1, vocab_size), y.view(-1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
            otimizador.step()

            total_loss += loss.item()
            pbar.set_postfix({"loss": f"{loss.item():.4f}"})

        scheduler.step()
        media_treino_loss = total_loss / len(dl_treino)

        # Validação
        modelo.eval()
        val_loss = 0.0
        with torch.no_grad():
            for x, y in dl_val:
                x, y = x.to(device), y.to(device)
                if args.modelo == "transformer":
                    logits = modelo(x)
                else:
                    logits, _ = modelo(x)
                l = criterio(logits.view(-1, vocab_size), y.view(-1))
                val_loss += l.item()

        media_val_loss = val_loss / max(1, len(dl_val))
        dur_ep = time.time() - inicio_ep

        print(f"Época {epoca:02d} | Treino Loss: {media_treino_loss:.4f} | Val Loss: {media_val_loss:.4f} | Tempo: {dur_ep:.1f}s")

        if media_val_loss < melhor_val_loss:
            melhor_val_loss = media_val_loss
            modelo.salvar(caminho_salvar)
            print(f"  ★ Melhor modelo salvo em: {caminho_salvar.relative_to(RAIZ)}")

    print("\nTreinamento Concluído!")
    print(f"Testando geração do modelo treinado:")
    amostra = modelo.gerar(
        token_para_id=token_para_id,
        id_para_token=id_para_token,
        num_tokens=30,
        temperatura=0.85,
        device=str(device),
    )
    print(f"Tokens gerados: {amostra[:12]}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Treinamento de Redes Neurais para Música")
    parser.add_argument("--modelo", type=str, default="transformer", choices=["transformer", "lstm"])
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seq_len", type=int, default=128)
    parser.add_argument("--d_model", type=int, default=256)
    parser.add_argument("--d_ff", type=int, default=512)
    parser.add_argument("--nhead", type=int, default=4)
    parser.add_argument("--num_layers", type=int, default=4)
    parser.add_argument("--device", type=str, default="cuda")

    args = parser.parse_args()
    treinar(args)
