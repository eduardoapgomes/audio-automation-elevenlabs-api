# Contexto para o Claude

Projeto do Eduardo para o canal de YouTube **Abrir e Rezar** (@abrirerezar):
narração de orações com a API da ElevenLabs, sem pagar duas vezes pelo mesmo áudio.
Leia `README.md` (uso) e `docs/PLANO.md` (decisões e roadmap) antes de mudar algo.

## Regras do projeto

- Respostas, mensagens e documentação em português do Brasil.
- **Nunca** chamar a API de geração (TTS) em testes ou na CI. Os testes usam
  `tests/auxiliares.py::ApiFalsa`. Chamadas reais só pelo `narrar gerar`, que
  pede confirmação.
- A chave do cache (`cache.chave_cache`) precisa incluir tudo que muda o som.
  Se mudar a forma de calcular, aumente `VERSAO_CHAVE`.
- Sem deduplicação por similaridade/embeddings: só duplicata exata.
- O texto falado tem que ser fiel ao livreto. Não "corrija" orações por conta própria.
- `cache/`, `saida/` e `.env` ficam fora do Git.
- Dependências: só PyYAML em produção. Prefira a biblioteca padrão.

## Comandos

```bash
pip install -e ".[dev]"
pytest
narrar plano roteiros/rosario_sao_miguel.yaml
```

## Estado atual

MVP1 pronto. Próximo passo do Eduardo: preencher os `TODO` de
`roteiros/rosario_sao_miguel.yaml` com o texto do livreto v28_FINAL, colar o ID
da voz e gerar.
