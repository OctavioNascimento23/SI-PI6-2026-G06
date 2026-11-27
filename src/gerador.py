"""
gerador.py
Motor Central de Inferência e Composição Musical:
Integra a geração da base harmônica (progressão de acordes) com a melodia de IA
(Transformer, LSTM ou Markov) e compila o MIDI multifaixa e áudio.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from src.teoria_musical import (
    ESCALAS,
    PROGRESSOES_GRAUS,
    gerar_progressao_acordes,
    resolver_progressao,
    deslocamento_para_do,
    transpor_tokens,
    filtrar_tokens_por_tonalidade,
    pitch_para_nome,
)
from src.midi_builder import construir_midi_completo, limitar_duracao, PROGRAMAS_GM
from src.audio_renderer import renderizar
from src.harmonia_guia import criar_guia_harmonico
from src.modelos.markov import ModeloMarkov

# Imports opcionais de Deep Learning (caso PyTorch não esteja instalado localmente)
try:
    from src.modelos.lstm_model import MelodyLSTM
except ImportError:
    MelodyLSTM = None

try:
    from src.modelos.transformer_model import MusicTransformer
except ImportError:
    MusicTransformer = None


class GeradorMusical:
    def __init__(self, raiz_projeto: Optional[Path] = None):
        if raiz_projeto is None:
            raiz_projeto = Path(__file__).resolve().parent.parent
        self.raiz = raiz_projeto
        self.pasta_modelos = self.raiz / "modelos"
        self.caminho_vocab = self.raiz / "dados_processados" / "sequencias" / "vocabulario.json"

        self.vocabulario: Optional[Dict] = None
        self.token_para_id: Dict[str, int] = {}
        self.id_para_token: Dict[str, str] = {}
        self._carregar_vocabulario()

        # Cache de instâncias de modelos
        self.modelo_markov: Optional[ModeloMarkov] = None
        self.modelo_lstm: Optional[Any] = None
        self.modelo_transformer: Optional[Any] = None

    def _carregar_vocabulario(self) -> None:
        # Prioriza o vocabulário dentro de modelos/ (específico do checkpoint treinado)
        caminhos = [
            self.pasta_modelos / "vocabulario.json",
            self.caminho_vocab,
        ]
        for p in caminhos:
            if p.exists():
                try:
                    dados = json.loads(p.read_text(encoding="utf-8"))
                    self.vocabulario = dados
                    self.token_para_id = dados.get("token_para_id", {})
                    self.id_para_token = dados.get("id_para_token", {})
                    break
                except Exception as e:
                    print(f"Aviso ao carregar vocabulário ({p}): {e}")

    def carregar_markov(self) -> Optional[ModeloMarkov]:
        if self.modelo_markov is None:
            caminho = self.pasta_modelos / "markov_modelo.pkl"
            if caminho.exists():
                m = ModeloMarkov()
                m.carregar(caminho)
                self.modelo_markov = m
        return self.modelo_markov

    def carregar_lstm(self) -> Optional[Any]:
        if MelodyLSTM is None:
            return None
        if self.modelo_lstm is None:
            caminho = self.pasta_modelos / "modelo_lstm.pt"
            if caminho.exists():
                try:
                    self.modelo_lstm = MelodyLSTM.carregar(caminho)
                except Exception as e:
                    print(f"Erro ao carregar LSTM: {e}")
        return self.modelo_lstm

    def carregar_transformer(self) -> Optional[Any]:
        if MusicTransformer is None:
            return None
        if not self.vocabulario:
            self._carregar_vocabulario()
        if self.modelo_transformer is None:
            caminho = self.pasta_modelos / "modelo_transformer.pt"
            if caminho.exists():
                try:
                    self.modelo_transformer = MusicTransformer.carregar(caminho)
                except Exception as e:
                    print(f"Erro ao carregar Transformer: {e}")
        return self.modelo_transformer

    def modelos_disponiveis(self) -> Dict[str, bool]:
        """Verifica quais modelos estão prontos para inferência na pasta modelos/."""
        tem_transformer = (self.pasta_modelos / "modelo_transformer.pt").exists() and MusicTransformer is not None
        tem_lstm = (self.pasta_modelos / "modelo_lstm.pt").exists() and MelodyLSTM is not None
        tem_markov = (self.pasta_modelos / "markov_modelo.pkl").exists()

        return {
            "Transformer (Deep Learning)": tem_transformer,
            "LSTM (Rede Neural)": tem_lstm,
            "Cadeia de Markov (Probabilístico)": tem_markov,
        }

    def compor(
        self,
        tonalidade: str = "Dó Maior",
        bpm: int = 120,
        duracao_seg: float = 30.0,
        estilo_progressao: str = "Pop / Hits (I - V - vi - IV)",
        tipo_modelo: str = "Cadeia de Markov (Probabilístico)",
        temperatura: float = 0.85,
        instrumento_melodia: str = "Piano Acústico",
        instrumento_acordes: str = "Piano Elétrico",
        caminho_saida_midi: Optional[str] = None,
        guiar_por_harmonia: bool = True,
    ) -> Dict[str, Any]:
        """
        Executa o pipeline completo de composição:
        1. Gera a progressão de acordes de base
        2. Gera os tokens de melodia via IA
        3. Harmoniza, quantiza e constrói o arquivo MIDI multifaixa
        4. Renderiza áudio WAV se possível
        """
        if caminho_saida_midi is None:
            caminho_saida_midi = str(self.raiz / "saida_temp" / "musica_gerada.mid")

        # 1. Base harmônica de acordes
        acordes = gerar_progressao_acordes(
            tonalidade=tonalidade,
            estilo_progressao=estilo_progressao,
            duracao_seg=duracao_seg,
            bpm=bpm,
        )

        # 2. Geração da melodia pela IA
        # Os modelos foram treinados SEM transposição e rendem melhor na região de Dó Maior / Lá Menor
        # (contexto/009). Por isso a melodia é gerada nessa região, com os acordes levados para lá, e
        # só depois transposta para a tonalidade escolhida.
        desloc = deslocamento_para_do(tonalidade)
        tonalidade_modelo = "Dó Maior"
        acordes_modelo = [
            dict(a, classes_pitch=[(c - desloc) % 12 for c in a["classes_pitch"]]) for a in acordes
        ]

        # Estima tokens necessários (~2 notas por segundo = 4 tokens)
        num_tokens_alvo = int(duracao_seg * 2 * 2) + 8
        tokens_brutos = []

        if "Transformer" in tipo_modelo:
            modelo = self.carregar_transformer()
            if modelo is not None and self.vocabulario is not None:
                tokens_brutos = self._gerar_neural(
                    modelo, acordes_modelo, tonalidade_modelo, num_tokens_alvo, temperatura, guiar_por_harmonia
                )
            else:
                tipo_modelo += " (Fallback: Markov acionado)"
                tokens_brutos = self._gerar_com_markov(num_tokens_alvo)

        elif "LSTM" in tipo_modelo:
            modelo = self.carregar_lstm()
            if modelo is not None and self.vocabulario is not None:
                # A LSTM pode escolher durações curtas e acabar antes: gera até cobrir a duração pedida
                tokens_brutos = self._gerar_neural(
                    modelo, acordes_modelo, tonalidade_modelo, num_tokens_alvo * 8, temperatura, guiar_por_harmonia,
                    beats_alvo=duracao_seg * bpm / 60.0,
                )
            else:
                tipo_modelo += " (Fallback: Markov acionado)"
                tokens_brutos = self._gerar_com_markov(num_tokens_alvo)

        else:
            tokens_brutos = self._gerar_com_markov(num_tokens_alvo)

        # 3. Teoria Musical e Harmonização
        tokens_harmonizados = filtrar_tokens_por_tonalidade(
            transpor_tokens(filtrar_tokens_por_tonalidade(tokens_brutos, tonalidade_modelo), desloc),
            tonalidade,
        )
        tokens_finais = limitar_duracao(tokens_harmonizados, bpm, duracao_seg)

        # 4. Construção do MIDI Multifaixa
        prog_melodia = PROGRAMAS_GM.get(instrumento_melodia, 0)
        prog_acordes = PROGRAMAS_GM.get(instrumento_acordes, 4)

        caminho_mid = construir_midi_completo(
            tokens_melodia=tokens_finais,
            acordes_base=acordes,
            bpm=bpm,
            caminho_saida=caminho_saida_midi,
            programa_melodia=prog_melodia,
            programa_acordes=prog_acordes,
        )

        # 5. Renderização de Áudio
        caminho_wav = renderizar(caminho_mid)

        # 6. Estatísticas
        notas_melodia = [t for t in tokens_finais if t.startswith("NOTE_")]
        pitches = []
        for n in notas_melodia:
            try:
                pitches.append(int(n.split("_")[1]))
            except ValueError:
                pass

        nota_grave = pitch_para_nome(min(pitches)) if pitches else "N/A"
        nota_aguda = pitch_para_nome(max(pitches)) if pitches else "N/A"

        return {
            "caminho_midi": caminho_mid,
            "caminho_wav": caminho_wav,
            "acordes": acordes,
            "aviso_progressao": resolver_progressao(tonalidade, estilo_progressao)[3],
            "tokens": tokens_finais,
            "num_notas": len(notas_melodia),
            "num_acordes": len(acordes),
            "tonalidade": tonalidade,
            "bpm": bpm,
            "duracao_solicitada": duracao_seg,
            "modelo_usado": tipo_modelo,
            "nota_grave": nota_grave,
            "nota_aguda": nota_aguda,
        }

    def _gerar_neural(
        self,
        modelo: Any,
        acordes: List[Dict],
        tonalidade: str,
        num_tokens: int,
        temperatura: float,
        guiar_por_harmonia: bool,
        beats_alvo: Optional[float] = None,
    ) -> List[str]:
        # Os IDs só fazem sentido com o vocabulário usado no treino do checkpoint
        vocab = getattr(modelo, "vocabulario", None) or self.vocabulario
        token_para_id = vocab["token_para_id"]
        id_para_token = vocab["id_para_token"]
        # Só o Transformer sai do tempo da base (medido em contexto/008); a LSTM fica sem ajuste de ritmo
        peso_ritmo = 3.0 if type(modelo).__name__ == "MusicTransformer" else 0.0
        guia = (criar_guia_harmonico(token_para_id, acordes, tonalidade, peso_ritmo=peso_ritmo)
                if guiar_por_harmonia else None)
        extra = {"beats_alvo": beats_alvo} if beats_alvo is not None else {}
        return modelo.gerar(
            token_para_id=token_para_id,
            id_para_token=id_para_token,
            num_tokens=num_tokens,
            temperatura=temperatura,
            ajustar_logits=guia,
            **extra,
        )

    def _gerar_com_markov(self, num_tokens: int) -> List[str]:
        modelo = self.carregar_markov()
        if modelo is None:
            # Fallback seguro caso o pickle ainda não tenha sido gerado
            return ["NOTE_60", "DURATION_0.50", "NOTE_62", "DURATION_0.50",
                    "NOTE_64", "DURATION_0.50", "NOTE_67", "DURATION_0.50"] * (num_tokens // 8 + 1)
        return modelo.gerar(num_tokens=num_tokens)
