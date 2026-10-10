"""Cache endereçado por conteúdo.

O nome de cada arquivo de áudio é o SHA-256 de tudo que muda o som:
texto normalizado, voz, modelo, ajustes de voz, formato, seed e idioma.
Se o arquivo existe, o áudio já foi pago e não é gerado de novo.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

# Aumente se a forma de calcular a chave mudar (invalida o cache antigo de propósito).
VERSAO_CHAVE = 1


def normalizar_texto(texto: str) -> str:
    """Unicode NFC e espaços colapsados. Pontuação é preservada: ela muda a entonação."""
    t = unicodedata.normalize("NFC", texto)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _normalizar_ajustes(ajustes: dict[str, Any] | None) -> dict[str, Any]:
    """1 e 1.0 devem gerar a mesma chave; booleanos ficam como estão."""
    saida: dict[str, Any] = {}
    for nome, valor in (ajustes or {}).items():
        if isinstance(valor, bool) or valor is None:
            saida[nome] = valor
        elif isinstance(valor, (int, float)):
            saida[nome] = float(valor)
        else:
            saida[nome] = valor
    return saida


def chave_cache(
    texto: str,
    voz: str,
    modelo: str,
    ajustes: dict[str, Any] | None,
    formato: str,
    seed: int | None = None,
    idioma: str | None = None,
) -> str:
    dados = {
        "v": VERSAO_CHAVE,
        "texto": normalizar_texto(texto),
        "voz": voz,
        "modelo": modelo,
        "ajustes": _normalizar_ajustes(ajustes),
        "formato": formato,
        "seed": seed,
        "idioma": idioma,
    }
    bruto = json.dumps(dados, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def extensao_do_formato(formato: str) -> str:
    """Extensão do arquivo salvo. PCM cru é embrulhado em WAV para abrir em qualquer editor."""
    if formato.startswith("mp3_"):
        return ".mp3"
    if formato.startswith("pcm_") or formato.startswith("wav_"):
        return ".wav"
    raise ValueError(
        f"Formato de saída '{formato}' ainda não suportado. Use mp3_* (ex.: mp3_44100_128) ou pcm_*."
    )


def _escrever_atomico(destino: Path, dados: bytes) -> None:
    """Escreve num temporário e renomeia: um corte no meio nunca deixa arquivo pela metade no cache."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=destino.parent, prefix=".tmp-", suffix=destino.suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(dados)
        os.replace(tmp, destino)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class Cache:
    def __init__(self, raiz: str | Path):
        self.raiz = Path(raiz)

    def caminho(self, chave: str, ext: str) -> Path:
        return self.raiz / chave[:2] / f"{chave}{ext}"

    def caminho_meta(self, chave: str) -> Path:
        return self.raiz / chave[:2] / f"{chave}.json"

    def existe(self, chave: str, ext: str) -> bool:
        p = self.caminho(chave, ext)
        return p.is_file() and p.stat().st_size > 0

    def salvar(self, chave: str, ext: str, audio: bytes, meta: dict[str, Any]) -> Path:
        if not audio:
            raise ValueError("Áudio vazio não é salvo no cache.")
        destino = self.caminho(chave, ext)
        _escrever_atomico(destino, audio)
        meta_bytes = json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8")
        _escrever_atomico(self.caminho_meta(chave), meta_bytes)
        return destino

    def meta(self, chave: str) -> dict[str, Any] | None:
        p = self.caminho_meta(chave)
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
