import io
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from narrador import cli

from auxiliares import ComPastaTemporaria

RAIZ = Path(__file__).resolve().parents[1]


def rodar(*args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        codigo = cli.main(list(args))
    return codigo, out.getvalue(), err.getvalue()


class TestCli(ComPastaTemporaria):
    def setUp(self):
        super().setUp()
        self._env = mock.patch.dict(os.environ, {}, clear=False)
        self._env.start()
        os.environ.pop("ELEVENLABS_API_KEY", None)

    def tearDown(self):
        self._env.stop()
        super().tearDown()

    def test_plano_do_exemplo_sem_chave(self):
        codigo, out, _ = rodar("plano", str(RAIZ / "roteiros" / "rosario_sao_miguel.yaml"),
                               "--biblioteca", str(RAIZ / "oracoes"), "--cache", str(self.cache_dir))
        self.assertEqual(codigo, 0)
        self.assertIn("Economia pela biblioteca", out)
        self.assertIn("Pendências", out)
        self.assertIn("sem ELEVENLABS_API_KEY", out)

    def test_gerar_com_pendencia_nao_gasta(self):
        codigo, _, err = rodar("gerar", str(RAIZ / "roteiros" / "rosario_sao_miguel.yaml"),
                               "--biblioteca", str(RAIZ / "oracoes"), "--cache", str(self.cache_dir),
                               "--sim")
        self.assertEqual(codigo, 2)
        self.assertIn("pendências", err)
        self.assertFalse(self.cache_dir.exists())

    def test_roteiro_com_erro_vira_mensagem(self):
        r = self.escrever_roteiro("voz: v\nsegmentos:\n  - oracao: inexistente\n")
        codigo, _, err = rodar("plano", str(r), "--biblioteca", str(self.biblioteca_dir))
        self.assertEqual(codigo, 2)
        self.assertIn("inexistente", err)

    def test_biblioteca_declarada_no_roteiro(self):
        outra = self.dir / "bibliotecas" / "curso"
        outra.mkdir(parents=True)
        (outra / "vinheta.yaml").write_text("id: vinheta\ntexto: Bem-vindo ao curso.\n", encoding="utf-8")
        r = self.escrever_roteiro(f"id: aula\nvoz: v\nbiblioteca: {outra}\n"
                                  "segmentos:\n  - bloco: vinheta\n  - texto: Aula 1.\n")
        codigo, out, err = rodar("plano", str(r), "--cache", str(self.cache_dir))
        self.assertEqual(codigo, 0, err)
        self.assertIn("vinheta", out)

    def test_carregar_env_nao_sobrescreve(self):
        env = self.dir / ".env"
        env.write_text('# comentário\nELEVENLABS_API_KEY="do-arquivo"\nOUTRA=1\n', encoding="utf-8")
        os.environ["OUTRA"] = "do-ambiente"
        cli.carregar_env(env)
        self.assertEqual(os.environ["ELEVENLABS_API_KEY"], "do-arquivo")
        self.assertEqual(os.environ["OUTRA"], "do-ambiente")


if __name__ == "__main__":
    unittest.main()
