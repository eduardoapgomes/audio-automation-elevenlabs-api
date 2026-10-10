import unittest

from narrador.cache import Cache, chave_cache, extensao_do_formato, normalizar_texto

from auxiliares import ComPastaTemporaria

BASE = dict(texto="Ave Maria, cheia de graça.", voz="v1", modelo="m1",
            ajustes={"stability": 0.5}, formato="mp3_44100_128", seed=1)


class TestChave(unittest.TestCase):
    def test_mesma_entrada_mesma_chave(self):
        self.assertEqual(chave_cache(**BASE), chave_cache(**BASE))

    def test_tudo_que_muda_o_som_muda_a_chave(self):
        original = chave_cache(**BASE)
        for campo, valor in [("voz", "v2"), ("modelo", "m2"), ("formato", "pcm_44100"),
                             ("seed", 2), ("ajustes", {"stability": 0.6}),
                             ("texto", "Ave Maria cheia de graça.")]:
            with self.subTest(campo=campo):
                self.assertNotEqual(original, chave_cache(**{**BASE, campo: valor}))
        self.assertNotEqual(original, chave_cache(**BASE, idioma="pt"))

    def test_espacos_e_quebras_de_linha_nao_mudam_a_chave(self):
        variacao = {**BASE, "texto": "  Ave Maria,\n  cheia   de graça. "}
        self.assertEqual(chave_cache(**BASE), chave_cache(**variacao))

    def test_pontuacao_muda_a_chave(self):
        self.assertNotEqual(chave_cache(**BASE), chave_cache(**{**BASE, "texto": "Ave Maria cheia de graça"}))

    def test_unicode_composto_e_decomposto_sao_iguais(self):
        decomposto = "Ave Maria, cheia de graça."
        self.assertEqual(chave_cache(**BASE), chave_cache(**{**BASE, "texto": decomposto}))

    def test_inteiro_e_float_equivalentes(self):
        a = chave_cache(**{**BASE, "ajustes": {"speed": 1}})
        b = chave_cache(**{**BASE, "ajustes": {"speed": 1.0}})
        self.assertEqual(a, b)

    def test_ordem_dos_ajustes_nao_importa(self):
        a = chave_cache(**{**BASE, "ajustes": {"stability": 0.5, "style": 0}})
        b = chave_cache(**{**BASE, "ajustes": {"style": 0, "stability": 0.5}})
        self.assertEqual(a, b)

    def test_normalizar(self):
        self.assertEqual(normalizar_texto(" a \n\t b "), "a b")


class TestExtensao(unittest.TestCase):
    def test_formatos(self):
        self.assertEqual(extensao_do_formato("mp3_44100_128"), ".mp3")
        self.assertEqual(extensao_do_formato("pcm_44100"), ".wav")
        with self.assertRaises(ValueError):
            extensao_do_formato("ulaw_8000")


class TestCacheEmDisco(ComPastaTemporaria):
    def test_salvar_e_encontrar(self):
        cache = Cache(self.cache_dir)
        chave = chave_cache(**BASE)
        self.assertFalse(cache.existe(chave, ".mp3"))
        caminho = cache.salvar(chave, ".mp3", b"audio", {"texto": "x"})
        self.assertTrue(cache.existe(chave, ".mp3"))
        self.assertEqual(caminho.parent.name, chave[:2])
        self.assertEqual(cache.meta(chave), {"texto": "x"})

    def test_audio_vazio_nao_entra(self):
        with self.assertRaises(ValueError):
            Cache(self.cache_dir).salvar("ab" * 32, ".mp3", b"", {})

    def test_sem_temporarios_sobrando(self):
        cache = Cache(self.cache_dir)
        cache.salvar("cd" * 32, ".mp3", b"audio", {})
        sobras = list(self.cache_dir.rglob(".tmp-*"))
        self.assertEqual(sobras, [])


if __name__ == "__main__":
    unittest.main()
