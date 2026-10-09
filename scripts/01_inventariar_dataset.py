"""
Script 01 — Inventariar o dataset
Percorre todos os MIDIs e registra metadados básicos sem nenhuma filtragem.
"""

import json
import csv
from pathlib import Path

import pretty_midi
import yaml
from tqdm import tqdm


def carregar_config():
    raiz = Path(__file__).resolve().parent.parent
    with open(raiz / "configuracao" / "pipeline.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f), raiz


def carregar_md5_map(arquivo_md5):
    if arquivo_md5.exists():
        with open(arquivo_md5, encoding="utf-8") as f:
            return json.load(f)
    return {}


def analisar_midi(caminho, raiz, md5_map):
    md5 = caminho.stem
    nome_original = ""
    if md5 in md5_map:
        nomes = md5_map[md5]
        nome_original = "; ".join(nomes) if isinstance(nomes, list) else str(nomes)

    registro = {
        "caminho_relativo": str(caminho.relative_to(raiz)),
        "md5": md5,
        "nome_original": nome_original,
        "tamanho_bytes": caminho.stat().st_size,
        "abre_sem_erro": False,
        "erro_leitura": "",
        "duracao_seg": 0.0,
        "num_faixas": 0,
        "num_instrumentos": 0,
        "tem_bateria": False,
        "num_notas_total": 0,
        "bpm_predominante": 0.0,
        "num_mudancas_tempo": 0,
        "faixas_info": "[]",
    }

    try:
        midi = pretty_midi.PrettyMIDI(str(caminho))

        registro["abre_sem_erro"] = True
        registro["duracao_seg"] = round(midi.get_end_time(), 3)
        registro["num_faixas"] = len(midi.instruments)

        programas_unicos = set()
        tem_bateria = False
        num_notas_total = 0
        faixas_info = []

        for instrumento in midi.instruments:
            programas_unicos.add(int(instrumento.program))
            if instrumento.is_drum:
                tem_bateria = True
            num_notas_total += len(instrumento.notes)
            faixas_info.append({
                "nome": instrumento.name,
                "programa": int(instrumento.program),
                "is_drum": bool(instrumento.is_drum),
                "num_notas": int(len(instrumento.notes)),
            })

        registro["num_instrumentos"] = len(programas_unicos)
        registro["tem_bateria"] = tem_bateria
        registro["num_notas_total"] = num_notas_total
        registro["faixas_info"] = json.dumps(faixas_info, ensure_ascii=False)

        # BPM e mudanças de tempo
        tempos = midi.get_tempo_changes()
        if len(tempos[1]) > 0:
            registro["bpm_predominante"] = round(float(tempos[1][0]), 2)
            registro["num_mudancas_tempo"] = len(tempos[1])
        else:
            registro["bpm_predominante"] = 120.0
            registro["num_mudancas_tempo"] = 0

    except Exception as e:
        registro["abre_sem_erro"] = False
        registro["erro_leitura"] = str(e)[:300]

    return registro


def main():
    cfg, raiz = carregar_config()
    pasta_lmd = raiz / cfg["dataset"]["pasta_lmd_full"]
    arquivo_md5 = raiz / cfg["dataset"]["arquivo_md5_json"]
    extensoes = tuple(cfg["dataset"]["extensoes"])
    pasta_relatorios = raiz / cfg["saidas"]["pasta_relatorios"]
    pasta_relatorios.mkdir(parents=True, exist_ok=True)

    piloto_ativo = cfg["piloto"]["ativo"]
    piloto_qtd = cfg["piloto"]["quantidade"]

    md5_map = carregar_md5_map(arquivo_md5)
    print(f"md5_map carregado: {len(md5_map)} entradas")

    todos_midis = sorted(p for p in pasta_lmd.rglob("*") if p.suffix.lower() in extensoes)

    if piloto_ativo:
        todos_midis = todos_midis[:piloto_qtd]
        print(f"[PILOTO] Processando {len(todos_midis)} arquivos.")
    else:
        print(f"Processando {len(todos_midis)} arquivos.")

    campos = [
        "caminho_relativo", "md5", "nome_original", "tamanho_bytes",
        "abre_sem_erro", "erro_leitura", "duracao_seg", "num_faixas",
        "num_instrumentos", "tem_bateria", "num_notas_total",
        "bpm_predominante", "num_mudancas_tempo", "faixas_info",
    ]

    caminho_csv = pasta_relatorios / "inventario.csv"
    with open(caminho_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()

        for caminho in tqdm(todos_midis, desc="Inventariando"):
            registro = analisar_midi(caminho, raiz, md5_map)
            writer.writerow(registro)

    print(f"\nInventário salvo em: {caminho_csv.relative_to(raiz)}")
    print(f"Total de registros: {len(todos_midis)}")


if __name__ == "__main__":
    main()
