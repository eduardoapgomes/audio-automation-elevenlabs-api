import json
import shutil
import unittest
import wave
from unittest import mock

from narrador.cache import Cache
from narrador.elevenlabs import ClienteElevenLabs, ErroAPI
from narrador.gerar import ErroGeracao, gerar_faltantes
from narrador.montagem import ErroMontagem, montar
from narrador.plano import montar_plano, relatorio
from narrador.roteiro import carregar_biblioteca, carregar_roteiro

from auxiliares import ApiFalsa, ComPastaTemporaria


class Base(ComPastaTemporaria):
    def plano(self, conteudo=None):
        caminho = self.escrever_roteiro(conteudo) if conteudo else self.escrever_roteiro()
        roteiro = carregar_roteiro(caminho, carregar_biblioteca(self.biblioteca_dir))
        return montar_plano(roteiro, Cache(self.cache_dir))

    def cliente(self, api):
        return ClienteElevenLabs("chave-teste", transporte=api, dormir=lambda s: None)


class TestPlano(Base):
    def test_deduplica(self):
        p = self.plano()
        # 6 falas: abertura, pai_nosso, 3 ave-marias (2 variantes), fim -> 5 áudios únicos
        self.assertEqual(len(p.roteiro.falas), 6)
        self.assertEqual(len(p.unicas), 5)
        self.assertEqual(len(p.a_gerar), 5)
        self.assertLess(p.caracteres_unicos, p.caracteres_sem_reuso)
        self.assertIn("Áudios únicos", relatorio(p))

    def test_flash_custa_metade(self):
        p = self.plano("""
            voz: v
            modelo: eleven_flash_v2_5
            segmentos:
              - texto: "abcd"
        """)
        self.assertEqual(p.creditos_estimados, 2.0)


class TestGerar(Base):
    def test_gera_so_o_que_falta_e_nao_repete(self):
        api = ApiFalsa()
        p = self.plano()
        n = gerar_faltantes(p, self.cliente(api), Cache(self.cache_dir), 10_000, log=lambda m: None)
        self.assertEqual(n, 5)
        self.assertEqual(len(api.tts), 5)

        # segunda rodada: tudo no cache, zero chamadas pagas
        api2 = ApiFalsa()
        p2 = self.plano()
        self.assertEqual(p2.a_gerar, [])
        self.assertEqual(gerar_faltantes(p2, self.cliente(api2), Cache(self.cache_dir), 10_000,
                                         log=lambda m: None), 0)
        self.assertEqual(api2.tts, [])

    def test_corpo_da_requisicao(self):
        api = ApiFalsa()
        p = self.plano()
        gerar_faltantes(p, self.cliente(api), Cache(self.cache_dir), 10_000, log=lambda m: None)
        primeira = api.tts[0]
        self.assertIn("/v1/text-to-speech/voz123?output_format=pcm_44100", primeira["url"])
        self.assertEqual(primeira["headers"]["xi-api-key"], "chave-teste")
        self.assertEqual(primeira["corpo"]["text"], "Em nome do Pai.")
        self.assertEqual(primeira["corpo"]["model_id"], "eleven_multilingual_v2")
        self.assertEqual(primeira["corpo"]["seed"], 10)
        self.assertNotIn("language_code", primeira["corpo"])

    def test_metadados_e_wav(self):
        api = ApiFalsa()
        p = self.plano()
        cache = Cache(self.cache_dir)
        gerar_faltantes(p, self.cliente(api), cache, 10_000, log=lambda m: None)
        chave, fala = next(iter(p.unicas.items()))
        meta = cache.meta(chave)
        self.assertEqual(meta["texto"], "Em nome do Pai.")
        self.assertTrue(meta["request_id"].startswith("req-"))
        with wave.open(str(cache.caminho(chave, fala.ext))) as w:
            self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()), (1, 2, 44100))

    def test_trava_de_caracteres(self):
        api = ApiFalsa()
        with self.assertRaises(ErroGeracao):
            gerar_faltantes(self.plano(), self.cliente(api), Cache(self.cache_dir), 10,
                            log=lambda m: None)
        self.assertEqual(api.chamadas, [])

    def test_pendencia_bloqueia(self):
        api = ApiFalsa()
        p = self.plano("""
            voz: v
            segmentos:
              - texto: "TODO: copiar"
        """)
        with self.assertRaises(ErroGeracao):
            gerar_faltantes(p, self.cliente(api), Cache(self.cache_dir), 10_000, log=lambda m: None)
        self.assertEqual(api.chamadas, [])

    def test_repete_em_429_e_depois_funciona(self):
        api = ApiFalsa(respostas_tts=[429, 503])
        esperas = []
        cliente = ClienteElevenLabs("k", transporte=api, dormir=esperas.append)
        p = self.plano("""
            voz: v
            formato: pcm_44100
            segmentos:
              - texto: "x"
        """)
        gerar_faltantes(p, cliente, Cache(self.cache_dir), 10_000, log=lambda m: None)
        self.assertEqual(len(api.tts), 3)
        self.assertEqual(esperas, [1.0, 2.0])

    def test_401_nao_repete(self):
        api = ApiFalsa(respostas_tts=[401])
        p = self.plano()
        with self.assertRaises(ErroAPI):
            gerar_faltantes(p, self.cliente(api), Cache(self.cache_dir), 10_000, log=lambda m: None)
        self.assertEqual(len(api.tts), 1)

    def test_falha_no_meio_mantem_o_que_ja_foi_pago(self):
        api = ApiFalsa(respostas_tts=[200, 200, 400])
        p = self.plano()
        with self.assertRaises(ErroAPI):
            gerar_faltantes(p, self.cliente(api), Cache(self.cache_dir), 10_000, log=lambda m: None)
        p2 = self.plano()
        self.assertEqual(len(p2.em_cache), 2)
        self.assertEqual(len(p2.a_gerar), 3)


