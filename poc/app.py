"""
app.py — Aplicação Streamlit principal
Gerador de Melodias com LSTM — Projeto B6
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
    pitch_para_nome,
    transpor_tokens_para_tonalidade,
)
from poc.midi_builder import limitar_duracao
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

@st.cache_resource(show_spinner="Carregando modelo...")
def carregar_modelo():
    import torch
    from modelo.rede import MelodiaLSTM

    caminho = RAIZ / "modelos" / "lstm_melodia.pt"
    if not caminho.exists():
        return None
    checkpoint = torch.load(caminho, map_location="cpu", weights_only=False)
    cfg = checkpoint["config"]
    token_para_id = checkpoint["token_para_id"]
    rede = MelodiaLSTM(
        vocabulario=len(token_para_id),
        embedding=int(cfg["embedding"]),
        oculto=int(cfg["oculto"]),
        camadas=int(cfg["camadas"]),
        dropout=float(cfg["dropout"]),
        pad_id=token_para_id["<PAD>"],
    )
    rede.load_state_dict(checkpoint["state_dict"])
    rede.eval()
    return {
        "rede": rede,
        "token_para_id": token_para_id,
        "id_para_token": checkpoint["id_para_token"],
    }

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
      <span id="status" style="margin-left:12px;color:#888;">Carregando instrumentos...</span>
    </div>
    <script>
      var Player = new MidiPlayer.Player(function(event) {{}});
      var ac = new AudioContext();
      var sons = {{}};
      var programas = {{}};
      var ativos = {{}};
      var pronto = false;

      function nomeDoPrograma(programa) {{
        if (programa === 4) return 'epiano';
        if (programa >= 16 && programa <= 18) return 'organ';
        if (programa === 32) return 'bassAcoustic';
        if (programa === 33 || programa === 34) return 'bass';
        if (programa === 89 || programa === 48) return 'pad';
        return 'piano';
      }}

      function escolher(event) {{
        var canal = event.channel;
        if (canal === 9 || canal === 10) return sons.drums;
        var programa = programas[canal];
        return sons[nomeDoPrograma(programa)] || sons.piano;
      }}

      function aoEvento(event) {{
        if (event.name === 'Program Change') {{
          programas[event.channel] = event.value !== undefined ? event.value : event.number;
          return;
        }}
        var ligar = event.name === 'Note on' && event.velocity > 0;
        var desligar = event.name === 'Note off' || (event.name === 'Note on' && event.velocity === 0);
        var chave = event.channel + '-' + event.noteNumber;
        if (ligar) {{
          var inst = escolher(event);
          if (!inst) return;
          ativos[chave] = inst.play(event.noteNumber, ac.currentTime, {{
            gain: Math.max(0.15, event.velocity / 127)
          }});
        }} else if (desligar && ativos[chave] && ativos[chave].stop) {{
          ativos[chave].stop(ac.currentTime + 0.02);
          delete ativos[chave];
        }}
      }}

      Player.on('midiEvent', aoEvento);
      Player.on('endOfFile', function() {{
        document.getElementById('btn-play').innerText = '▶ Play';
        document.getElementById('status').innerText = 'Concluído';
      }});

      var pedidos = [
        ['piano', 'acoustic_grand_piano'],
        ['organ', 'rock_organ'],
        ['bassAcoustic', 'acoustic_bass'],
        ['bass', 'electric_bass_finger'],
        ['epiano', 'electric_piano_1'],
        ['pad', 'pad_2_warm'],
        ['drums', 'synth_drum']
      ];
      Promise.all(pedidos.map(function(par) {{
        return Soundfont.instrument(ac, par[1], {{ soundfont: 'MusyngKite' }}).then(function(inst) {{
          sons[par[0]] = inst;
        }});
      }})).then(function() {{
        pronto = true;
        document.getElementById('status').innerText = 'Pronto';
      }}).catch(function() {{
        document.getElementById('status').innerText = 'Não foi possível carregar os instrumentos';
      }});

      var midiData = atob("{midi_b64}");
      var bytes = new Uint8Array(midiData.length);
      for (var i = 0; i < midiData.length; i++) {{
        bytes[i] = midiData.charCodeAt(i);
      }}
      Player.loadArrayBuffer(bytes.buffer);

      function togglePlay() {{
        if (!pronto) return;
        ac.resume();
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
    st.components.v1.html(html, height=90)

# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

st.title("🎵 Gerador de Melodias — Projeto B6")
st.caption("Projeto Integrador VI — 2026 | Motores: LSTM no Lakh e midi-model do SkyTNT")

modelo = carregar_modelo()

if modelo is None:
    st.error(
        "Modelo não encontrado em `modelos/lstm_melodia.pt`.\n\n"
        "Execute primeiro:\n```\npython scripts/06_treinar_lstm.py\n```"
    )
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar — Parâmetros
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("🎛️ Parâmetros")

    motor = st.selectbox(
        "Motor",
        options=["LSTM", "SkyTNT"],
        index=0,
        help="LSTM é a rede treinada aqui. SkyTNT é um Transformer de MIDI já treinado.",
    )

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

    temperatura = st.slider(
        "Variação",
        min_value=0.5,
        max_value=1.4,
        value=0.9,
        step=0.1,
        help="Valores menores repetem padrões com mais frequência. Valores maiores variam mais.",
    )

    if motor == "LSTM":
        estilo = st.selectbox(
            "Estilo do arranjo",
            options=["Pop", "Rock", "Balada"],
            index=0,
            help="Define bateria, baixo e acorde em volta da melodia.",
        )
    else:
        estilo = "SkyTNT"
        st.caption("No SkyTNT os instrumentos saem do modelo. A primeira geração carrega os pesos e pode levar cerca de um minuto.")

    gerar = st.button("🎵 Gerar música", use_container_width=True, type="primary")

# ---------------------------------------------------------------------------
# Geração
# ---------------------------------------------------------------------------

if gerar:
    aviso = "Gerando com o midi-model..." if motor == "SkyTNT" else "Gerando música..."
    with st.spinner(aviso):
        st.session_state["geracao"] = st.session_state.get("geracao", 0) + 1
        caminho_mid = str(RAIZ / "poc" / "saida_temp" / f"melodia_{st.session_state['geracao']}.mid")
        os.makedirs(os.path.dirname(caminho_mid), exist_ok=True)

        if motor == "SkyTNT":
            from poc.skytnt_pedido import pedir_geracao

            try:
                st.session_state["resumo"] = pedir_geracao(
                    tonalidade, bpm, float(duracao), float(temperatura), caminho_mid
                )
            except Exception as exc:
                st.error(f"Não foi possível gerar com o SkyTNT: {exc}")
                st.stop()
            st.session_state["tokens"] = []
        else:
            from modelo.rede import gerar as gerar_tokens
            from poc.arranjo import salvar_musica

            num_tokens_alvo = min(2500, int(duracao / 0.03) + 32)
            tokens = gerar_tokens(
                modelo["rede"],
                modelo["token_para_id"],
                modelo["id_para_token"],
                num_tokens=num_tokens_alvo,
                temperatura=float(temperatura),
                parar_no_fim=False,
            )
            tokens = transpor_tokens_para_tonalidade(tokens, tonalidade)
            tokens = limitar_duracao(tokens, bpm, float(duracao))
            salvar_musica(tokens, tonalidade, bpm, float(duracao), estilo, caminho_mid)
            st.session_state["resumo"] = None
            st.session_state["tokens"] = tokens

        caminho_wav = renderizar(caminho_mid)
        st.session_state["melodia_mid"] = caminho_mid
        st.session_state["melodia_wav"] = caminho_wav
        st.session_state["bpm"] = bpm
        st.session_state["tonalidade"] = tonalidade
        st.session_state["temperatura"] = temperatura
        st.session_state["estilo"] = estilo
        st.session_state["motor"] = motor

# ---------------------------------------------------------------------------
# Área de resultado
# ---------------------------------------------------------------------------

if "melodia_mid" in st.session_state:
    st.subheader("🎼 Música gerada")

    col1, col2 = st.columns([2, 1])

    with col1:
        wav = st.session_state["melodia_wav"]
        mid = st.session_state["melodia_mid"]

        if wav and Path(wav).exists():
            with open(wav, "rb") as f:
                st.audio(f.read(), format="audio/wav")
        else:
            st.info(
                "FluidSynth não disponível — o player da página toca "
                "melodia, acorde, baixo e bateria. Clique em ▶ Play abaixo."
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
                key=f"download_{st.session_state.get('geracao', 0)}",
            )

    with col2:
        st.subheader("📊 Detalhes")
        resumo = st.session_state.get("resumo")
        tokens = st.session_state.get("tokens") or []
        notas = [t for t in tokens if t.startswith("NOTE_")]

        st.metric("Motor", st.session_state.get("motor", "LSTM"))
        st.metric("Notas geradas", resumo["notas"] if resumo else len(notas))
        st.metric("BPM", st.session_state["bpm"])
        st.metric("Tonalidade", st.session_state["tonalidade"])
        st.metric("Estilo", st.session_state.get("estilo", "Pop"))
        st.metric("Variação", f"{st.session_state.get('temperatura', 0.9):.1f}")
        if resumo:
            st.caption(resumo["faixas"])
            if resumo["grave"] is not None:
                st.metric("Nota mais grave", pitch_para_nome(resumo["grave"]))
                st.metric("Nota mais aguda", pitch_para_nome(resumo["aguda"]))
        else:
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
    "Motores: LSTM + arranjo, e midi-model (SkyTNT, Apache 2.0) | "
    "Dados: Lakh MIDI Dataset (CC BY 4.0)"
)
