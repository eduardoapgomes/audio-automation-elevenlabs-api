# Prompt padrão: material → arquivos de narração

Use este prompt sempre que precisar gerar a narração de um material (PDF, livreto,
apostila, roteiro, artigo...) com o `narrar`. Serve para orações e para qualquer
outro tipo de projeto.

## Jeito rápido (quando o Claude tem acesso ao repositório)

Anexe o material e mande:

```text
Siga o docs/PROMPT.md do repositório eduardoapgomes/audio-automation-elevenlabs-api
com o material anexo.
PROJETO: Abrir e Rezar
ID DO ROTEIRO: rosario_sao_miguel
BIBLIOTECA: oracoes
VOZ: <ID da voz ou "a mesma do canal">
OBSERVAÇÕES: <o que pular, o que só resumir, trechos que mudaram etc.>
```

## Jeito completo (qualquer conversa, com ou sem o repositório)

Copie tudo o que está entre as linhas `=====`, preencha o cabeçalho, anexe o
material e envie.

=====

Você vai preparar a narração de um material para o meu gerador de áudio `narrar`
(repositório eduardoapgomes/audio-automation-elevenlabs-api, que usa a API da ElevenLabs).
Não gere áudio: sua entrega são os arquivos YAML e um relatório.

PROJETO: <nome do projeto ou canal>
ID DO ROTEIRO: <ex.: rosario_sao_miguel — só minúsculas, números e _>
BIBLIOTECA: <pasta dos blocos reutilizáveis — "oracoes" para orações do canal; para outros projetos, bibliotecas/<projeto>>
VOZ: <ID da voz na ElevenLabs; se não souber, deixe "COLE_AQUI">
MODELO: <padrão: eleven_multilingual_v2>
OBSERVAÇÕES: <o que pular, o que resumir, o público, tom desejado, versões que substituem outras>

### 1. Leia o material inteiro antes de escrever

- Leia todas as páginas, incluindo o texto dentro das imagens. Anote a página de cada trecho.
- Se houver mais de uma versão do material, use só a que eu indicar como final.
- Separe o que é **texto para ser falado** do que é **instrução visual**: títulos de
  seção, números de página, rodapés, créditos, sumário, legendas de imagem e rubricas
  ("reza-se...", "em seguida...") só entram na narração se eu pedir ou se forem
  necessários para quem ouve acompanhar (nesse caso, curtos e marcados com `nota`).

### 2. Fidelidade ao texto (regra mais importante)

- O texto falado é o texto do material, palavra por palavra. Não corrija, não
  modernize, não resuma e não complete orações "de memória".
- Erros evidentes de digitação: mantenha como está e liste no relatório para eu decidir.
- Texto ilegível ou cortado: escreva `TODO: <o que falta, página X>` no lugar. Isso
  bloqueia a geração até eu resolver, de propósito.

### 3. Prepare o texto para a voz (sem mudar o sentido)

Só estas adaptações são permitidas, e cada uma deve ficar registrada em `nota`:

- Números, datas e horas por extenso ("3" → "três"; "séc. XIX" → "século dezenove").
- Numerais romanos por extenso ("Pio XII" → "Pio Doze"; "Capítulo IV" → "Capítulo quatro").
- Abreviações expandidas ("Sto." → "Santo", "S." → "São", "Pe." → "Padre",
  "N. Sra." → "Nossa Senhora", "Sr." → "Senhor", "p. ex." → "por exemplo").
- Símbolos removidos ou falados: ℣/℟, V./R., †, ✠, *, (bis), números de nota de rodapé.
  Se o material indicar versículo e resposta, a narração fala os dois em sequência.
- Siglas soletradas só se forem lidas assim ("CNBB" → "cê ene bê bê").
- Palavras em latim ou estrangeiras: mantenha e liste no relatório (a voz pode errar a pronúncia).
- Quebras de linha não fazem diferença no áudio. Para pausas, use pontuação ou separe segmentos.

### 4. Encontre os blocos reutilizáveis

Um **bloco** é um texto que se repete: dentro deste material, entre materiais do mesmo
projeto ou entre projetos (orações tradicionais, vinheta de abertura, chamada final, refrão).

- Primeiro veja os blocos que já existem na BIBLIOTECA (se você tem acesso ao repositório,
  leia a pasta; senão, pergunte ou assuma que está vazia).
- Texto idêntico a um bloco existente → use `bloco: <id>`. Não crie outro igual.
- Texto parecido mas diferente (uma palavra ou pontuação a mais) → **não reutilize**.
  Crie um bloco novo com sufixo (`ave_maria_livreto`) e aponte a diferença no relatório.
- Texto que aparece duas ou mais vezes e ainda não está na biblioteca → crie um bloco novo.
- Texto que aparece uma vez só → fica no roteiro com `texto:`.
- Blocos que se repetem três ou mais vezes no mesmo roteiro → defina `variantes: 2` ou `3`
  para não soar como o mesmo clipe repetido.

### 5. Divida em segmentos

- Um segmento é uma unidade natural de fala: uma oração, um parágrafo, uma fala de diálogo.
- Ideal: até ~1.000 caracteres por segmento. Limites rígidos por requisição: eleven_v3
  5.000; eleven_multilingual_v2 10.000; eleven_flash_v2_5 40.000.
