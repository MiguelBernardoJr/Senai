# Chat com PDF — Streamlit + Groq + RAG

RAG em duas etapas independentes: a ingestão constrói o índice vetorial a partir do PDF; o chatbot consulta esse índice e responde com a Groq, citando as fontes.

```
core.py         camada compartilhada (config, chunking, embeddings, FAISS)
ingestao.py     ETAPA 1 — PDF  -> chunks -> embeddings -> índice FAISS
app.py          ETAPA 2 — chatbot Streamlit + Groq sobre o índice
indice/         gerado pela Etapa 1 (faiss.index, chunks.jsonl, manifest.json)
```

## Instalação

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # preencha GROQ_API_KEY
```

Chave em https://console.groq.com/keys.

## Etapa 1 — ingestão

```bash
python ingestao.py --pdf documentos/documento.pdf
python ingestao.py --dir documentos                  # todos os PDFs da pasta
python ingestao.py --pdf documentos/documento.pdf --reset  # recria o índice do zero
```

Comportamento:

- extrai texto por página (pypdf) e descarta páginas vazias;
- chunking de ~1000 caracteres com 150 de sobreposição, cortando em fim de frase e reconstituindo palavras hifenizadas na quebra de linha;
- embeddings locais com `intfloat/multilingual-e5-small` (multilíngue, roda em CPU, sem custo de API — a Groq não expõe endpoint de embeddings);
- índice `IndexFlatIP` com vetores normalizados, equivalente a similaridade de cosseno;
- execuções seguintes são **incrementais**: documentos com o mesmo SHA-256 são ignorados e novos PDFs são acrescentados ao índice existente.

PDF digitalizado (sem camada de texto) é rejeitado com mensagem explícita — rode OCR antes, por exemplo `ocrmypdf entrada.pdf saida.pdf`.

## Etapa 2 — chatbot

```bash
streamlit run app.py
```

A cada pergunta: embedding da consulta → top-k no FAISS com corte por similaridade mínima → contexto com fontes numeradas → resposta em streaming pela Groq.

- Modelo padrão `openai/gpt-oss-120b` (produção na GroqCloud). As famílias Llama 3.1/3.3 e Qwen3-32B foram descontinuadas para os planos free/developer.
- Para os modelos gpt-oss o app envia `reasoning_effort` e `reasoning_format="hidden"`, mantendo o raciocínio fora da resposta.
- O prompt de sistema proíbe responder fora do contexto e exige citação `[Fonte N]`; cada resposta traz o expander com trechos e scores.
- Barra lateral: modelo, top-k, similaridade mínima, temperatura e limpeza da conversa.
- Perguntas curtas de acompanhamento ("e o prazo?") são combinadas com a pergunta anterior antes da recuperação.

## Ajustes que mais afetam a qualidade

| Parâmetro | Onde | Efeito |
|---|---|---|
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `.env` ou CLI | contexto mais amplo por trecho vs. precisão da recuperação |
| `TOP_K` | `.env` / sidebar | mais trechos = mais cobertura e mais tokens por chamada |
| `MIN_SCORE` | `.env` / sidebar | corte de ruído; com E5 valores úteis ficam entre 0.70 e 0.85 |
| `EMBEDDING_MODEL` | `.env` | `intfloat/multilingual-e5-large` melhora a recuperação ao custo de memória e tempo |

Trocar o modelo de embedding exige `--reset`: o índice guarda o modelo usado e recusa mistura.
