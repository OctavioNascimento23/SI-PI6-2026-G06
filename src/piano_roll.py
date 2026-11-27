"""
piano_roll.py — Visualização HTML/CSS da composição (piano-roll + faixa de acordes).

Converte os tokens da melodia (NOTE_x, DURATION_y, REST_z) em retângulos posicionados em
porcentagem, alinhados no mesmo eixo de tempo da faixa de acordes. Sem JavaScript.
"""

import html
from typing import Dict, List

from src.teoria_musical import pitch_para_nome


def _beats(valor: str) -> float:
    v = float(valor)
    return 0.125 if v == 0.12 else v  # o vocabulário grava 0.125 como "0.12"


def extrair_notas(tokens: List[str], bpm: int) -> List[Dict]:
    """Replica a leitura de tokens do midi_builder: devolve notas com início/duração em segundos."""
    seg_por_beat = 60.0 / bpm
    cursor = 0.0
    pendente = None
    notas = []
    for tok in tokens:
        if tok.startswith("NOTE_"):
            try:
                pendente = int(tok.split("_")[1])
            except ValueError:
                pendente = None
        elif tok.startswith("DURATION_") and pendente is not None:
            try:
                dur = _beats(tok.split("_")[1])
                notas.append({"inicio": cursor * seg_por_beat, "duracao": dur * seg_por_beat, "pitch": pendente})
                cursor += dur
            except ValueError:
                pass
            pendente = None
        elif tok.startswith("REST_"):
            try:
                cursor += _beats(tok.split("_")[1])
            except ValueError:
                pass
            pendente = None
    return notas


def _compacto(texto: str) -> str:
    """Remove indentação/quebras: o Markdown do Streamlit trataria linhas indentadas como bloco de código."""
    return "".join(linha.strip() for linha in texto.splitlines())


def _passo_eixo(total: float) -> int:
    for passo in (1, 2, 4, 5, 10, 15, 30):
        if total / passo <= 10:
            return passo
    return 60


def html_piano_roll(res: Dict, geracao: int = 0) -> str:
    """Piano-roll completo da composição. `geracao` alterna a animação para que ela rode a cada nova geração."""
    acordes = res["acordes"]
    notas = extrair_notas(res["tokens"], res["bpm"])
    if not notas or not acordes:
        return ""

    total = max(acordes[-1]["fim_seg"], max(n["inicio"] + n["duracao"] for n in notas))
    p_min = min(n["pitch"] for n in notas)
    p_max = max(n["pitch"] for n in notas)
    linhas = (p_max - p_min + 1) + 2  # uma linha de respiro acima e abaixo
    altura_linha = 100.0 / linhas

    def pct_x(seg: float) -> float:
        return seg / total * 100.0

    # Linhas de grade: uma por Dó (oitava) e divisórias de compasso
    grade = "".join(
        f'<i class="g-oitava" style="bottom:{((p - p_min + 1) / linhas) * 100:.3f}%"></i>'
        for p in range(p_min, p_max + 1)
        if p % 12 == 0
    )
    divisorias = "".join(
        f'<i class="g-compasso" style="left:{pct_x(a["inicio_seg"]):.3f}%"></i>' for a in acordes[1:]
    )

    # Notas: sólidas quando pertencem ao acorde vigente, esmaecidas quando são de passagem
    retangulos = []
    for n in notas:
        acorde = next((a for a in acordes if a["inicio_seg"] <= n["inicio"] < a["fim_seg"]), acordes[-1])
        no_acorde = (n["pitch"] % 12) in acorde["classes_pitch"]
        classe = "nota" if no_acorde else "nota passagem"
        retangulos.append(
            f'<b class="{classe}" style="left:{pct_x(n["inicio"]):.3f}%;'
            f'width:calc({pct_x(n["duracao"]):.3f}% - 1px);'
            f'bottom:{((n["pitch"] - p_min + 1) / linhas) * 100:.3f}%;'
            f'height:{altura_linha:.3f}%"></b>'
        )

    # Faixa de acordes
    denso = len(acordes) > 14
    blocos = []
    for a in acordes:
        grau = "" if denso else f'<small>{html.escape(str(a["grau"]))}</small>'
        blocos.append(
            f'<div class="bloco" style="left:{pct_x(a["inicio_seg"]):.3f}%;'
            f'width:{pct_x(a["fim_seg"] - a["inicio_seg"]):.3f}%">'
            f'<span>{html.escape(str(a["nome"]))}</span>{grau}</div>'
        )

    # Eixo de tempo
    passo = _passo_eixo(total)
    marcas = "".join(
        f'<span style="left:{pct_x(t):.3f}%">{t}s</span>' for t in range(0, int(total) + 1, passo)
    )

    anim = "a" if geracao % 2 == 0 else "b"
    return _compacto(f"""
    <div class="roll">
      <div class="roll-topo">
        <div class="legenda">
          <span><i class="sw nota"></i>Nota do acorde</span>
          <span><i class="sw nota passagem"></i>Nota de passagem</span>
        </div>
        <div class="roll-meta">{len(acordes)} compassos · {len(notas)} notas</div>
      </div>
      <div class="roll-corpo">
        <div class="eixo-y">
          <span>{html.escape(pitch_para_nome(p_max))}</span>
          <span>{html.escape(pitch_para_nome(p_min))}</span>
        </div>
        <div class="roll-area">
          {grade}{divisorias}
          <div class="roll-notas anim-{anim}">{"".join(retangulos)}</div>
        </div>
      </div>
      <div class="roll-acordes">
        <div class="eixo-y"><span>Acordes</span></div>
        <div class="faixa">{"".join(blocos)}</div>
      </div>
      <div class="roll-tempo">
        <div class="eixo-y"></div>
        <div class="marcas">{marcas}</div>
      </div>
    </div>
    """)


def html_piano_roll_vazio() -> str:
    """Esqueleto do piano-roll exibido antes da primeira geração."""
    padrao = [(2, 9, 5), (12, 6, 7), (20, 10, 4), (32, 7, 8), (41, 8, 6), (52, 6, 3), (61, 10, 7), (74, 8, 5), (85, 9, 9)]
    notas = "".join(
        f'<b class="nota fantasma" style="left:{x}%;width:{w}%;bottom:{r * 9 + 6}%;height:7%"></b>'
        for x, w, r in padrao
    )
    return _compacto(f"""
    <div class="roll roll-vazio">
      <div class="roll-corpo">
        <div class="eixo-y"></div>
        <div class="roll-area">{notas}
          <div class="vazio-texto">
            <strong>Nenhuma composição ainda</strong>
            Ajuste os parâmetros e clique em “Compor música”.
          </div>
        </div>
      </div>
    </div>
    """)
