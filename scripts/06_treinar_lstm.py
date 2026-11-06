"""
Script 06 — Treinar a LSTM de melodias.

Lê as sequências JSONL de treino e validação, corta em janelas de 128 tokens
e salva o melhor modelo em modelos/lstm_melodia.pt.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import yaml
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from modelo.rede import MelodiaLSTM, gerar


def carregar_config():
    with open(RAIZ / "configuracao" / "pipeline.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def carregar_vocabulario(pasta_sequencias):
    caminho = pasta_sequencias / "vocabulario.json"
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return dados["token_para_id"], dados["id_para_token"]


def ler_sequencias(caminho_jsonl, token_para_id):
    inicio = token_para_id["<START>"]
    fim = token_para_id["<END>"]
    sequencias = []
    with open(caminho_jsonl, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            tokens = json.loads(linha).get("tokens") or []
            if not tokens:
                continue
            ids = [inicio]
            ids.extend(token_para_id[tok] for tok in tokens)
            ids.append(fim)
            sequencias.append(ids)
    return sequencias


def inicios_janela(comprimento, janela, passo):
    if comprimento < 2:
        return
    inicio = 0
    while inicio < comprimento - 1:
        yield inicio
        if inicio + janela >= comprimento - 1:
            break
        inicio += passo


def montar_janelas(sequencias, janela, passo, pad_id):
    total = sum(1 for seq in sequencias for _ in inicios_janela(len(seq), janela, passo))
    entradas = np.full((total, janela), pad_id, dtype=np.int64)
    alvos = np.full((total, janela), pad_id, dtype=np.int64)
    i = 0
    for seq in sequencias:
        arr = np.asarray(seq, dtype=np.int64)
        for inicio in inicios_janela(len(arr), janela, passo):
            trecho = arr[inicio: inicio + janela + 1]
            n = len(trecho) - 1
            entradas[i, :n] = trecho[:n]
            alvos[i, :n] = trecho[1:]
            i += 1
    return torch.from_numpy(entradas), torch.from_numpy(alvos)


def avaliar(modelo, loader, criterio, dispositivo):
    modelo.eval()
    soma = 0.0
    n = 0
    with torch.no_grad():
        for x, y in loader:
            x = x.to(dispositivo, non_blocking=True)
            y = y.to(dispositivo, non_blocking=True)
            logits, _ = modelo(x)
            perda = criterio(logits.reshape(-1, logits.size(-1)), y.reshape(-1))
            soma += float(perda.item()) * x.size(0)
            n += x.size(0)
    return soma / n if n else 0.0


def main():
    cfg = carregar_config()
    mcfg = cfg["modelo"]
    saidas = cfg["saidas"]

    semente = int(mcfg["semente"])
    torch.manual_seed(semente)
    np.random.seed(semente)

    dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if dispositivo.type == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        print(f"Dispositivo: {torch.cuda.get_device_name(0)}")
    else:
        print("Dispositivo: CPU")

    pasta_sequencias = RAIZ / saidas["pasta_sequencias"]
    token_para_id, id_para_token = carregar_vocabulario(pasta_sequencias)
    pad_id = token_para_id["<PAD>"]
    vocab = len(token_para_id)
    janela = int(mcfg["janela"])
    passo = int(mcfg["passo"])

    print("Lendo sequências...")
    treino_seq = ler_sequencias(RAIZ / saidas["pasta_treino"] / "sequencias.jsonl", token_para_id)
    val_seq = ler_sequencias(RAIZ / saidas["pasta_validacao"] / "sequencias.jsonl", token_para_id)
    print(f"Treino: {len(treino_seq)}  Validação: {len(val_seq)}  Vocabulário: {vocab}")

    print("Montando janelas...")
    x_tr, y_tr = montar_janelas(treino_seq, janela, passo, pad_id)
    x_va, y_va = montar_janelas(val_seq, janela, passo, pad_id)
    print(f"Janelas de treino: {len(x_tr):,}  Janelas de validação: {len(x_va):,}")

    lote = int(mcfg["lote"])
    loader_tr = DataLoader(
        TensorDataset(x_tr, y_tr),
        batch_size=lote,
        shuffle=True,
        pin_memory=dispositivo.type == "cuda",
    )
    loader_va = DataLoader(
        TensorDataset(x_va, y_va),
        batch_size=lote,
        shuffle=False,
        pin_memory=dispositivo.type == "cuda",
    )

    modelo = MelodiaLSTM(
        vocabulario=vocab,
        embedding=int(mcfg["embedding"]),
        oculto=int(mcfg["oculto"]),
        camadas=int(mcfg["camadas"]),
        dropout=float(mcfg["dropout"]),
        pad_id=pad_id,
    ).to(dispositivo)
    n_params = sum(p.numel() for p in modelo.parameters())
    print(f"Parâmetros: {n_params:,}")

    criterio = nn.CrossEntropyLoss(ignore_index=pad_id)
    otimizador = torch.optim.AdamW(modelo.parameters(), lr=float(mcfg["taxa_aprendizado"]), weight_decay=0.01)

    epocas = int(mcfg["epocas"])
    paciencia = int(mcfg["paciencia"])
    melhor = float("inf")
    sem_melhora = 0
    historico = []
    pasta_modelos = RAIZ / "modelos"
    pasta_modelos.mkdir(parents=True, exist_ok=True)
    caminho_modelo = pasta_modelos / "lstm_melodia.pt"

    for epoca in range(1, epocas + 1):
        modelo.train()
        inicio = time.perf_counter()
        soma = 0.0
        n = 0
        for x, y in loader_tr:
            x = x.to(dispositivo, non_blocking=True)
            y = y.to(dispositivo, non_blocking=True)
            otimizador.zero_grad(set_to_none=True)
            logits, _ = modelo(x)
            perda = criterio(logits.reshape(-1, vocab), y.reshape(-1))
            perda.backward()
            nn.utils.clip_grad_norm_(modelo.parameters(), 1.0)
            otimizador.step()
            soma += float(perda.item()) * x.size(0)
            n += x.size(0)

        perda_treino = soma / n
        perda_val = avaliar(modelo, loader_va, criterio, dispositivo)
        duracao = time.perf_counter() - inicio
        historico.append({
            "epoca": epoca,
            "treino": round(perda_treino, 4),
            "validacao": round(perda_val, 4),
            "segundos": round(duracao, 1),
        })
        print(
            f"Época {epoca}/{epocas}  treino {perda_treino:.4f}  validação {perda_val:.4f}  {duracao:.1f}s",
            flush=True,
        )

        if perda_val < melhor - 1e-4:
            melhor = perda_val
            sem_melhora = 0
            torch.save(
                {
                    "state_dict": modelo.state_dict(),
                    "config": mcfg,
                    "token_para_id": token_para_id,
                    "id_para_token": id_para_token,
                    "perda_validacao": round(melhor, 4),
                    "epoca": epoca,
                },
                caminho_modelo,
            )
        else:
            sem_melhora += 1
            if sem_melhora >= paciencia:
                print(f"Parada antecipada na época {epoca}. Melhor validação: {melhor:.4f}")
                break

    caminho_hist = pasta_modelos / "historico_lstm.json"
    caminho_hist.write_text(
        json.dumps({"melhor_validacao": round(melhor, 4), "epocas": historico}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    checkpoint = torch.load(caminho_modelo, map_location=dispositivo, weights_only=False)
    modelo.load_state_dict(checkpoint["state_dict"])
    amostra = gerar(
        modelo, token_para_id, id_para_token,
        num_tokens=24, temperatura=0.9, dispositivo=dispositivo,
    )
    print(f"\nModelo salvo em: {caminho_modelo.relative_to(RAIZ)}")
    print(f"Melhor validação: {melhor:.4f} (época {checkpoint['epoca']})")
    print("Amostra:", " ".join(amostra))


if __name__ == "__main__":
    main()
