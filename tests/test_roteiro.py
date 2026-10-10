import unittest

from narrador.roteiro import ErroRoteiro, carregar_biblioteca, carregar_roteiro

from auxiliares import ComPastaTemporaria


class TestRoteiro(ComPastaTemporaria):
    def carregar(self, conteudo=None):
        caminho = self.escrever_roteiro(conteudo) if conteudo else self.escrever_roteiro()
        return carregar_roteiro(caminho, carregar_biblioteca(self.biblioteca_dir))

    def test_expande_na_ordem(self):
        r = self.carregar()
        rotulos = [f.rotulo for f in r.falas]
        self.assertEqual(rotulos, ["abertura", "pai_nosso", "ave_maria (1/3)", "ave_maria (2/3)",
                                   "ave_maria (3/3)", "fim"])
        self.assertEqual([f.ordem for f in r.falas], [1, 2, 3, 4, 5, 6])
        self.assertEqual(r.pendencias, [])

    def test_variantes_alternam_e_mudam_a_seed(self):
        r = self.carregar()
        aves = [f for f in r.falas if f.oracao == "ave_maria"]
        self.assertEqual([f.variante for f in aves], [0, 1, 0])
        self.assertEqual([f.seed for f in aves], [10, 11, 10])
        self.assertEqual(aves[0].chave, aves[2].chave)
        self.assertNotEqual(aves[0].chave, aves[1].chave)

    def test_variantes_continuam_entre_segmentos(self):
        r = self.carregar("""
            voz: v
            variantes: {ave_maria: 3}
            segmentos:
              - oracao: ave_maria
                repetir: 2
              - texto: "meio"
              - oracao: ave_maria
                repetir: 2
        """)
        aves = [f.variante for f in r.falas if f.oracao == "ave_maria"]
        self.assertEqual(aves, [0, 1, 2, 0])

    def test_segmento_sobrescreve_ajustes(self):
        r = self.carregar("""
            voz: v
            ajustes: {stability: 0.5, speed: 1.0}
            segmentos:
              - texto: "lento"
                ajustes: {speed: 0.8}
        """)
        self.assertEqual(r.falas[0].ajustes, {"stability": 0.5, "speed": 0.8})

    def test_oracao_inexistente(self):
        with self.assertRaises(ErroRoteiro):
            self.carregar("""
                voz: v
                segmentos:
                  - oracao: credo
            """)

    def test_texto_e_oracao_juntos_e_erro(self):
        with self.assertRaises(ErroRoteiro):
            self.carregar("""
                voz: v
                segmentos:
                  - oracao: ave_maria
                    texto: "x"
            """)

    def test_todo_e_voz_faltando_viram_pendencia(self):
        r = self.carregar("""
            voz: COLE_AQUI_O_ID
            segmentos:
              - id: saudacao
                texto: "TODO: copiar do livreto"
        """)
        self.assertEqual(len(r.pendencias), 2)

    def test_limite_de_caracteres_do_modelo(self):
        longo = "a" * 5001
        with self.assertRaises(ErroRoteiro):
            self.carregar(f"""
                voz: v
                modelo: eleven_v3
                segmentos:
                  - texto: "{longo}"
            """)

    def test_formato_invalido_falha_cedo(self):
        with self.assertRaises(ValueError):
            self.carregar("""
                voz: v
                formato: ulaw_8000
                segmentos:
                  - texto: "x"
            """)


class TestExemploDoRepositorio(unittest.TestCase):
    def test_exemplo_do_rosario_carrega(self):
        from pathlib import Path
        raiz = Path(__file__).resolve().parents[1]
        r = carregar_roteiro(raiz / "roteiros" / "rosario_sao_miguel.yaml",
                             carregar_biblioteca(raiz / "oracoes"))
        aves = [f for f in r.falas if f.oracao == "ave_maria"]
        pais = [f for f in r.falas if f.oracao == "pai_nosso"]
        self.assertEqual(len(aves), 27)
        self.assertEqual(len(pais), 13)
        self.assertTrue(r.pendencias)  # o exemplo vem com TODO de propósito


if __name__ == "__main__":
    unittest.main()
