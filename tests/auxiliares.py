"""Ferramentas comuns dos testes: biblioteca/roteiro temporários e uma API falsa."""

from __future__ import annotations

import json
import struct
import tempfile
import textwrap
import unittest
from pathlib import Path


def pcm_tom(segundos: float, taxa: int = 44_100) -> bytes:
    """PCM 16-bit mono não silencioso (para diferenciar de pausas)."""
    n = int(segundos * taxa)
    return b"".join(struct.pack("<h", 1000 if (i // 50) % 2 else -1000) for i in range(n))


class ApiFalsa:
    """Imita a ElevenLabs e registra cada chamada. Nunca acessa a rede."""

    def __init__(self, respostas_tts: list[int] | None = None, segundos: float = 0.5):
        self.chamadas: list[dict] = []
        self.status_tts = list(respostas_tts or [])
        self.segundos = segundos

    def __call__(self, metodo, url, headers, corpo):
        self.chamadas.append({"metodo": metodo, "url": url, "headers": headers,
                              "corpo": json.loads(corpo) if corpo else None})
        if "/v1/user/subscription" in url:
            return 200, {}, json.dumps({"tier": "creator", "character_count": 1000,
                                        "character_limit": 100000}).encode()
        if "/v1/voices" in url:
            return 200, {}, json.dumps({"voices": [{"voice_id": "abc", "name": "Teste"}]}).encode()
        if "/v1/text-to-speech/" in url:
            status = self.status_tts.pop(0) if self.status_tts else 200
            if status != 200:
                return status, {}, json.dumps({"detail": {"message": "erro simulado"}}).encode()
            return 200, {"request-id": f"req-{len(self.chamadas)}"}, pcm_tom(self.segundos)
        return 404, {}, b"{}"

    @property
    def tts(self) -> list[dict]:
        return [c for c in self.chamadas if "/v1/text-to-speech/" in c["url"]]


ROTEIRO_PADRAO = """
id: teste
titulo: Teste
voz: voz123
modelo: eleven_multilingual_v2
formato: pcm_44100
ajustes: {stability: 0.5, similarity_boost: 0.75, speed: 1}
seed: 10
pausa_padrao: 1.0
variantes:
  ave_maria: 2
segmentos:
  - id: abertura
    texto: "Em nome do Pai."
  - oracao: pai_nosso
  - oracao: ave_maria
    repetir: 3
  - id: fim
    texto: "Amém."
"""


class ComPastaTemporaria(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        bib = self.dir / "oracoes"
        bib.mkdir()
        (bib / "pai_nosso.yaml").write_text("id: pai_nosso\ntexto: Pai nosso, que estais nos céus.\n",
                                            encoding="utf-8")
        (bib / "ave_maria.yaml").write_text("id: ave_maria\ntexto: Ave Maria, cheia de graça.\n",
                                            encoding="utf-8")
        self.biblioteca_dir = bib
        self.cache_dir = self.dir / "cache"

    def tearDown(self):
        self._tmp.cleanup()

    def escrever_roteiro(self, conteudo: str = ROTEIRO_PADRAO, nome: str = "teste.yaml") -> Path:
        p = self.dir / nome
        p.write_text(textwrap.dedent(conteudo), encoding="utf-8")
        return p
