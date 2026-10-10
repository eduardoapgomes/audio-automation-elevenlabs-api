"""Linha de comando `narrar`.

  narrar plano  roteiros/x.yaml   o que falta gerar e quanto custa (não gasta nada)
  narrar gerar  roteiros/x.yaml   gera só o que falta (gasta créditos, pede confirmação)
  narrar montar roteiros/x.yaml   junta tudo numa trilha + manifesto + legendas
  narrar saldo                    saldo da conta ElevenLabs (não gasta nada)
  narrar vozes                    lista as vozes da conta com seus IDs (não gasta nada)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .cache import Cache
from .elevenlabs import ClienteElevenLabs, ErroAPI
from .gerar import ErroGeracao, gerar_faltantes
from .montagem import ErroMontagem, montar
from .plano import montar_plano, relatorio
from .roteiro import ErroRoteiro, carregar_biblioteca, carregar_roteiro, ler_yaml_roteiro


def carregar_env(caminho: str | Path = ".env") -> None:
    """Lê KEY=VALOR de um .env simples, sem sobrescrever o que já está no ambiente."""
    p = Path(caminho)
    if not p.is_file():
        return
    for linha in p.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def _cliente() -> ClienteElevenLabs:
    return ClienteElevenLabs(os.environ.get("ELEVENLABS_API_KEY", ""))


def _pasta_biblioteca(args: argparse.Namespace) -> str:
    """--biblioteca na linha de comando > 'biblioteca:' no roteiro > pasta 'oracoes'."""
    if args.biblioteca:
        return args.biblioteca
    return str(ler_yaml_roteiro(args.roteiro).get("biblioteca") or "oracoes")


def _plano(args: argparse.Namespace):
    biblioteca = carregar_biblioteca(_pasta_biblioteca(args))
    roteiro = carregar_roteiro(args.roteiro, biblioteca)
    return montar_plano(roteiro, Cache(args.cache))


def cmd_plano(args: argparse.Namespace) -> int:
    plano = _plano(args)
    if os.environ.get("ELEVENLABS_API_KEY"):
        try:
            plano.saldo = _cliente().assinatura()
        except ErroAPI as e:
            plano.avisos.append(f"não consegui ler o saldo da conta ({e}).")
    else:
        plano.avisos.append("sem ELEVENLABS_API_KEY: saldo da conta não consultado.")
    print(relatorio(plano))
    return 0


def cmd_gerar(args: argparse.Namespace) -> int:
    plano = _plano(args)
    print(relatorio(plano))
    print()
    if not plano.a_gerar:
        print("Nada a gerar: tudo já está no cache.")
        return 0
    if not plano.pode_gerar:
        raise ErroGeracao("O roteiro tem pendências (listadas acima). Nada foi gerado.")
    if not args.sim:
        if not sys.stdin.isatty():
            raise ErroGeracao("Sem terminal para confirmar. Rode com --sim para gerar sem perguntar.")
        resposta = input(
            f"Gerar {len(plano.a_gerar)} áudio(s), {plano.caracteres_a_gerar} caracteres? [s/N] "
        )
        if resposta.strip().lower() not in {"s", "sim", "y", "yes"}:
            print("Cancelado. Nada foi gerado.")
            return 1
    n = gerar_faltantes(plano, _cliente(), Cache(args.cache), args.max_caracteres)
    print(f"Pronto: {n} áudio(s) gerado(s) e guardado(s) em {args.cache}/.")
    return 0


def cmd_montar(args: argparse.Namespace) -> int:
    plano = _plano(args)
    pasta = Path(args.saida) / plano.roteiro.id
    manifesto = montar(plano, Cache(args.cache), pasta, mp3=not args.sem_mp3)
    minutos, segundos = divmod(manifesto["duracao_total_s"], 60)
    print(f"Trilha montada: {pasta}/narracao.wav ({int(minutos)}min{segundos:04.1f}s)")
    print(f"Manifesto: {pasta}/manifesto.json   Legendas: {pasta}/legendas.srt")
    if "faixa_mp3" in manifesto:
        print(f"MP3: {pasta}/narracao.mp3")
    return 0


def cmd_saldo(args: argparse.Namespace) -> int:
    dados = _cliente().assinatura()
    usado, limite = dados.get("character_count"), dados.get("character_limit")
    print(f"Plano: {dados.get('tier', '?')}")
    if isinstance(usado, int) and isinstance(limite, int):
        print(f"Caracteres usados: {usado} de {limite} (restam {limite - usado})")
    return 0


def cmd_vozes(args: argparse.Namespace) -> int:
    for v in sorted(_cliente().vozes(), key=lambda v: str(v.get("name", "")).lower()):
        rotulos = v.get("labels") or {}
        extra = ", ".join(f"{k}: {val}" for k, val in rotulos.items() if val)
        print(f"{v.get('voice_id')}  {v.get('name')}" + (f"  ({extra})" if extra else ""))
    return 0


def criar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="narrar", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="comando", required=True)

    def com_roteiro(nome: str, ajuda: str) -> argparse.ArgumentParser:
        sp = sub.add_parser(nome, help=ajuda)
        sp.add_argument("roteiro", help="arquivo YAML do roteiro")
        sp.add_argument("--biblioteca", default=None,
                        help="pasta dos blocos reutilizáveis (padrão: campo 'biblioteca' do roteiro, "
                             "ou 'oracoes')")
        sp.add_argument("--cache", default="cache", help="pasta do cache de áudio (padrão: cache)")
        return sp

    com_roteiro("plano", "mostra o que falta gerar e o custo, sem gastar nada").set_defaults(func=cmd_plano)

    g = com_roteiro("gerar", "gera os áudios que faltam (gasta créditos)")
    g.add_argument("--sim", action="store_true", help="não pedir confirmação")
    g.add_argument("--max-caracteres", type=int, default=20_000,
                   help="trava de segurança: não gera se faltar mais que isso (padrão: 20000)")
    g.set_defaults(func=cmd_gerar)

    m = com_roteiro("montar", "monta a trilha, o manifesto e as legendas")
    m.add_argument("--saida", default="saida", help="pasta de saída (padrão: saida)")
    m.add_argument("--sem-mp3", action="store_true", help="não gerar narracao.mp3")
    m.set_defaults(func=cmd_montar)

    sub.add_parser("saldo", help="saldo da conta ElevenLabs").set_defaults(func=cmd_saldo)
    sub.add_parser("vozes", help="vozes da conta com seus IDs").set_defaults(func=cmd_vozes)
    return p


def main(argv: list[str] | None = None) -> int:
    carregar_env()
    args = criar_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ErroRoteiro, ErroAPI, ErroGeracao, ErroMontagem) as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
