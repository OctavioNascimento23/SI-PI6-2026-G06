"""
app.py — Aplicação Principal Streamlit
Gerador Inteligente de Melodias e Progressões Harmônicas — Projeto Integrador VI (Grupo B6)
"""

import html
import os
import sys
from pathlib import Path
import streamlit as st

# Garante que a raiz do projeto está no sys.path
RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from src.teoria_musical import ESCALAS, PROGRESSOES_GRAUS
from src.midi_builder import PROGRAMAS_GM
from src.gerador import GeradorMusical
from src.piano_roll import html_piano_roll, html_piano_roll_vazio

# ---------------------------------------------------------------------------
# Configuração da Página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Gerador de Melodias — PI VI",
    page_icon="🎹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sistema de design (tokens, tipografia, motion) em assets/estilo.css
_css = RAIZ / "assets" / "estilo.css"
if _css.exists():
    st.markdown(f"<style>{_css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def secao(titulo: str, detalhe: str = "") -> None:
    nota = f'<span class="secao-nota">{html.escape(detalhe)}</span>' if detalhe else ""
    st.markdown(
        f'<div class="secao"><span class="secao-titulo">{html.escape(titulo)}</span>{nota}</div>',
        unsafe_allow_html=True,
    )


def rotulo_sidebar(texto: str) -> None:
    st.markdown(f'<div class="sb-grupo">{html.escape(texto)}</div>', unsafe_allow_html=True)


_MARCA_SVG = (
    '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">'
    '<rect x="1" y="12" width="6" height="4" rx="1" fill="#f0b44c"/>'
    '<rect x="8" y="6" width="9" height="4" rx="1" fill="#f0b44c"/>'
    '<rect x="12" y="14" width="8" height="4" rx="1" fill="#f0b44c" fill-opacity=".35" '
    'stroke="#f0b44c" stroke-opacity=".6"/></svg>'
)

# ---------------------------------------------------------------------------
# Inicialização do Gerador com Cache
# ---------------------------------------------------------------------------

@st.cache_resource
def obter_gerador(versao_codigo: float):
    # versao_codigo (mtime dos módulos) invalida o cache quando o código-fonte muda
    return GeradorMusical(raiz_projeto=RAIZ)

_versao_codigo = max(p.stat().st_mtime for p in (RAIZ / "src").rglob("*.py"))
gerador = obter_gerador(_versao_codigo)
# Força a verificação e recarregamento caso novos modelos tenham sido colocados
if gerador.modelo_transformer is None and (RAIZ / "modelos" / "modelo_transformer.pt").exists():
    gerador.carregar_transformer()

# ---------------------------------------------------------------------------
# Sidebar — Controles e Parâmetros
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(f'<div class="sb-marca">{_MARCA_SVG}Melodia &amp; Harmonia</div>', unsafe_allow_html=True)
    st.divider()
    rotulo_sidebar("Harmonia")

    tonalidade = st.selectbox(
        "Tonalidade / Escala",
        options=list(ESCALAS.keys()),
        index=0,
        help="Define a tonalidade e a escala musical da composição."
    )

    estilo_harmonia = st.selectbox(
        "Progressão de acordes",
        options=list(PROGRESSOES_GRAUS.keys()),
        index=0,
        help="Define a cadência harmônica (graus I-V-vi-IV, etc.) que servirá de suporte para a melodia."
    )

    col_bpm, col_dur = st.columns(2)
    with col_bpm:
        bpm = st.slider("BPM", min_value=60, max_value=180, value=120, step=5)
    with col_dur:
        duracao = st.slider("Duração (s)", min_value=8, max_value=60, value=20, step=4)

    st.divider()
    rotulo_sidebar("Motor de IA")

    modelos_status = gerador.modelos_disponiveis()
    opcoes_modelos = list(modelos_status.keys())

    # Seleção inteligente do modelo padrão
    idx_default = 0
    if not modelos_status["Transformer (Deep Learning)"]:
        idx_default = 2  # Markov enquanto o modelo neural não for treinado/baixado

    modelo_escolhido = st.selectbox(
        "Arquitetura de geração",
        options=opcoes_modelos,
        index=idx_default,
        help="Escolha entre Transformer (Deep Learning), LSTM ou o modelo probabilístico de Markov."
    )

    guiar_harmonia = st.checkbox(
        "Guiar melodia pela harmonia",
        value=True,
        help="Favorece notas do acorde do compasso (mais nos tempos fortes) durante a geração. Aplica-se a Transformer e LSTM.",
    )

    temperatura = st.slider(
        "Criatividade (temperatura)",
        min_value=0.2,
        max_value=1.5,
        value=0.85,
        step=0.05,
        help="Controla a aleatoriedade da geração de notas melódicas."
    )

    st.divider()
    rotulo_sidebar("Instrumentação")

    inst_melodia = st.selectbox("Melodia (faixa 2)", options=list(PROGRAMAS_GM.keys()), index=0)
    inst_acordes = st.selectbox("Acordes (faixa 1)", options=list(PROGRAMAS_GM.keys()), index=1)

    st.divider()
    btn_gerar = st.button("Compor música", use_container_width=True, type="primary")

    if st.button("Recarregar motor e modelos", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()


# ---------------------------------------------------------------------------
# Conteúdo Principal
# ---------------------------------------------------------------------------

# Status dos motores: chips discretos em vez de três cartões idênticos
_motores = [
    ("Transformer (Deep Learning)", "Transformer", "Treinar no Colab"),
    ("LSTM (Rede Neural)", "LSTM", "Treinar no Colab"),
    ("Cadeia de Markov (Probabilístico)", "Markov", "Pendente"),
]
_chips = "".join(
    f'<span class="motor{"" if modelos_status[chave] else " pendente"}">{nome}'
    f'{"" if modelos_status[chave] else f" <em>· {pendente}</em>"}</span>'
    for chave, nome, pendente in _motores
)
st.markdown(
    '<div class="hero"><h1>Melodias e harmonias compostas por IA</h1>'
    "<p>Escolha tonalidade, progressão e motor na barra lateral. O resultado é uma melodia "
    "alinhada a uma faixa de acordes, pronta para ouvir ou baixar em MIDI.</p>"
    f'<div class="motores">{_chips}</div></div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Execução da Geração
# ---------------------------------------------------------------------------

if btn_gerar:
    with st.spinner("Gerando acordes e compondo a melodia..."):
        saida_mid = str(RAIZ / "saida_temp" / "musica_gerada.mid")
        os.makedirs(os.path.dirname(saida_mid), exist_ok=True)

        resultado = gerador.compor(
            tonalidade=tonalidade,
            bpm=bpm,
            duracao_seg=float(duracao),
            estilo_progressao=estilo_harmonia,
            tipo_modelo=modelo_escolhido,
            temperatura=temperatura,
            instrumento_melodia=inst_melodia,
            instrumento_acordes=inst_acordes,
            caminho_saida_midi=saida_mid,
            guiar_por_harmonia=guiar_harmonia,
        )

        st.session_state["resultado_geracao"] = resultado
        st.session_state["contador_geracao"] = st.session_state.get("contador_geracao", 0) + 1

# ---------------------------------------------------------------------------
# Exibição dos Resultados e Player de Áudio Sincronizado
# ---------------------------------------------------------------------------

if "resultado_geracao" not in st.session_state:
    secao("Composição", "Melodia e acordes aparecerão aqui")
    st.markdown(html_piano_roll_vazio(), unsafe_allow_html=True)
else:
    res = st.session_state["resultado_geracao"]
    wav_path = res.get("caminho_wav")
    mid_path = res.get("caminho_midi")

    secao("Composição", f"{res['tonalidade']} · {res['bpm']} BPM")

    # Player e download lado a lado, logo acima da visualização
    col_player, col_baixar = st.columns([2.4, 1], gap="medium", vertical_alignment="center")
    with col_player:
        if wav_path and Path(wav_path).exists():
            with open(wav_path, "rb") as f_audio:
                st.audio(f_audio.read(), format="audio/wav")
    with col_baixar:
        nome_arqv = f"musica_b6_{res['tonalidade'].replace(' ', '_')}_{res['bpm']}bpm.mid"
        with open(mid_path, "rb") as f_mid:
            st.download_button(
                label="Baixar MIDI (.mid)",
                data=f_mid,
                file_name=nome_arqv,
                mime="audio/midi",
                use_container_width=True,
            )

    # Assinatura visual: piano-roll da melodia alinhado à faixa de acordes
    if res.get("aviso_progressao"):
        st.info(res["aviso_progressao"])
    st.markdown(
        html_piano_roll(res, st.session_state.get("contador_geracao", 0)),
        unsafe_allow_html=True,
    )

    # Métricas da composição
    metricas = [
        ("Motor", res["modelo_usado"].split(" (")[0]),
        ("Acordes", f"{len(res['acordes'])} compassos"),
        ("Melodia", f"{res['num_notas']} notas"),
        ("Extensão", f"{res['nota_grave']} – {res['nota_aguda']}"),
    ]
    itens = "".join(
        f'<div class="metrica"><div class="rotulo">{html.escape(r)}</div>'
        f'<div class="valor">{html.escape(str(v))}</div></div>'
        for r, v in metricas
    )
    st.markdown(f'<div class="metricas">{itens}</div>', unsafe_allow_html=True)
    if "Fallback" in res["modelo_usado"]:
        st.caption(f"Motor utilizado: {res['modelo_usado']}")

    # Detalhes técnicos para inspeção/banca
    st.write("")
    with st.expander("Inspeção técnica de tokens e eventos MIDI"):
        st.json({
            "parametros": {
                "tonalidade": res["tonalidade"],
                "bpm": res["bpm"],
                "modelo": res["modelo_usado"],
            },
            "acordes_base": res["acordes"],
            "tokens_melodia": res["tokens"][:50],
        })

# ---------------------------------------------------------------------------
# Rodapé Institucional
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="rodape">PUC-Campinas · Sistemas de Informação — Projeto Integrador VI (2026)<br/>'
    "Grupo B6: Eduardo Freitas, Guilherme Santos, Hector Lopes, Mariana Ferreira, Octávio Nascimento<br/>"
    "Orientação: Prof. Dimas Augusto</div>",
    unsafe_allow_html=True,
)
