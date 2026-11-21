"""
avaliar_transformer.py
Avalia o MusicTransformer treinado (modelos/modelo_transformer.pt) nos conjuntos
de treino, validação e teste.

A tarefa do modelo é prever o próximo token (classificação multiclasse sobre o
vocabulário). Para cada conjunto são reportadas: perda (cross-entropy),
perplexidade, acurácia, acurácia top-5, precisão, recall, F1-Score (macro) e
AUC-ROC (macro, one-vs-rest). A matriz de confusão de cada conjunto é salva em CSV.

Uso:
    python scripts/avaliar_transformer.py
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from torch.utils.data import DataLoader

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

from treinar_neural import DatasetSequenciasMusicais  # noqa: E402
from src.modelos.transformer_model import MusicTransformer  # noqa: E402

SEMENTE = 42
SEQ_LEN = 128
BATCH_SIZE = 32
FRACAO_AMOSTRA_AUC = 0.05  # fração dos tokens-alvo usada no cálculo da AUC-ROC (limita memória)


def avaliar_conjunto(modelo, dataloader, pad_id, vocab_size, rng):
    criterio = nn.CrossEntropyLoss(ignore_index=pad_id, reduction="sum")
    perda_total = 0.0
    n_tokens = 0
    y_real, y_previsto, top5_acertos = [], [], []
    y_amostra, probs_amostra = [], []

    modelo.eval()
    with torch.no_grad():
        for x, y in dataloader:
            logits = modelo(x).reshape(-1, vocab_size)
            alvo = y.reshape(-1)

            mascara = alvo != pad_id
            logits = logits[mascara]
            alvo = alvo[mascara]
            if alvo.numel() == 0:
                continue

            perda_total += criterio(logits, alvo).item()
            n_tokens += alvo.numel()

            probs = torch.softmax(logits, dim=1)
            previsto = probs.argmax(dim=1)
            top5 = probs.topk(5, dim=1).indices
            top5_acertos.append((top5 == alvo.unsqueeze(1)).any(dim=1).numpy())

            y_real.append(alvo.numpy())
            y_previsto.append(previsto.numpy())

            escolha = rng.random(alvo.numel()) < FRACAO_AMOSTRA_AUC
            if escolha.any():
                y_amostra.append(alvo.numpy()[escolha])
                probs_amostra.append(probs.numpy()[escolha])

    y_real = np.concatenate(y_real)
    y_previsto = np.concatenate(y_previsto)
    top5_acertos = np.concatenate(top5_acertos)
    y_amostra = np.concatenate(y_amostra)
    probs_amostra = np.concatenate(probs_amostra)

    precisao, recall, f1, _ = precision_recall_fscore_support(
        y_real, y_previsto, average="macro", zero_division=0
    )

    aucs = []
    for classe in np.unique(y_amostra):
        positivos = y_amostra == classe
        if positivos.all():
            continue
        aucs.append(roc_auc_score(positivos, probs_amostra[:, classe]))

    perda_media = perda_total / n_tokens
    matriz = confusion_matrix(y_real, y_previsto, labels=np.arange(vocab_size))

    metricas = {
        "tokens_avaliados": int(n_tokens),
        "perda_cross_entropy": round(perda_media, 4),
        "perplexidade": round(math.exp(perda_media), 4),
        "acuracia": round(accuracy_score(y_real, y_previsto), 4),
        "acuracia_top5": round(float(top5_acertos.mean()), 4),
        "precisao_macro": round(float(precisao), 4),
        "recall_macro": round(float(recall), 4),
        "f1_macro": round(float(f1), 4),
        "auc_roc_macro_ovr": round(float(np.mean(aucs)), 4),
        "classes_com_auc": len(aucs),
        "tokens_amostra_auc": int(y_amostra.shape[0]),
    }
    return metricas, matriz


def main():
    torch.manual_seed(SEMENTE)
    rng = np.random.default_rng(SEMENTE)

    caminho_vocab = RAIZ / "modelos" / "vocabulario.json"
    vocab = json.loads(caminho_vocab.read_text(encoding="utf-8"))
    token_para_id = vocab["token_para_id"]
    vocab_size = len(token_para_id)
    pad_id = token_para_id["<PAD>"]

    modelo = MusicTransformer.carregar(RAIZ / "modelos" / "modelo_transformer.pt")

    conjuntos = {
        "treino": RAIZ / "dados_processados" / "treino",
        "validacao": RAIZ / "dados_processados" / "validacao",
        "teste": RAIZ / "dados_processados" / "teste",
    }

    resultados = {"vocabulario_tamanho": vocab_size, "seq_len": SEQ_LEN}
    for nome, pasta in conjuntos.items():
        dataset = DatasetSequenciasMusicais(pasta, token_para_id, seq_len=SEQ_LEN)
        loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False)
        print(f"Avaliando {nome}: {len(dataset):,} janelas")
        metricas, matriz = avaliar_conjunto(modelo, loader, pad_id, vocab_size, rng)
        metricas["janelas"] = len(dataset)
        resultados[nome] = metricas
        print(json.dumps(metricas, ensure_ascii=False, indent=2))

        caminho_matriz = RAIZ / "relatorios" / f"matriz_confusao_transformer_{nome}.csv"
        np.savetxt(caminho_matriz, matriz, fmt="%d", delimiter=",")

    caminho_saida = RAIZ / "relatorios" / "metricas_transformer.json"
    caminho_saida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nMétricas salvas em {caminho_saida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
