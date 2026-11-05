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
    filtrar_tokens_por_tonalidade,
    pitch_para_nome,
)
from src.midi_builder import construir_midi_completo, limitar_duracao, PROGRAMAS_GM
from src.audio_renderer import renderizar
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
        if self.caminho_vocab.exists():
            try:
                dados = json.loads(self.caminho_vocab.read_text(encoding="utf-8"))
                self.vocabulario = dados
                self.token_para_id = dados.get("token_para_id", {})
                self.id_para_token = dados.get("id_para_token", {})
            except Exception as e:
                print(f"Aviso ao carregar vocabulário: {e}")

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
        # Estima tokens necessários (~2 notas por segundo = 4 tokens)
        num_tokens_alvo = int(duracao_seg * 2 * 2) + 8
        tokens_brutos = []

        if "Transformer" in tipo_modelo:
            modelo = self.carregar_transformer()
            if modelo is not None and self.vocabulario is not None:
                tokens_brutos = modelo.gerar(
                    token_para_id=self.token_para_id,
                    id_para_token=self.id_para_token,
                    num_tokens=num_tokens_alvo,
                    temperatura=temperatura,
                )
            else:
                tipo_modelo += " (Fallback: Markov acionado)"
                tokens_brutos = self._gerar_com_markov(num_tokens_alvo)

        elif "LSTM" in tipo_modelo:
            modelo = self.carregar_lstm()
            if modelo is not None and self.vocabulario is not None:
                tokens_brutos = modelo.gerar(
                    token_para_id=self.token_para_id,
                    id_para_token=self.id_para_token,
                    num_tokens=num_tokens_alvo,
                    temperatura=temperatura,
                )
            else:
                tipo_modelo += " (Fallback: Markov acionado)"
                tokens_brutos = self._gerar_com_markov(num_tokens_alvo)

        else:
            tokens_brutos = self._gerar_com_markov(num_tokens_alvo)

        # 3. Teoria Musical e Harmonização
        tokens_harmonizados = filtrar_tokens_por_tonalidade(tokens_brutos, tonalidade)
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

    def _gerar_com_markov(self, num_tokens: int) -> List[str]:
        modelo = self.carregar_markov()
        if modelo is None:
            # Fallback seguro caso o pickle ainda não tenha sido gerado
            return ["NOTE_60", "DURATION_0.50", "NOTE_62", "DURATION_0.50",
                    "NOTE_64", "DURATION_0.50", "NOTE_67", "DURATION_0.50"] * (num_tokens // 8 + 1)
        return modelo.gerar(num_tokens=num_tokens)
