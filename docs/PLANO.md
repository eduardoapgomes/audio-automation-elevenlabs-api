# Plano e decisões

Revisão do plano original (Python + ElevenLabs + n8n + GitHub), com as correções
que mudam custo ou resultado. Atualizado em outubro/2026.

## Decisões

1. **A chave do cache é o hash de tudo que muda o som**: texto normalizado, voz,
   modelo, ajustes de voz, formato, seed e idioma. Com o hash só do texto, trocar
   a voz devolveria o áudio antigo. Implementado em `src/narrador/cache.py`.

2. **Normalização mínima**: Unicode NFC e espaços colapsados. A pontuação fica,
   porque muda a entonação.

3. **Sem embeddings para deduplicar.** Reaproveitar o áudio de um texto
   "parecido" faria o narrador dizer palavras que não estão no roteiro. Em TTS só
   existe duplicata exata. Similaridade pode virar, no futuro, um *alerta* de
   possível erro de digitação, nunca uma substituição.

4. **A unidade é a oração, não o roteiro.** O roteiro *declara* a estrutura e
   aponta para a biblioteca `oracoes/`. Cada oração é gerada uma vez para o canal
   inteiro (vídeos longos e Shorts).

5. **Variantes** (`variantes:` no roteiro): 2–3 gravações da mesma oração com
   seeds diferentes, alternadas, para não soar como o mesmo clipe repetido.

6. **Dry-run é local** (`narrar plano`). Toda chamada de TTS gera e cobra; não
   existe "pedir só os headers". O plano soma o que falta e consulta o saldo em
   `/v1/user/subscription`, que não gasta créditos.

7. **Áudio fora do Git.** A cota gratuita do Git LFS é pequena (10 GiB) e todo
   download feito pelo Actions consome banda. O `cache/` é endereçado por hash e
   tem backup separado. No Git ficam código, YAMLs e documentação.

8. **Sem SQLite no MVP.** "O arquivo existe" já é a deduplicação; um `.json` ao
   lado de cada áudio guarda os metadados (texto, voz, request-id, data).

9. **Sem SDK, sem dependências pesadas.** O cliente HTTP usa só a biblioteca
   padrão; o transporte é injetável, então os testes nunca chamam a API.

10. **A CI nunca gera áudio.** Testes com API simulada a cada push; o workflow
    manual só consulta o saldo.

## ElevenLabs (out/2026)

| Modelo | Limite por requisição | Observação |
|---|---|---|
| `eleven_v3` | 5.000 caracteres | mais expressivo; sem request stitching; usa tags próprias como `[pause]` |
| `eleven_multilingual_v2` | 10.000 | boa qualidade, padrão do projeto |
| `eleven_flash_v2_5` | 40.000 | metade do preço por caractere; testar se a qualidade basta |
| `eleven_turbo_*` | — | descontinuados; usar Flash |

- Request stitching por ID só vale para requisições de até 2 horas, então não
  serve para clipes do cache reaproveitados dias depois. As pausas entre orações
  já disfarçam as emendas.
- Voz: usar a mesma do canal, não a "Rachel" (voz americana).
- A montagem decodifica os MP3 com ffmpeg antes de juntar, o que evita os
  pequenos silêncios do preenchimento de cada MP3.

## Roadmap

- [x] **MVP1** — CLI `narrar` com biblioteca de orações, cache por hash,
  plano/custo, geração com travas, montagem com manifesto e legendas, testes.
- [ ] **MVP2** — backup automático do `cache/` (Google Drive ou bucket barato);
  comando para comparar modelos ouvindo a mesma oração.
- [ ] **MVP3** — automação só quando houver um gatilho real (ex.: livreto novo na
  estante). Se for n8n: o nó Execute Command vem desativado desde a versão 2.0 e
  não existe no n8n Cloud; melhor expor o Python como um pequeno endpoint HTTP e
  chamar pelo nó HTTP Request.
- [ ] Ideia: alerta de "quase duplicata" entre roteiros e biblioteca (erro de digitação).

## Fontes

- https://elevenlabs.io/docs/overview/models
- https://elevenlabs.io/docs/api-reference/how-to-use-request-stitching
- https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand
- https://docs.github.com/en/billing/concepts/product-billing/git-lfs
