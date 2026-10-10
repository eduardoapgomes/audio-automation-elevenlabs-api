# audio-automation-elevenlabs-api

Gera a narração dos vídeos do canal **Abrir e Rezar** com a API da ElevenLabs,
sem pagar duas vezes pelo mesmo áudio.

O roteiro de cada vídeo é um YAML que diz *qual oração vem quando*. O texto de
cada oração (Pai-Nosso, Ave-Maria, Glória...) fica numa biblioteca única, usada
por todos os vídeos. Cada áudio é guardado num cache cujo nome é o hash de tudo
que muda o som (texto, voz, modelo, ajustes, formato, seed). Se já existe, não
é gerado de novo — nem neste vídeo, nem nos próximos, nem nos Shorts.

No exemplo do Rosário de São Miguel, isso corta **cerca de 78%** dos caracteres
(57 falas viram 22 áudios únicos).

## Instalar (Windows, Mac ou Linux)

Precisa de **Python 3.10+** e, para montar a trilha final, do **ffmpeg**
(Windows: `winget install ffmpeg`; Mac: `brew install ffmpeg`).

```bash
git clone https://github.com/eduardoapgomes/audio-automation-elevenlabs-api.git
cd audio-automation-elevenlabs-api
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

Copie `.env.example` para `.env` e cole sua chave da ElevenLabs
(elevenlabs.io → Developers → API Keys). O `.env` nunca vai para o Git.

## Usar

```bash
narrar vozes                                   # lista suas vozes e os IDs (grátis)
narrar saldo                                   # saldo da conta (grátis)
narrar plano  roteiros/rosario_sao_miguel.yaml # o que falta gerar e quanto custa (grátis)
narrar gerar  roteiros/rosario_sao_miguel.yaml # gera só o que falta (GASTA créditos, pede confirmação)
narrar montar roteiros/rosario_sao_miguel.yaml # junta tudo numa trilha
```

`narrar montar` cria em `saida/<roteiro>/`:

| Arquivo | Para quê |
|---|---|
| `narracao.wav` / `narracao.mp3` | a trilha de narração completa, com as pausas |
| `manifesto.json` | início e fim de cada fala, para sincronizar as imagens no editor |
| `legendas.srt` | o texto de cada fala com tempo; importa direto no CapCut, Premiere, DaVinci etc. |

### Travas de segurança

- `narrar gerar` **se recusa** a gastar enquanto o roteiro tiver `TODO` ou `COLE_AQUI`.
- Pede confirmação antes de gerar (pule com `--sim`).
- Não gera se faltar mais de 20.000 caracteres (mude com `--max-caracteres`).
- Se cair no meio, o que já foi gerado fica salvo; rodar de novo continua de onde parou.

## Próximo passo: deixar o Rosário de São Miguel pronto

1. Rode `narrar vozes` e cole em `voz:` o ID da voz que você já usa no canal.
2. Em `roteiros/rosario_sao_miguel.yaml`, troque cada `TODO` pelo texto exato do
   livreto **v28_FINAL** e confira a ordem das orações.
3. Confira `oracoes/*.yaml` com o livreto (a voz tem que ser fiel ao texto).
4. `narrar plano ...` até não aparecer nenhuma pendência; depois `narrar gerar ...`.
5. Ouça um Pai-Nosso e uma Ave-Maria antes de seguir. Se quiser comparar com o
   Flash (metade do preço), troque `modelo:` e rode de novo: o cache não mistura os dois.

## Como escrever um roteiro

```yaml
id: meu_terco
voz: "ID_DA_VOZ"
modelo: eleven_multilingual_v2
ajustes: {stability: 0.6, similarity_boost: 0.75, style: 0, speed: 0.95}
pausa_padrao: 1.2
variantes: {ave_maria: 3}        # 3 gravações diferentes, alternadas
segmentos:
  - id: abertura
    texto: "Texto livre, só deste vídeo."
  - oracao: pai_nosso            # vem de oracoes/pai_nosso.yaml
  - oracao: ave_maria
    repetir: 3
    pausa_depois: 2.5            # silêncio extra depois desta fala
  - texto: "Trecho mais lento"
    ajustes: {speed: 0.85}       # sobrescreve só aqui
```

Pausas entre frases: use pontuação ou separe em segmentos. Quebras de linha
dentro do texto são ignoradas (não mudam o áudio nem o hash).

## Onde fica o quê

```
oracoes/        biblioteca de orações (vai para o Git)
roteiros/       um YAML por vídeo ou Short (vai para o Git)
cache/          áudios pagos, nome = hash (NÃO vai para o Git — faça backup!)
saida/          trilhas montadas (NÃO vai para o Git, dá para refazer)
src/narrador/   o código
tests/          testes com API simulada (nunca gastam créditos)
docs/PLANO.md   decisões de arquitetura e roadmap
```

**Backup do `cache/`:** é o único lugar onde ficam os áudios já pagos. Copie a
pasta para o Google Drive (ou outro lugar) de vez em quando. Ao trocar de PC,
copie o `cache/` junto, senão o primeiro `narrar gerar` vai pagar tudo de novo.

## Testes

```bash
pytest          # ou: python -m unittest discover -s tests
```

O GitHub Actions roda os testes a cada push. Há também um workflow manual
("Conferir chave ElevenLabs") que só consulta o saldo, para testar o segredo
`ELEVENLABS_API_KEY` sem gastar créditos.
