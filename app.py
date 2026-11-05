"""
app.py — Aplicação Principal Streamlit
Gerador Inteligente de Melodias e Progressões Harmônicas — Projeto Integrador VI (Grupo B6)
"""

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

# ---------------------------------------------------------------------------
# Configuração da Página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Gerador de Melodia & Harmonia — PI VI",
    page_icon="🎹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Inicialização do Gerador com Cache
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Carregando motor de composição musical...")
def obter_gerador():
    return GeradorMusical(raiz_projeto=RAIZ)

gerador = obter_gerador()

# ---------------------------------------------------------------------------
# Sidebar — Controles e Parâmetros
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🎛️ Parâmetros Musicais")

    tonalidade = st.selectbox(
        "🎼 Tonalidade / Escala",
        options=list(ESCALAS.keys()),
        index=0,
        help="Define a tonalidade e a escala musical da composição."
    )

    estilo_harmonia = st.selectbox(
        "🎹 Progressão de Acordes (Base)",
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
    st.subheader("🤖 Motor de IA")

    modelos_status = gerador.modelos_disponiveis()
    opcoes_modelos = list(modelos_status.keys())

    # Seleção inteligente do modelo padrão
    idx_default = 0
    if not modelos_status["Transformer (Deep Learning)"]:
        idx_default = 2  # Markov enquanto o modelo neural não for treinado/baixado

    modelo_escolhido = st.selectbox(
        "Arquitetura de Geração",
        options=opcoes_modelos,
        index=idx_default,
        help="Escolha entre Transformer (Deep Learning), LSTM ou o modelo probabilístico de Markov."
    )

    temperatura = st.slider(
        "Criatividade (Temperatura)",
        min_value=0.2,
        max_value=1.5,
        value=0.85,
        step=0.05,
        help="Controla a aleatoriedade da geração de notas melódicas."
    )

    st.divider()
    st.subheader("🎻 Instrumentação Multifaixa")

    col_inst1, col_inst2 = st.columns(2)
    with col_inst1:
        inst_melodia = st.selectbox("Melodia (Faixa 2)", options=list(PROGRAMAS_GM.keys()), index=0)
    with col_inst2:
        inst_acordes = st.selectbox("Acordes (Faixa 1)", options=list(PROGRAMAS_GM.keys()), index=1)

    st.divider()
    btn_gerar = st.button("✨ Compor Música com IA", use_container_width=True, type="primary")


# ---------------------------------------------------------------------------
# Conteúdo Principal
# ---------------------------------------------------------------------------

st.title("🎹 Gerador de Melodias & Harmonias com IA")
st.caption("Projeto Integrador VI — Sistemas de Informação (2026) | Grupo B6")

# Status dos Modelos
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    ativo = modelos_status["Transformer (Deep Learning)"]
    st.metric("Transformer (GPT Music)", "Ativo ✅" if ativo else "Treinar no Colab ☁️")
with col_m2:
    ativo = modelos_status["LSTM (Rede Neural)"]
    st.metric("LSTM Recorrente", "Ativo ✅" if ativo else "Treinar no Colab ☁️")
with col_m3:
    ativo = modelos_status["Cadeia de Markov (Probabilístico)"]
    st.metric("Markov Baseline", "Pronto ✅" if ativo else "Pendente ⚠️")

st.divider()

# ---------------------------------------------------------------------------
# Execução da Geração
# ---------------------------------------------------------------------------

if btn_gerar:
    with st.spinner("Gerando base de acordes e compondo melodia multifaixa..."):
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
        )

        st.session_state["resultado_geracao"] = resultado

# ---------------------------------------------------------------------------
# Exibição dos Resultados e Player de Áudio Sincronizado
# ---------------------------------------------------------------------------

if "resultado_geracao" in st.session_state:
    res = st.session_state["resultado_geracao"]

    st.subheader("🎧 Composição Gerada (Áudio Multifaixa Completo)")

    col_player, col_stats = st.columns([1.7, 1.3])

    with col_player:
        wav_path = res.get("caminho_wav")
        mid_path = res.get("caminho_midi")

        st.markdown("**🔊 Player de Áudio Sincronizado (Acordes + Melodia Simultâneos):**")
        if wav_path and Path(wav_path).exists():
            with open(wav_path, "rb") as f_audio:
                st.audio(f_audio.read(), format="audio/wav")
            st.caption("🎵 Áudio sintetizado contendo a Faixa 1 (Acordes de Base) e a Faixa 2 (Melodia) perfeitamente alinhadas.")

        # Botão de download do MIDI multifaixa
        nome_arqv = f"musica_b6_{res['tonalidade'].replace(' ', '_')}_{res['bpm']}bpm.mid"
        with open(mid_path, "rb") as f_mid:
            st.download_button(
                label="⬇️ Baixar Arquivo MIDI Multifaixa (.mid)",
                data=f_mid,
                file_name=nome_arqv,
                mime="audio/midi",
                use_container_width=True,
            )

    with col_stats:
        st.markdown("**📊 Resumo da Composição**")
        st.write(f"• **Motor Utilizado:** `{res['modelo_usado']}`")
        st.write(f"• **Tonalidade:** `{res['tonalidade']}` | **Andamento:** `{res['bpm']} BPM`")
        st.write(f"• **Faixa 1 (Base Harmônica):** {len(res['acordes'])} compassos de acordes")
        st.write(f"• **Faixa 2 (Solo Melódico):** {res['num_notas']} notas geradas")
        st.write(f"• **Extensão Melódica:** De `{res['nota_grave']}` até `{res['nota_aguda']}`")

    # Exibição visual da Progressão de Acordes
    st.subheader("🎼 Estrutura Harmônica por Compasso")
    acordes_lista = res["acordes"]

    cols_acordes = st.columns(min(len(acordes_lista), 8))
    for idx, ac in enumerate(acordes_lista[:8]):
        with cols_acordes[idx]:
            st.markdown(
                f"""
                <div style="background:#1e1e2e;padding:12px;border-radius:8px;text-align:center;border-left:4px solid #10b981;">
                  <span style="font-size:12px;color:#9ca3af;">Compasso {ac['compasso']}</span><br/>
                  <strong style="font-size:22px;color:#f3f4f6;">{ac['nome']}</strong><br/>
                  <span style="font-size:13px;color:#10b981;font-weight:600;">Grau {ac['grau']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Detalhes técnicos para inspeção/banca
    with st.expander("🔍 Inspeção Técnica de Tokens e Eventos MIDI"):
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

st.divider()
st.caption(
    "PUC-Campinas | Sistemas de Informação — Projeto Integrador VI (2026) | "
    "Grupo B6: Eduardo Freitas, Guilherme Santos, Hector Lopes, Mariana Ferreira, Octávio Nascimento | "
    "Orientação: Prof. Dimas Augusto"
)
