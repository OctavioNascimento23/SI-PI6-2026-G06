"""Funções compartilhadas do pipeline de melodias."""

import csv
import warnings
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message="Tempo, Key or Time signature change events found on non-zero tracks.*",
    category=RuntimeWarning,
)

import numpy as np
import pretty_midi
import yaml

PERFIL_MAIOR = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
)
PERFIL_MENOR = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
)
NOMES_PITCH = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
LIMIAR_SIMULTANEO = 0.05


def carregar_config():
    raiz = Path(__file__).resolve().parent.parent
    with open(raiz / "configuracao" / "pipeline.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f), raiz


def aplicar_smoke(cfg, smoke):
    """Redireciona saídas para pastas de teste, sem mexer no inventário real."""
    if not smoke:
        return cfg
    cfg["saidas"] = dict(cfg["saidas"])
    cfg["saidas"]["pasta_midi_validos"] = "dados_processados/smoke/midi_validos"
    cfg["saidas"]["pasta_melodias"] = "dados_processados/smoke/melodias_extraidas"
    cfg["saidas"]["pasta_sequencias"] = "dados_processados/smoke/sequencias"
    cfg["saidas"]["pasta_treino"] = "dados_processados/smoke/treino"
    cfg["saidas"]["pasta_validacao"] = "dados_processados/smoke/validacao"
    cfg["saidas"]["pasta_teste"] = "dados_processados/smoke/teste"
    cfg["saidas"]["pasta_relatorios"] = "relatorios/smoke"
    return cfg


def primeiro_nome(md5_map, md5):
    nomes = md5_map.get(md5) if md5_map else None
    if not nomes:
        return ""
    if isinstance(nomes, list):
        texto = "; ".join(str(n) for n in nomes[:3])
    else:
        texto = str(nomes)
    return texto[:300]


def carregar_md5_map(caminho):
    import json

    if not caminho.exists():
        return {}
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def garantir_csv_integro(caminho: Path):
    if not caminho.exists() or caminho.stat().st_size == 0:
        return
    dados = caminho.read_bytes()
    if dados.endswith(b"\n"):
        return
    corte = dados.rfind(b"\n")
    caminho.write_bytes(dados[: corte + 1] if corte >= 0 else b"")


def md5s_no_csv(caminho: Path, coluna="md5"):
    if not caminho.exists() or caminho.stat().st_size == 0:
        return set()
    garantir_csv_integro(caminho)
    vistos = set()
    with open(caminho, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or coluna not in reader.fieldnames:
            return set()
        for row in reader:
            valor = (row.get(coluna) or "").strip()
            if valor:
                vistos.add(valor)
    return vistos


def abrir_csv(caminho: Path, campos, retomada: bool):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    garantir_csv_integro(caminho)
    existe = caminho.exists() and caminho.stat().st_size > 0
    modo = "a" if retomada and existe else "w"
    arquivo = open(caminho, modo, encoding="utf-8", newline="")
    writer = csv.DictWriter(arquivo, fieldnames=campos, extrasaction="ignore")
    if modo == "w":
        writer.writeheader()
    return arquivo, writer


def executar_pool(funcao, itens, trabalhadores, inicializador=None, initargs=()):
    """Executa funcao em paralelo e devolve resultados conforme ficam prontos."""
    itens = iter(itens)
    trabalhadores = max(1, int(trabalhadores))
    if trabalhadores == 1:
        for item in itens:
            yield funcao(item)
        return

    max_em_voo = trabalhadores * 4
    with ProcessPoolExecutor(
        max_workers=trabalhadores,
        initializer=inicializador,
        initargs=initargs,
    ) as executor:
        em_voo = set()

        def enviar():
            try:
                em_voo.add(executor.submit(funcao, next(itens)))
                return True
            except StopIteration:
                return False

        for _ in range(max_em_voo):
            if not enviar():
                break

        while em_voo:
            prontos, em_voo = wait(em_voo, return_when=FIRST_COMPLETED)
            for futuro in prontos:
                yield futuro.result()
                enviar()


def nome_instrumento(programa, nome_faixa):
    if nome_faixa and str(nome_faixa).strip():
        return str(nome_faixa).strip()
    try:
        return pretty_midi.program_to_instrument_name(int(programa))
    except Exception:
        return f"program_{programa}"


def _correlacao(a, b):
    a = a - a.mean()
    b = b - b.mean()
    denom = float(np.sqrt((a * a).sum() * (b * b).sum()))
    if denom < 1e-9:
        return 0.0
    return float((a * b).sum() / denom)


def detectar_tonalidade(notas):
    """Estima o tom e devolve (nome, modo, semitons até Dó maior ou Lá menor)."""
    hist = np.zeros(12, dtype=np.float64)
    for nota in notas:
        hist[int(nota.pitch) % 12] += max(float(nota.end) - float(nota.start), 0.05)

    melhor_corr = -2.0
    tonica = 0
    modo = "maior"
    for nome_modo, perfil in (("maior", PERFIL_MAIOR), ("menor", PERFIL_MENOR)):
        for shift in range(12):
            rotacionado = np.array([perfil[(i - shift) % 12] for i in range(12)])
            corr = _correlacao(hist, rotacionado)
            if corr > melhor_corr:
                melhor_corr = corr
                tonica = shift
                modo = nome_modo

    destino = 0 if modo == "maior" else 9
    semitons = (destino - tonica) % 12
    if semitons > 6:
        semitons -= 12
    nome = NOMES_PITCH[tonica] if modo == "maior" else f"{NOMES_PITCH[tonica]}m"
    return nome, modo, int(semitons)


def transpor_notas(notas, semitons, pitch_min, pitch_max):
    for nota in notas:
        novo = int(nota.pitch) + int(semitons)
        while novo > pitch_max:
            novo -= 12
        while novo < pitch_min:
            novo += 12
        nota.pitch = int(novo)
    return notas


def quantizar(duracao_beats, grades):
    grades_arr = np.asarray(grades, dtype=np.float64)
    idx = int(np.argmin(np.abs(grades_arr - duracao_beats)))
    return float(grades_arr[idx])


def formatar_grade(valor):
    return f"{float(valor):.2f}"


def tokenizar_notas(notas, bpm, grades):
    if not notas:
        return []
    beats_por_segundo = float(bpm) / 60.0
    tokens = []
    notas_ord = sorted(notas, key=lambda n: n.start)
    for i, nota in enumerate(notas_ord):
        if i > 0:
            gap = nota.start - notas_ord[i - 1].end
            if gap > 0.01:
                grade = quantizar(gap * beats_por_segundo, grades)
                tokens.append(f"REST_{formatar_grade(grade)}")
        duracao_beats = max(nota.end - nota.start, 0.0) * beats_por_segundo
        grade = quantizar(duracao_beats, grades)
        tokens.append(f"NOTE_{int(nota.pitch)}")
        tokens.append(f"DURATION_{formatar_grade(grade)}")
    return tokens


def calcular_pontuacao(instrumento):
    notas = instrumento.notes
    if not notas:
        return -1.0, {}

    num_notas = len(notas)
    pitches = [n.pitch for n in notas]
    pitch_medio = float(np.mean(pitches))
    variacao_pitch = float(np.std(pitches))

    notas_ord = sorted(notas, key=lambda n: n.start)
    sobrepostos = 0
    for i in range(1, len(notas_ord)):
        if notas_ord[i].start < notas_ord[i - 1].end - 0.001:
            sobrepostos += 1
    pct_polifonia = sobrepostos / num_notas if num_notas else 0.0

    duracao_total = notas_ord[-1].end - notas_ord[0].start
    tempo_com_nota = sum(n.end - n.start for n in notas_ord)
    pct_pausas = max(0.0, 1.0 - (tempo_com_nota / duracao_total)) if duracao_total > 0 else 1.0

    norm_notas = min(num_notas / 500.0, 1.0)
    norm_registro = min(max((pitch_medio - 36) / 60.0, 0.0), 1.0)
    norm_var = min(variacao_pitch / 12.0, 1.0)

    pontuacao = (
        0.3 * norm_notas
        + 0.2 * norm_registro
        + 0.3 * norm_var
        - 0.1 * pct_polifonia
        - 0.1 * pct_pausas
    )
    detalhes = {
        "num_notas": num_notas,
        "pitch_medio": round(pitch_medio, 2),
        "variacao_pitch": round(variacao_pitch, 2),
        "pct_polifonia": round(pct_polifonia, 4),
        "pct_pausas": round(pct_pausas, 4),
        "pontuacao": round(pontuacao, 6),
    }
    return pontuacao, detalhes


def converter_monofonia(notas, regra):
    if not notas:
        return []
    notas_ord = sorted(notas, key=lambda n: (n.start, -n.pitch))
    resultado = []
    grupo = [notas_ord[0]]
    for nota in notas_ord[1:]:
        if nota.start - grupo[0].start < LIMIAR_SIMULTANEO:
            grupo.append(nota)
        else:
            resultado.append(_escolher_nota(grupo, regra))
            grupo = [nota]
    if grupo:
        resultado.append(_escolher_nota(grupo, regra))
    return resultado


def _escolher_nota(grupo, regra):
    if regra == "maior_duracao":
        return max(grupo, key=lambda n: (n.end - n.start, n.pitch))
    return max(grupo, key=lambda n: (n.pitch, n.end - n.start))


def aplicar_filtros_finais(notas, filtros):
    if not notas:
        return [], "SEM_NOTAS_APOS_MONOFONIA"

    pitch_min = filtros["pitch_minimo"]
    pitch_max = filtros["pitch_maximo"]
    fora = [n for n in notas if not (pitch_min <= n.pitch <= pitch_max)]
    if notas and len(fora) / len(notas) > 0.05:
        notas = [n for n in notas if pitch_min <= n.pitch <= pitch_max]

    if len(notas) < filtros["notas_minimas"]:
        return [], f"NOTAS_INSUFICIENTES_APOS_FILTRO ({len(notas)})"
    if len(notas) > filtros["notas_maximas"]:
        return [], f"NOTAS_EXCESSIVAS ({len(notas)})"

    contagem = {}
    for nota in notas:
        contagem[nota.pitch] = contagem.get(nota.pitch, 0) + 1
    top2 = sum(sorted(contagem.values(), reverse=True)[:2])
    if top2 / len(notas) > 0.80:
        return [], "MELODIA_PLANA"
    return notas, None


def analisar_midi(args):
    """Lê um MIDI e devolve o registro do inventário. Não consulta o mapa MD5."""
    caminho_str, raiz_str = args
    caminho = Path(caminho_str)
    raiz = Path(raiz_str)
    registro = {
        "caminho_relativo": str(caminho.relative_to(raiz)),
        "md5": caminho.stem,
        "nome_original": "",
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
        import json

        midi = pretty_midi.PrettyMIDI(str(caminho))
        registro["abre_sem_erro"] = True
        registro["duracao_seg"] = round(float(midi.get_end_time()), 3)
        registro["num_faixas"] = len(midi.instruments)

        programas = set()
        tem_bateria = False
        num_notas = 0
        faixas = []
        for instrumento in midi.instruments:
            programas.add(int(instrumento.program))
            if instrumento.is_drum:
                tem_bateria = True
            num_notas += len(instrumento.notes)
            faixas.append({
                "nome": instrumento.name or "",
                "programa": int(instrumento.program),
                "is_drum": bool(instrumento.is_drum),
                "num_notas": int(len(instrumento.notes)),
            })
        registro["num_instrumentos"] = len(programas)
        registro["tem_bateria"] = tem_bateria
        registro["num_notas_total"] = num_notas
        registro["faixas_info"] = json.dumps(faixas, ensure_ascii=False)

        tempos = midi.get_tempo_changes()
        if len(tempos[1]) > 0:
            registro["bpm_predominante"] = round(float(tempos[1][0]), 2)
            registro["num_mudancas_tempo"] = int(len(tempos[1]))
        else:
            registro["bpm_predominante"] = 120.0
            registro["num_mudancas_tempo"] = 0
    except Exception as exc:
        registro["abre_sem_erro"] = False
        registro["erro_leitura"] = str(exc)[:300]
    return registro


_CTX_MELODIA = {}


def init_melodia(ctx):
    global _CTX_MELODIA
    _CTX_MELODIA = ctx


def processar_melodia(tarefa):
    """Extrai, filtra e transpõe a melodia de um MIDI. Grava o .mid resultante."""
    ctx = _CTX_MELODIA
    filtros = ctx["filtros"]
    md5 = tarefa["md5"]
    caminho = tarefa["caminho"]
    faixas_csv = []
    base = {
        "md5": md5,
        "status": "erro",
        "motivo": "",
        "faixas": faixas_csv,
        "melodia": None,
    }
    try:
        midi = pretty_midi.PrettyMIDI(caminho)
    except Exception as exc:
        base["motivo"] = str(exc)[:300]
        return base

    duracao_total = float(midi.get_end_time())
    tempos = midi.get_tempo_changes()
    bpm = float(tempos[1][0]) if len(tempos[1]) > 0 else 120.0
    limite_poli = float(filtros["polifonia_maxima_pct"])

    melhor = None
    for idx, instrumento in enumerate(midi.instruments):
        score, det = calcular_pontuacao(instrumento)
        faixas_csv.append({
            "md5": md5,
            "indice_faixa": idx,
            "nome_faixa": instrumento.name or "",
            "programa": int(instrumento.program),
            "is_drum": bool(instrumento.is_drum),
            "num_notas": len(instrumento.notes),
            "duracao_seg": round(duracao_total, 3),
            "pitch_medio": det.get("pitch_medio", ""),
            "variacao_pitch": det.get("variacao_pitch", ""),
            "pct_polifonia": det.get("pct_polifonia", ""),
            "pct_pausas": det.get("pct_pausas", ""),
            "pontuacao": det.get("pontuacao", ""),
            "selecionada": False,
            "motivo_descarte": "",
        })
        if instrumento.is_drum:
            continue
        if len(instrumento.notes) < filtros["notas_minimas"]:
            continue
        if duracao_total < filtros["duracao_minima_seg"]:
            continue
        if det.get("pct_polifonia", 1) > limite_poli:
            continue
        if melhor is None or score > melhor[0]:
            melhor = (score, idx, instrumento, det)

    if melhor is None:
        base["status"] = "sem_faixa"
        base["motivo"] = "SEM_FAIXA_VALIDA"
        return base

    _, melhor_idx, instrumento, det = melhor
    faixas_csv[melhor_idx]["selecionada"] = True
    notas = converter_monofonia(instrumento.notes, ctx["regra_monofonia"])
    notas, motivo = aplicar_filtros_finais(notas, filtros)
    if motivo:
        faixas_csv[melhor_idx]["motivo_descarte"] = motivo
        base["status"] = "filtro"
        base["motivo"] = motivo
        return base

    tonalidade, modo, semitons = ("C", "maior", 0)
    if ctx["transpor"]:
        tonalidade, modo, semitons = detectar_tonalidade(notas)
        transpor_notas(notas, semitons, filtros["pitch_minimo"], filtros["pitch_maximo"])

    destino = Path(ctx["pasta_melodias"]) / f"{md5}.mid"
    midi_out = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    inst = pretty_midi.Instrument(program=0, name="Melodia")
    inst.notes = list(notas)
    midi_out.instruments.append(inst)
    midi_out.write(str(destino))

    pitches = [int(n.pitch) for n in notas]
    duracao_melodia = float(notas[-1].end - notas[0].start) if notas else 0.0
    base["status"] = "ok"
    base["melodia"] = {
        "md5": md5,
        "nome_original": tarefa.get("nome_original", ""),
        "indice_faixa": melhor_idx,
        "instrumento": nome_instrumento(instrumento.program, instrumento.name),
        "num_notas": len(notas),
        "duracao_seg": round(duracao_melodia, 3),
        "pitch_min": min(pitches),
        "pitch_max": max(pitches),
        "pitch_medio": round(float(np.mean(pitches)), 2),
        "bpm": round(bpm, 2),
        "pontuacao_selecao": det.get("pontuacao", ""),
        "tonalidade_origem": tonalidade,
        "modo": modo,
        "semitons": semitons,
    }
    return base
