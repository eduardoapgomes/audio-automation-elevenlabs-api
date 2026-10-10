"""Leitura do roteiro YAML e da biblioteca de orações.

O roteiro declara a estrutura (que oração vem quando, quantas vezes); a biblioteca
guarda o texto de cada oração uma única vez para todos os vídeos do canal.
O resultado é uma lista plana de `Fala`, na ordem em que serão ouvidas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .cache import chave_cache, extensao_do_formato, normalizar_texto

# Caracteres por requisição, por modelo (docs ElevenLabs, out/2026).
LIMITE_CARACTERES = {
    "eleven_v3": 5_000,
    "eleven_multilingual_v2": 10_000,
    "eleven_flash_v2_5": 40_000,
    "eleven_flash_v2": 30_000,
}

# Créditos por caractere na API (Flash custa metade). Estimativa: confira no seu plano.
CREDITOS_POR_CARACTERE = {
    "eleven_flash_v2_5": 0.5,
    "eleven_flash_v2": 0.5,
}

MARCADORES_PENDENTES = ("TODO", "COLE_AQUI")

FORMATO_PADRAO = "mp3_44100_128"


class ErroRoteiro(ValueError):
    pass


@dataclass(frozen=True)
class Fala:
    ordem: int
    rotulo: str
    texto: str
    voz: str
    modelo: str
    ajustes: dict[str, Any]
    formato: str
    seed: int | None
    idioma: str | None
    pausa_depois: float
    oracao: str | None = None
    variante: int | None = None
    total_variantes: int | None = None

    @property
    def chave(self) -> str:
        return chave_cache(
            self.texto, self.voz, self.modelo, self.ajustes, self.formato, self.seed, self.idioma
        )

    @property
    def ext(self) -> str:
        return extensao_do_formato(self.formato)

    @property
    def caracteres(self) -> int:
        return len(normalizar_texto(self.texto))


@dataclass
class Roteiro:
    id: str
    titulo: str
    falas: list[Fala]
    pendencias: list[str] = field(default_factory=list)


def carregar_biblioteca(pasta: str | Path) -> dict[str, dict[str, Any]]:
    pasta = Path(pasta)
    if not pasta.is_dir():
        raise ErroRoteiro(f"Pasta da biblioteca de orações não encontrada: {pasta}")
    oracoes: dict[str, dict[str, Any]] = {}
    for arq in sorted(pasta.glob("*.y*ml")):
        dados = yaml.safe_load(arq.read_text(encoding="utf-8")) or {}
        oid = str(dados.get("id") or arq.stem)
        if "texto" not in dados or not str(dados["texto"]).strip():
            raise ErroRoteiro(f"Oração '{oid}' ({arq.name}) está sem texto.")
        if oid in oracoes:
            raise ErroRoteiro(f"Oração '{oid}' aparece duas vezes na biblioteca.")
        oracoes[oid] = dados
    return oracoes


def _pendencias_do_texto(rotulo: str, texto: str) -> list[str]:
    return [f"{rotulo}: texto ainda com marcador '{m}'" for m in MARCADORES_PENDENTES if m in texto]


def carregar_roteiro(caminho: str | Path, biblioteca: dict[str, dict[str, Any]]) -> Roteiro:
    caminho = Path(caminho)
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}

    rid = str(dados.get("id") or caminho.stem)
    titulo = str(dados.get("titulo") or rid)
    voz_padrao = str(dados.get("voz") or "")
    modelo_padrao = str(dados.get("modelo") or "eleven_multilingual_v2")
    formato_padrao = str(dados.get("formato") or FORMATO_PADRAO)
    ajustes_padrao = dict(dados.get("ajustes") or {})
    idioma_padrao = dados.get("idioma")
    seed_base = int(dados.get("seed", 1))
    pausa_padrao = float(dados.get("pausa_padrao", 1.0))
    variantes_por_oracao = {str(k): int(v) for k, v in (dados.get("variantes") or {}).items()}
    segmentos = dados.get("segmentos") or []

    if not segmentos:
        raise ErroRoteiro(f"Roteiro '{rid}' não tem segmentos.")
    extensao_do_formato(formato_padrao)  # valida cedo

    pendencias: list[str] = []
    if not voz_padrao or any(m in voz_padrao for m in MARCADORES_PENDENTES):
        pendencias.append("roteiro: falta o ID da voz (campo 'voz')")

    for oid, n in variantes_por_oracao.items():
        if oid not in biblioteca:
            raise ErroRoteiro(f"'variantes' cita a oração '{oid}', que não está na biblioteca.")
        if n < 1:
            raise ErroRoteiro(f"'variantes' de '{oid}' precisa ser 1 ou mais.")

    contador_oracao: dict[str, int] = {}
    falas: list[Fala] = []

    for i, seg in enumerate(segmentos, start=1):
        if not isinstance(seg, dict):
            raise ErroRoteiro(f"Segmento {i} precisa ser um mapa (chave: valor).")
        tem_texto = "texto" in seg
        tem_oracao = "oracao" in seg
        if tem_texto == tem_oracao:
            raise ErroRoteiro(f"Segmento {i}: use exatamente um de 'texto' ou 'oracao'.")

        repetir = int(seg.get("repetir", 1))
        if repetir < 1:
            raise ErroRoteiro(f"Segmento {i}: 'repetir' precisa ser 1 ou mais.")

        voz = str(seg.get("voz") or voz_padrao)
        modelo = str(seg.get("modelo") or modelo_padrao)
        formato = str(seg.get("formato") or formato_padrao)
        ajustes = {**ajustes_padrao, **dict(seg.get("ajustes") or {})}
        idioma = seg.get("idioma", idioma_padrao)
        pausa = float(seg.get("pausa_depois", pausa_padrao))

        if tem_oracao:
            oid = str(seg["oracao"])
            if oid not in biblioteca:
                raise ErroRoteiro(f"Segmento {i}: oração '{oid}' não existe na biblioteca.")
            texto = str(biblioteca[oid]["texto"])
            rotulo_base = str(seg.get("id") or oid)
        else:
            oid = None
            texto = str(seg["texto"])
            rotulo_base = str(seg.get("id") or f"segmento_{i}")

        if not texto.strip():
            raise ErroRoteiro(f"Segmento {i} ({rotulo_base}): texto vazio.")
        pendencias.extend(_pendencias_do_texto(rotulo_base, texto))

        limite = LIMITE_CARACTERES.get(modelo)
        if limite and len(normalizar_texto(texto)) > limite:
            raise ErroRoteiro(
                f"Segmento {i} ({rotulo_base}): {len(normalizar_texto(texto))} caracteres, "
                f"acima do limite de {limite} do modelo {modelo}. Divida em segmentos menores."
            )

        for r in range(repetir):
            variante = total = None
            seed = seed_base
            if oid is not None:
                n_var = variantes_por_oracao.get(oid, 1)
                k = contador_oracao.get(oid, 0)
                contador_oracao[oid] = k + 1
                if n_var > 1:
                    variante = k % n_var
                    total = n_var
                    seed = seed_base + variante
            rotulo = rotulo_base if repetir == 1 else f"{rotulo_base} ({r + 1}/{repetir})"
            falas.append(
                Fala(
                    ordem=len(falas) + 1,
                    rotulo=rotulo,
                    texto=texto,
                    voz=voz,
                    modelo=modelo,
                    ajustes=ajustes,
                    formato=formato,
                    seed=seed,
                    idioma=idioma,
                    pausa_depois=pausa,
                    oracao=oid,
                    variante=variante,
                    total_variantes=total,
                )
            )

    return Roteiro(id=rid, titulo=titulo, falas=falas, pendencias=pendencias)
