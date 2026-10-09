"""
app.py — Aplicação Streamlit principal
Gerador de Melodias com Cadeia de Markov — Projeto B6
"""

import base64
import os
import sys
from pathlib import Path

import streamlit as st

# Garante que a raiz do projeto está no sys.path para imports relativos
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from poc.teoria_musical import (
    ESCALAS,
    filtrar_tokens_por_tonalidade,
    pitch_para_nome,
)
from poc.midi_builder import tokens_para_midi, limitar_duracao
from poc.audio_renderer import renderizar

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Gerador de Melodias — B6",
    page_icon="🎵",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Carregamento do modelo com cache
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Carregando modelo Markov...")
def carregar_modelo():
    from poc.markov import ModeloMarkov
    caminho = RAIZ / "modelos" / "markov_modelo.pkl"
    if not caminho.exists():
        return None
    modelo = ModeloMarkov()
    modelo.carregar(caminho)
    return modelo

# ---------------------------------------------------------------------------
# Player MIDI em JavaScript (fallback sem FluidSynth)
# ---------------------------------------------------------------------------

def exibir_player_js(caminho_mid: str) -> None:
    with open(caminho_mid, "rb") as f:
        midi_b64 = base64.b64encode(f.read()).decode()

    html = f"""
    <script src="https://cdn.jsdelivr.net/npm/midi-player-js@2.0.16/browser/midiplayer.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/soundfont-player/dist/soundfont-player.min.js"></script>
    <div id="player-container" style="padding:10px;">
      <button id="btn-play" onclick="togglePlay()"
        style="padding:10px 24px;font-size:16px;cursor:pointer;
               background:#4CAF50;color:white;border:none;border-radius:6px;">
        ▶ Play
      </button>
      <span id="status" style="margin-left:12px;color:#888;">Pronto</span>
    </div>
    <script>
      var Player = new MidiPlayer.Player(function(event) {{}});
      var ac = new AudioContext();
      var instrument;

      Soundfont.instrument(ac, 'acoustic_grand_piano').then(function(piano) {{
        instrument = piano;
        Player.on('midiEvent', function(event) {{
          if (event.name === 'Note on' && event.velocity > 0) {{
            instrument.play(event.noteNumber, ac.currentTime, {{gain: event.velocity / 127}});
          }}
        }});
        Player.on('endOfFile', function() {{
          document.getElementById('btn-play').innerText = '▶ Play';
          document.getElementById('status').innerText = 'Concluído';
        }});
      }});

      var midiData = atob("{midi_b64}");
      var bytes = new Uint8Array(midiData.length);
      for (var i = 0; i < midiData.length; i++) {{
        bytes[i] = midiData.charCodeAt(i);
      }}
      Player.loadArrayBuffer(bytes.buffer);

      function togglePlay() {{
        if (Player.isPlaying()) {{
          Player.pause();
          document.getElementById('btn-play').innerText = '▶ Play';
          document.getElementById('status').innerText = 'Pausado';
        }} else {{
          Player.play();
          document.getElementById('btn-play').innerText = '⏸ Pause';
          document.getElementById('status').innerText = 'Tocando...';
        }}
      }}
    </script>
    """
    st.components.v1.html(html, height=80)

# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

st.title("🎵 Gerador de Melodias — Projeto B6")
st.caption("Projeto Integrador VI — 2026 | Motor: Cadeia de Markov (ordem 2)")

modelo = carregar_modelo()

if modelo is None:
    st.error(
        "Modelo não encontrado em `modelos/markov_modelo.pkl`.\n\n"
        "Execute primeiro:\n```\npython poc/treinar_markov.py\n```"
    )
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar — Parâmetros
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("🎛️ Parâmetros")

    tonalidade = st.selectbox(
        "Tonalidade",
        options=list(ESCALAS.keys()),
        index=0,
    )

    bpm = st.slider(
        "BPM (andamento)",
        min_value=60,
        max_value=180,
        value=120,
        step=5,
    )

    duracao = st.slider(
        "Duração (segundos)",
        min_value=10,
        max_value=60,
        value=30,
        step=5,
    )

    gerar = st.button("🎵 Gerar Melodia", use_container_width=True, type="primary")

# ---------------------------------------------------------------------------
# Geração
# ---------------------------------------------------------------------------

if gerar:
    with st.spinner("Gerando melodia..."):
        # Estimar tokens necessários: ~2 notas/s × 2 tokens/nota
        num_tokens_alvo = int(duracao * 2 * 2)

        tokens = modelo.gerar(num_tokens=num_tokens_alvo)
        tokens = filtrar_tokens_por_tonalidade(tokens, tonalidade)
        tokens = limitar_duracao(tokens, bpm, float(duracao))

        caminho_mid = str(RAIZ / "poc" / "saida_temp" / "melodia.mid")
        os.makedirs(os.path.dirname(caminho_mid), exist_ok=True)
        tokens_para_midi(tokens, bpm, caminho_mid)

        caminho_wav = renderizar(caminho_mid)

        st.session_state["melodia_mid"] = caminho_mid
        st.session_state["melodia_wav"] = caminho_wav
        st.session_state["tokens"] = tokens
        st.session_state["bpm"] = bpm
        st.session_state["tonalidade"] = tonalidade

# ---------------------------------------------------------------------------
# Área de resultado
# ---------------------------------------------------------------------------

if "melodia_mid" in st.session_state:
    st.subheader("🎼 Melodia Gerada")

    col1, col2 = st.columns([2, 1])

    with col1:
        wav = st.session_state["melodia_wav"]
        mid = st.session_state["melodia_mid"]

        if wav and Path(wav).exists():
            with open(wav, "rb") as f:
                st.audio(f.read(), format="audio/wav")
        else:
            st.info(
                "FluidSynth não disponível — usando player JavaScript. "
                "Clique em ▶ Play abaixo."
            )
            exibir_player_js(mid)

        # Botão de download
        nome_arquivo = (
            f"melodia_b6_{st.session_state['tonalidade'].replace(' ', '_')}.mid"
        )
        with open(mid, "rb") as f:
            st.download_button(
                label="⬇️ Download .mid",
                data=f,
                file_name=nome_arquivo,
                mime="audio/midi",
            )

    with col2:
        st.subheader("📊 Detalhes")
        tokens = st.session_state["tokens"]
        notas = [t for t in tokens if t.startswith("NOTE_")]

        st.metric("Notas geradas", len(notas))
        st.metric("BPM", st.session_state["bpm"])
        st.metric("Tonalidade", st.session_state["tonalidade"])
        st.metric("Total de tokens", len(tokens))

        if notas:
            pitches = [int(t.split("_")[1]) for t in notas]
            st.metric("Nota mais grave", pitch_para_nome(min(pitches)))
            st.metric("Nota mais aguda", pitch_para_nome(max(pitches)))

# ---------------------------------------------------------------------------
# Rodapé
# ---------------------------------------------------------------------------

st.divider()
st.caption(
    "Projeto B6 — SI-PI6-2026-G06 | Projeto Integrador VI — 2026 | "
    "Motor de geração: Cadeia de Markov (ordem 2) | "
    "Dados: Lakh MIDI Dataset (CC BY 4.0)"
)
