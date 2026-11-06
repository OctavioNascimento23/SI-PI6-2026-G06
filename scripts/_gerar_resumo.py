"""Gera relatorios/resumo_limpeza.md com os números atuais do pipeline."""

import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path

import yaml

raiz = Path(__file__).resolve().parent.parent


def pct(valor, total):
    return f"{100 * valor / total:.1f}%" if total else "0%"


def contar_csv(caminho):
    if not caminho.exists():
        return 0
    with open(caminho, encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))


def main():
    rejeitados = Counter()
    caminho_rej = raiz / "relatorios" / "arquivos_rejeitados.csv"
    if caminho_rej.exists():
        with open(caminho_rej, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                rejeitados[row["motivo_rejeicao"]] += 1

    total = contar_csv(raiz / "relatorios" / "inventario.csv")
    aprovados = contar_csv(raiz / "relatorios" / "aprovados.csv")
    recorte = contar_csv(raiz / "relatorios" / "recorte.csv")

    extracao = Counter()
    caminho_estado = raiz / "relatorios" / "extracao_vistos.csv"
    if caminho_estado.exists():
        with open(caminho_estado, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                extracao[row["status"]] += 1

    melodias = contar_csv(raiz / "relatorios" / "melodias_selecionadas.csv")

    jsonl = raiz / "dados_processados" / "sequencias" / "sequencias.jsonl"
    total_seq = 0
    total_tokens = 0
    if jsonl.exists():
        with open(jsonl, encoding="utf-8") as f:
            for linha in f:
                if not linha.strip():
                    continue
                registro = json.loads(linha)
                total_seq += 1
                total_tokens += len(registro.get("tokens", []))
    media = total_tokens / total_seq if total_seq else 0

    vocab_path = raiz / "dados_processados" / "sequencias" / "vocabulario.json"
    tam_vocab = 0
    if vocab_path.exists():
        tam_vocab = json.loads(vocab_path.read_text(encoding="utf-8"))["tamanho_vocabulario"]

    div_path = raiz / "relatorios" / "divisao_dataset.json"
    div = {"treino": 0, "validacao": 0, "teste": 0, "total_sequencias": 0, "semente": 42}
    if div_path.exists():
        div = json.loads(div_path.read_text(encoding="utf-8"))

    cfg = (raiz / "configuracao" / "pipeline.yaml").read_text(encoding="utf-8")
    corrompidos = rejeitados["CORROMPIDO"]
    sem_notas = rejeitados["SEM_NOTAS"]
    curtos = rejeitados["MUITO_CURTO"]
    longos = rejeitados["MUITO_LONGO"]
    minimo = rejeitados["ARQUIVO_MINIMO"]

    linhas = [
        "# Relatório de Limpeza — LMD-full — Projeto B6",
        "",
        f"**Data de execução:** {date.today().isoformat()}",
        f"**Modo:** Inventário de {total} arquivos; recorte de treino com {recorte} MIDIs",
        "",
        "## Números gerais",
        f"- Total de arquivos no LMD-full analisados: {total}",
        f"- Arquivos corrompidos ou inválidos: {corrompidos} ({pct(corrompidos, total)})",
        f"- Arquivos sem notas: {sem_notas} ({pct(sem_notas, total)})",
        f"- Arquivos muito curtos (< 15s): {curtos} ({pct(curtos, total)})",
        f"- Arquivos muito longos (> 600s): {longos} ({pct(longos, total)})",
        f"- Arquivos abaixo do tamanho mínimo (< 200 bytes): {minimo} ({pct(minimo, total)})",
        f"- MIDIs aprovados na validação: {aprovados} ({pct(aprovados, total)})",
        f"- MIDIs no recorte de treino: {recorte}",
        "",
        "## Extração de melodias",
        f"- MIDIs sem faixa melódica válida: {extracao['sem_faixa']}",
        f"- MIDIs descartados por filtros de qualidade: {extracao['filtro']}",
        f"- Erros de leitura na extração: {extracao['erro']}",
        f"- Melodias monofônicas extraídas: {melodias}",
        "",
        "## Tokenização",
        f"- Sequências geradas: {total_seq}",
        f"- Tamanho médio das sequências (tokens): {media:.1f}",
        f"- Tamanho do vocabulário: {tam_vocab}",
        "",
        "## Divisão do dataset",
        f"- Treino: {div['treino']} sequências ({pct(div['treino'], div['total_sequencias'])})",
        f"- Validação: {div['validacao']} sequências ({pct(div['validacao'], div['total_sequencias'])})",
        f"- Teste: {div['teste']} sequências ({pct(div['teste'], div['total_sequencias'])})",
        "",
        "## Parâmetros utilizados",
        "",
        "```yaml",
        cfg.rstrip(),
        "```",
        "",
        "## Observações",
        "- O inventário percorre o LMD-full e pode ser retomado se a execução parar.",
        "- Os MIDIs aprovados não são copiados. A extração lê o arquivo original em arquivos_brutos.",
        "- O recorte de treino é uma amostra estratificada por pasta do hash, com semente 42.",
        "- Cada melodia é transposta para Dó maior ou Lá menor antes da tokenização.",
        "- As sequências ficam em JSONL, um arquivo por conjunto, sem um JSON por música.",
        f"- Semente da divisão: {div.get('semente', 42)}.",
        "",
    ]

    saida = raiz / "relatorios" / "resumo_limpeza.md"
    saida.write_text("\n".join(linhas), encoding="utf-8")
    print(f"Gerado: {saida.relative_to(raiz)}")


if __name__ == "__main__":
    main()
