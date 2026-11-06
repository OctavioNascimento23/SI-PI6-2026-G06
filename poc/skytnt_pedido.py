"""Pede um MIDI ao processo do SkyTNT sem carregar a GPU nesta página."""

import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
_PROC = None
_LOG = None


def _fechar():
    global _PROC
    proc = _PROC
    _PROC = None
    if proc is not None and proc.poll() is None:
        proc.kill()


def _abrir():
    global _PROC, _LOG
    if _PROC is not None and _PROC.poll() is None:
        return _PROC
    pasta = RAIZ / "poc" / "saida_temp"
    pasta.mkdir(parents=True, exist_ok=True)
    _LOG = open(pasta / "skytnt_worker.log", "a", encoding="utf-8")
    _PROC = subprocess.Popen(
        [sys.executable, str(RAIZ / "poc" / "skytnt_worker.py")],
        cwd=str(RAIZ),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=_LOG,
        text=True,
        bufsize=1,
    )
    return _PROC


def pedir_geracao(tonalidade, bpm, duracao, temperatura, caminho) -> dict:
    """Gera o MIDI e devolve o resumo das faixas. O modelo fica no outro processo."""
    proc = _abrir()
    pedido = json.dumps(
        {
            "tonalidade": tonalidade,
            "bpm": int(bpm),
            "duracao": float(duracao),
            "temperatura": float(temperatura),
            "caminho": caminho,
        },
        ensure_ascii=False,
    )
    try:
        proc.stdin.write(pedido + "\n")
        proc.stdin.flush()
        linha = proc.stdout.readline()
    except Exception as exc:
        _fechar()
        raise RuntimeError(f"O gerador SkyTNT interrompeu: {exc}") from exc
    if not linha:
        _fechar()
        raise RuntimeError("O gerador SkyTNT encerrou antes de devolver o MIDI.")
    resposta = json.loads(linha)
    if not resposta.get("ok"):
        raise RuntimeError(resposta.get("erro", "falha na geração"))
    return resposta["resumo"]
