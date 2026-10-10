"""Geração dos áudios que faltam no cache."""

from __future__ import annotations

import io
import wave
from datetime import datetime, timezone
from typing import Callable

from .cache import Cache, normalizar_texto
from .elevenlabs import ClienteElevenLabs
from .plano import Plano
from .roteiro import Fala


class ErroGeracao(RuntimeError):
    pass


def pcm_para_wav(pcm: bytes, taxa: int) -> bytes:
    """A ElevenLabs entrega PCM cru, 16 bits, mono. Embrulha em WAV."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        w.writeframes(pcm)
    return buf.getvalue()


def _taxa_do_formato(formato: str) -> int:
    try:
        return int(formato.split("_")[1])
    except (IndexError, ValueError) as e:
        raise ErroGeracao(f"Não entendi a taxa de amostragem do formato '{formato}'.") from e


def _metadados(fala: Fala, headers: dict[str, str]) -> dict:
    return {
        "texto": normalizar_texto(fala.texto),
        "rotulo": fala.rotulo,
        "bloco": fala.oracao,
        "variante": fala.variante,
        "voz": fala.voz,
        "modelo": fala.modelo,
        "ajustes": fala.ajustes,
        "formato": fala.formato,
        "seed": fala.seed,
        "idioma": fala.idioma,
        "caracteres": fala.caracteres,
        "request_id": headers.get("request-id"),
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def gerar_faltantes(
    plano: Plano,
    cliente: ClienteElevenLabs,
    cache: Cache,
    max_caracteres: int,
    log: Callable[[str], None] = print,
) -> int:
    """Gera só o que não está no cache. Devolve quantos áudios foram gerados."""
    if not plano.pode_gerar:
        raise ErroGeracao(
            "O roteiro tem pendências (veja `narrar plano`). Nada foi gerado."
        )
    if plano.caracteres_a_gerar > max_caracteres:
        raise ErroGeracao(
            f"Faltam {plano.caracteres_a_gerar} caracteres, acima do limite de segurança de "
            f"{max_caracteres}. Use --max-caracteres para aumentar, se for isso mesmo."
        )

    faltantes = plano.a_gerar
    for i, (chave, fala) in enumerate(faltantes, start=1):
        log(f"[{i}/{len(faltantes)}] {fala.rotulo} ({fala.caracteres} caracteres)")
        audio, headers = cliente.tts(fala)
        if fala.formato.startswith("pcm_"):
            audio = pcm_para_wav(audio, _taxa_do_formato(fala.formato))
        cache.salvar(chave, fala.ext, audio, _metadados(fala, headers))
        plano.em_cache.add(chave)
    return len(faltantes)
