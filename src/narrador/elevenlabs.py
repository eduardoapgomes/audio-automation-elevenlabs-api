"""Cliente mínimo da API ElevenLabs, só com a biblioteca padrão.

O transporte HTTP é injetável: os testes usam um transporte falso e nunca
gastam créditos.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from .cache import normalizar_texto
from .roteiro import Fala

API = "https://api.elevenlabs.io"

# (metodo, url, headers, corpo) -> (status, headers, corpo)
Transporte = Callable[[str, str, dict[str, str], bytes | None], tuple[int, dict[str, str], bytes]]

STATUS_REPETIR = {429, 500, 502, 503, 504}


class ErroAPI(RuntimeError):
    def __init__(self, mensagem: str, status: int | None = None):
        super().__init__(mensagem)
        self.status = status


def transporte_urllib(
    metodo: str, url: str, headers: dict[str, str], corpo: bytes | None, timeout: float = 180
) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url, data=corpo, method=metodo, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read()


def _resumo_erro(corpo: bytes) -> str:
    try:
        dados = json.loads(corpo)
        detalhe = dados.get("detail", dados)
        if isinstance(detalhe, dict):
            return str(detalhe.get("message") or detalhe.get("status") or detalhe)[:300]
        return str(detalhe)[:300]
    except (ValueError, AttributeError):
        return corpo[:300].decode("utf-8", "replace")


class ClienteElevenLabs:
    def __init__(
        self,
        api_key: str,
        transporte: Transporte | None = None,
        dormir: Callable[[float], None] = time.sleep,
        tentativas: int = 4,
        base: str = API,
    ):
        if not api_key:
            raise ErroAPI(
                "ELEVENLABS_API_KEY não definida. Coloque no arquivo .env (veja .env.example)."
            )
        self.api_key = api_key
        self.transporte = transporte or transporte_urllib
        self.dormir = dormir
        self.tentativas = tentativas
        self.base = base.rstrip("/")

    def _requisicao(
        self, metodo: str, caminho: str, corpo: dict[str, Any] | None = None, aceitar: str = "*/*"
    ) -> tuple[dict[str, str], bytes]:
        url = f"{self.base}{caminho}"
        headers = {"xi-api-key": self.api_key, "accept": aceitar}
        dados = None
        if corpo is not None:
            headers["content-type"] = "application/json"
            dados = json.dumps(corpo, ensure_ascii=False).encode("utf-8")

        ultimo = ""
        for tentativa in range(self.tentativas):
            status, h, resposta = self.transporte(metodo, url, headers, dados)
            if 200 <= status < 300:
                return h, resposta
            ultimo = _resumo_erro(resposta)
            if status == 401:
                raise ErroAPI(f"Chave da API recusada (401): {ultimo}", status)
            if status not in STATUS_REPETIR or tentativa == self.tentativas - 1:
                raise ErroAPI(f"ElevenLabs respondeu {status}: {ultimo}", status)
            espera = 2.0**tentativa
            if "retry-after" in h:
                try:
                    espera = max(espera, float(h["retry-after"]))
                except ValueError:
                    pass
            self.dormir(espera)
        raise ErroAPI(f"Falhou após {self.tentativas} tentativas: {ultimo}")  # pragma: no cover

    def tts(self, fala: Fala) -> tuple[bytes, dict[str, str]]:
        """Gera o áudio de uma fala. Cada chamada GASTA créditos."""
        corpo: dict[str, Any] = {
            "text": normalizar_texto(fala.texto),
            "model_id": fala.modelo,
            "voice_settings": fala.ajustes,
        }
        if fala.seed is not None:
            corpo["seed"] = fala.seed
        if fala.idioma:
            corpo["language_code"] = fala.idioma
        voz = urllib.parse.quote(fala.voz, safe="")
        formato = urllib.parse.quote(fala.formato, safe="")
        headers, audio = self._requisicao(
            "POST", f"/v1/text-to-speech/{voz}?output_format={formato}", corpo, aceitar="audio/*"
        )
        if not audio:
            raise ErroAPI(f"ElevenLabs devolveu áudio vazio para '{fala.rotulo}'.")
        return audio, headers

    def assinatura(self) -> dict[str, Any]:
        """Saldo de caracteres da conta. Não gasta créditos."""
        _, corpo = self._requisicao("GET", "/v1/user/subscription", aceitar="application/json")
        return json.loads(corpo)

    def vozes(self) -> list[dict[str, Any]]:
        """Vozes disponíveis na conta. Não gasta créditos."""
        _, corpo = self._requisicao("GET", "/v1/voices", aceitar="application/json")
        return list(json.loads(corpo).get("voices", []))
