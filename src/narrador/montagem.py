"""Montagem: junta os clipes do cache, na ordem do roteiro, numa trilha única.

Saídas em saida/<roteiro>/:
  narracao.wav     trilha de narração com as pausas (mono, 44,1 kHz)
  narracao.mp3     a mesma trilha em MP3 (se o ffmpeg estiver instalado)
  manifesto.json   início/fim de cada fala, para sincronizar imagens no editor
  legendas.srt     o texto de cada fala com tempo, importável em qualquer editor
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

from .cache import Cache, normalizar_texto
from .plano import Plano

TAXA = 44_100
CANAIS = 1
BYTES_AMOSTRA = 2


class ErroMontagem(RuntimeError):
    pass


def _ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def _ler_frames(caminho: Path, tmp: Path) -> bytes:
    if caminho.suffix == ".wav":
        with wave.open(str(caminho), "rb") as w:
            if (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (CANAIS, BYTES_AMOSTRA, TAXA):
                return w.readframes(w.getnframes())
    ffmpeg = _ffmpeg()
    if not ffmpeg:
        raise ErroMontagem(
            f"Para ler {caminho.name} é preciso o ffmpeg instalado (https://ffmpeg.org/download.html)."
        )
    destino = tmp / f"{caminho.stem}.wav"
    subprocess.run(
        [ffmpeg, "-v", "error", "-y", "-i", str(caminho),
         "-ac", str(CANAIS), "-ar", str(TAXA), "-sample_fmt", "s16", str(destino)],
        check=True,
    )
    with wave.open(str(destino), "rb") as w:
        return w.readframes(w.getnframes())


def _tempo_srt(segundos: float) -> str:
    ms = round(segundos * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def montar(plano: Plano, cache: Cache, pasta_saida: str | Path, mp3: bool = True) -> dict[str, Any]:
    faltando = [f.rotulo for c, f in plano.unicas.items() if c not in plano.em_cache]
    if faltando:
        raise ErroMontagem(
            "Ainda faltam áudios no cache: " + ", ".join(faltando[:5])
            + ("..." if len(faltando) > 5 else "") + ". Rode `narrar gerar` antes."
        )

    saida = Path(pasta_saida)
    saida.mkdir(parents=True, exist_ok=True)
    trilha = saida / "narracao.wav"
    falas = plano.roteiro.falas
    itens: list[dict[str, Any]] = []
    decodificados: dict[str, bytes] = {}
    cursor = 0  # em frames

    with tempfile.TemporaryDirectory() as tmpdir, wave.open(str(trilha), "wb") as out:
        out.setnchannels(CANAIS)
        out.setsampwidth(BYTES_AMOSTRA)
        out.setframerate(TAXA)
        for i, fala in enumerate(falas):
            chave = fala.chave
            if chave not in decodificados:
                decodificados[chave] = _ler_frames(cache.caminho(chave, fala.ext), Path(tmpdir))
            frames = decodificados[chave]
            n_frames = len(frames) // (CANAIS * BYTES_AMOSTRA)
            inicio = cursor / TAXA
            out.writeframes(frames)
            cursor += n_frames
            fim = cursor / TAXA
            ultima = i == len(falas) - 1
            pausa = 0.0 if ultima else fala.pausa_depois
            if pausa > 0:
                n_silencio = round(pausa * TAXA)
                out.writeframes(b"\x00" * n_silencio * CANAIS * BYTES_AMOSTRA)
                cursor += n_silencio
            itens.append({
                "ordem": fala.ordem,
                "rotulo": fala.rotulo,
                "oracao": fala.oracao,
                "variante": fala.variante,
                "texto": normalizar_texto(fala.texto),
                "arquivo_cache": str(cache.caminho(chave, fala.ext)),
                "inicio_s": round(inicio, 3),
                "fim_s": round(fim, 3),
                "pausa_depois_s": pausa,
            })

    manifesto = {
        "roteiro": plano.roteiro.id,
        "titulo": plano.roteiro.titulo,
        "faixa": trilha.name,
        "taxa_hz": TAXA,
        "duracao_total_s": round(cursor / TAXA, 3),
        "falas": itens,
    }
    (saida / "manifesto.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    blocos = [
        f"{n}\n{_tempo_srt(it['inicio_s'])} --> {_tempo_srt(it['fim_s'])}\n{it['texto']}\n"
        for n, it in enumerate(itens, start=1)
    ]
    (saida / "legendas.srt").write_text("\n".join(blocos), encoding="utf-8")

    ffmpeg = _ffmpeg()
    if mp3 and ffmpeg:
        subprocess.run(
            [ffmpeg, "-v", "error", "-y", "-i", str(trilha),
             "-codec:a", "libmp3lame", "-b:a", "128k", str(saida / "narracao.mp3")],
            check=True,
        )
        manifesto["faixa_mp3"] = "narracao.mp3"
    return manifesto
