"""
Módulo de Modelos de Inteligência Artificial e Aprendizado de Máquina.
"""
from .markov import ModeloMarkov

try:
    from .lstm_model import MelodyLSTM
except ImportError:
    MelodyLSTM = None

try:
    from .transformer_model import MusicTransformer
except ImportError:
    MusicTransformer = None

__all__ = ["ModeloMarkov", "MelodyLSTM", "MusicTransformer"]