- Use `repetir: N` para repetições seguidas do mesmo bloco, em vez de copiar o segmento.
- Cada segmento recebe um `id` descritivo (`abertura`, `saudacao_3`, `capitulo_2_p1`),
  exceto os que usam `bloco`, que já se identificam pelo nome.
- Preencha `pagina:` e `cena:` (qual imagem ou tela aparece enquanto a fala toca).
  Esses campos não mudam o áudio, mas vão para o `manifesto.json` e guiam a edição do vídeo.

### 6. Padrões de pausa (`pausa_depois`, em segundos)

| Situação | Pausa |
|---|---|
| Entre frases curtas de um mesmo trecho | 0,6 a 0,8 |
| Padrão entre falas (`pausa_padrao`) | 1,2 |
| Fim de uma oração completa ou parágrafo | 1,5 a 2 |
| Troca de seção, mistério, capítulo | 2,5 a 3 |
| Momento de silêncio ou reflexão pedido no material | 4 a 6 |

A última fala do roteiro não precisa de pausa: a montagem já ignora.

### 7. Padrões de voz

Use estes valores, a menos que eu peça outra coisa:

- `modelo: eleven_multilingual_v2` e `formato: mp3_44100_128`.
- `ajustes`: `stability: 0.6`, `similarity_boost: 0.75`, `style: 0`,
  `use_speaker_boost: true`, `speed: 0.95` (oração/meditação) ou `1.0` (conteúdo explicativo).
- `seed: 1`.
- Não use o campo `idioma`: o modelo reconhece o português pelo texto.
- Ajuste por segmento só quando houver motivo (ex.: `speed: 0.9` num trecho solene) e
  explique em `nota`.

**Atenção ao cache:** mudar voz, modelo, ajustes, formato ou seed gera áudio novo e
custa de novo. Para manter o reaproveitamento entre vídeos, repita exatamente os mesmos
valores dos roteiros anteriores do projeto.

### 8. Arquivos a entregar

**a) Roteiro** — `roteiros/<ID DO ROTEIRO>.yaml`, neste formato (só estes campos são aceitos):

```yaml
id: exemplo_modelo
titulo: Título que aparece nos relatórios
descricao: Uma linha sobre o vídeo
fonte: "Nome do material, versão, data"
biblioteca: oracoes
voz: "COLE_AQUI_O_ID_DA_VOZ"
modelo: eleven_multilingual_v2
formato: mp3_44100_128
ajustes:
  stability: 0.6
  similarity_boost: 0.75
  style: 0
  use_speaker_boost: true
  speed: 0.95
seed: 1
pausa_padrao: 1.2
variantes:
  ave_maria: 3
segmentos:
  - id: abertura
    texto: >
      Texto só deste material, exatamente como no original.
    pagina: 2
    cena: capa
    pausa_depois: 2
  - bloco: pai_nosso
    pagina: 3
    cena: imagem_p3
  - bloco: ave_maria
    repetir: 3
    pagina: 3
    cena: imagem_p3
    pausa_depois: 2.5
  - id: trecho_lento
    texto: "Trecho dito mais devagar."
    ajustes: {speed: 0.9}
    nota: "mais lento por ser o fechamento"
    pagina: 4
    cena: imagem_p4
```

**b) Blocos novos** — um arquivo por bloco, em `<BIBLIOTECA>/<id>.yaml`:

```yaml
id: ave_maria_livreto
titulo: Ave-Maria (versão do livreto)
fonte: "Nome do material, página 3"
texto: >
  Texto exato do bloco.
```

Nunca altere um bloco que já existe: outros roteiros dependem dele e o áudio já foi pago.

**c) Relatório**, na resposta, com:
1. Tabela dos segmentos: ordem, id ou bloco, página, cena, caracteres, pausa.
2. Blocos reutilizados, blocos novos e repetições evitadas.
3. Todas as adaptações de texto (o que estava e o que ficou).
4. Dúvidas e `TODO` pendentes, com página.
5. Total de caracteres únicos a gerar e a economia pela biblioteca.

### 9. Valide antes de entregar

- **Com acesso ao repositório:** grave os arquivos, rode `narrar plano roteiros/<ID>.yaml`
  e `pytest`, corrija qualquer erro e faça commit e push com uma mensagem descritiva.
  Cole a saída do `narrar plano` no relatório.
- **Sem acesso ao repositório:** entregue cada arquivo para download com o caminho
  exato onde ele deve ficar, e confira você mesmo os campos contra o modelo acima.
- **Nunca** rode `narrar gerar`: gerar áudio gasta créditos e é decisão minha.

=====

## Depois de receber os arquivos

```bash
git pull                                  # se o Claude fez o push
narrar plano roteiros/<id>.yaml           # confira pendências e custo (grátis)
narrar gerar roteiros/<id>.yaml           # gera só o que falta (gasta créditos)
narrar montar roteiros/<id>.yaml          # trilha + manifesto.json + legendas.srt
```

Ouça os primeiros áudios antes de gerar o resto. Se uma palavra sair com pronúncia
errada, ajuste a escrita no segmento (ex.: separar sílabas, trocar por extenso) e
gere de novo só aquele trecho: o resto continua no cache.
