"""Plano de geração (o "dry-run"): o que já está pago, o que falta e quanto custa.

Nada aqui chama a API de geração. O saldo da conta, quando disponível, vem de
um endpoint que não gasta créditos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .cache import Cache
from .roteiro import CREDITOS_POR_CARACTERE, Fala, Roteiro


@dataclass
class Plano:
    roteiro: Roteiro
    unicas: dict[str, Fala]  # chave -> primeira fala com aquele áudio
    em_cache: set[str]
    saldo: dict[str, Any] | None = None
    avisos: list[str] = field(default_factory=list)

    @property
    def a_gerar(self) -> list[tuple[str, Fala]]:
        return [(c, f) for c, f in self.unicas.items() if c not in self.em_cache]

    @property
    def caracteres_sem_reuso(self) -> int:
        return sum(f.caracteres for f in self.roteiro.falas)

    @property
    def caracteres_unicos(self) -> int:
        return sum(f.caracteres for f in self.unicas.values())

    @property
    def caracteres_a_gerar(self) -> int:
        return sum(f.caracteres for _, f in self.a_gerar)

    @property
    def creditos_estimados(self) -> float:
        return sum(f.caracteres * CREDITOS_POR_CARACTERE.get(f.modelo, 1.0) for _, f in self.a_gerar)

    @property
    def pode_gerar(self) -> bool:
        return not self.roteiro.pendencias


def montar_plano(roteiro: Roteiro, cache: Cache) -> Plano:
    unicas: dict[str, Fala] = {}
    for fala in roteiro.falas:
        unicas.setdefault(fala.chave, fala)
    em_cache = {c for c, f in unicas.items() if cache.existe(c, f.ext)}
    return Plano(roteiro=roteiro, unicas=unicas, em_cache=em_cache)


def _n(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def relatorio(plano: Plano) -> str:
    r = plano.roteiro
    linhas = [
        f"Roteiro: {r.titulo} ({r.id})",
        f"  Falas na ordem do vídeo: {len(r.falas):>5}   ({_n(plano.caracteres_sem_reuso)} caracteres se gerasse tudo)",
        f"  Áudios únicos:           {len(plano.unicas):>5}   ({_n(plano.caracteres_unicos)} caracteres)",
        f"  Já no cache (pagos):     {len(plano.em_cache):>5}",
        f"  A gerar agora:           {len(plano.a_gerar):>5}   ({_n(plano.caracteres_a_gerar)} caracteres"
        f" ≈ {_n(plano.creditos_estimados)} créditos, estimativa)",
    ]
    if plano.caracteres_sem_reuso:
        economia = 1 - plano.caracteres_unicos / plano.caracteres_sem_reuso
        linhas.append(f"  Economia pela biblioteca de orações: {economia:.0%}")

    if plano.saldo:
        usado = plano.saldo.get("character_count")
        limite = plano.saldo.get("character_limit")
        if isinstance(usado, int) and isinstance(limite, int):
            restante = limite - usado
            linhas.append(f"  Saldo na conta: {_n(restante)} de {_n(limite)} caracteres")
            if plano.creditos_estimados > restante:
                linhas.append("  ATENÇÃO: o saldo não cobre o que falta gerar.")

    if plano.a_gerar:
        linhas.append("")
        linhas.append("  Faltam gerar:")
        for _, f in plano.a_gerar:
            var = f" [variante {f.variante + 1}/{f.total_variantes}]" if f.total_variantes else ""
            linhas.append(f"    - {f.rotulo}{var}: {f.caracteres} caracteres")

    if r.pendencias:
        linhas.append("")
        linhas.append("  Pendências (a geração fica bloqueada até resolver):")
        linhas.extend(f"    - {p}" for p in r.pendencias)

    for aviso in plano.avisos:
        linhas.append(f"  Aviso: {aviso}")
    return "\n".join(linhas)