class TestMontar(Base):
    def gerar_tudo(self):
        p = self.plano()
        gerar_faltantes(p, self.cliente(ApiFalsa(segundos=0.5)), Cache(self.cache_dir), 10_000,
                        log=lambda m: None)
        return p

    def test_monta_trilha_manifesto_e_legendas(self):
        p = self.gerar_tudo()
        saida = self.dir / "saida"
        manifesto = montar(p, Cache(self.cache_dir), saida, mp3=False)
        # 6 falas de 0,5 s + 5 pausas de 1 s (nenhuma depois da última)
        self.assertAlmostEqual(manifesto["duracao_total_s"], 6 * 0.5 + 5 * 1.0, places=2)
        falas = manifesto["falas"]
        self.assertEqual(falas[0]["inicio_s"], 0.0)
        self.assertAlmostEqual(falas[1]["inicio_s"], 1.5, places=2)
        self.assertEqual(falas[-1]["pausa_depois_s"], 0.0)
        with wave.open(str(saida / "narracao.wav")) as w:
            self.assertAlmostEqual(w.getnframes() / w.getframerate(), 8.0, places=2)
        srt = (saida / "legendas.srt").read_text(encoding="utf-8")
        self.assertIn("00:00:00,000 --> 00:00:00,500", srt)
        self.assertIn("Ave Maria, cheia de graça.", srt)
        salvo = json.loads((saida / "manifesto.json").read_text(encoding="utf-8"))
        self.assertEqual(len(salvo["falas"]), 6)

    def test_sem_audio_no_cache_nao_monta(self):
        with self.assertRaises(ErroMontagem):
            montar(self.plano(), Cache(self.cache_dir), self.dir / "saida", mp3=False)

    @unittest.skipUnless(shutil.which("ffmpeg"), "precisa do ffmpeg")
    def test_gera_mp3_com_ffmpeg(self):
        p = self.gerar_tudo()
        manifesto = montar(p, Cache(self.cache_dir), self.dir / "saida", mp3=True)
        self.assertEqual(manifesto["faixa_mp3"], "narracao.mp3")
        self.assertTrue((self.dir / "saida" / "narracao.mp3").stat().st_size > 0)

    def test_mp3_sem_ffmpeg_avisa(self):
        p = self.plano("""
            voz: v
            formato: mp3_44100_128
            segmentos:
              - texto: "x"
        """)
        cache = Cache(self.cache_dir)
        chave, fala = next(iter(p.unicas.items()))
        cache.salvar(chave, fala.ext, b"mp3-falso", {})
        p.em_cache.add(chave)
        with mock.patch("narrador.montagem._ffmpeg", return_value=None):
            with self.assertRaises(ErroMontagem) as ctx:
                montar(p, cache, self.dir / "saida", mp3=False)
        self.assertIn("ffmpeg", str(ctx.exception))


class TestCliente(Base):
    def test_saldo_e_vozes_nao_chamam_tts(self):
        api = ApiFalsa()
        c = self.cliente(api)
        self.assertEqual(c.assinatura()["character_limit"], 100000)
        self.assertEqual(c.vozes()[0]["voice_id"], "abc")
        self.assertEqual(api.tts, [])

    def test_sem_chave(self):
        with self.assertRaises(ErroAPI):
            ClienteElevenLabs("")


if __name__ == "__main__":
    unittest.main()
