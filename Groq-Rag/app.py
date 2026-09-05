"""
ETAPA 2 — Chatbot Streamlit + Groq sobre o índice gerado na Etapa 1.

Fluxo por pergunta: embedding da consulta -> busca no FAISS -> montagem do
contexto com fontes numeradas -> resposta em streaming pela API da Groq.

Uso:
    streamlit run app.py
"""

from __future__ import annotations

import logging
from typing import Iterator

import streamlit as st
from groq import APIError, Groq

from core import (
    GROQ_API_KEY,
    GROQ_MAX_COMPLETION_TOKENS,
    GROQ_MODEL,
    GROQ_REASONING_EFFORT,
    GROQ_TEMPERATURE,
    MIN_SCORE,
    MODELOS_REASONING,
    TOP_K,
    Resultado,
    buscar,
    carregar_indice,
    carregar_embedder,
    configurar_log,
    indice_existe,
    montar_contexto,
)

configurar_log()
logger = logging.getLogger("app")

MODELOS_DISPONIVEIS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "groq/compound",
    "groq/compound-mini",
]

MAX_TURNOS_HISTORICO = 6  # mensagens enviadas ao modelo além da pergunta atual

PROMPT_SISTEMA = """Você é um assistente de consulta a documentos. Responda em português do Brasil.

Regras:
1. Use exclusivamente as informações do CONTEXTO fornecido. Não complemente com conhecimento externo.
2. Cite a origem de cada afirmação no formato [Fonte N], usando a numeração do contexto.
3. Se o contexto não contiver a resposta, diga exatamente que a informação não foi localizada no documento e indique o que seria necessário para respondê-la.
4. Não invente números, datas, nomes ou cláusulas. Prefira transcrever valores exatamente como aparecem.
5. Seja objetivo e direto. Use listas ou tabelas quando a pergunta envolver múltiplos itens."""


# --------------------------------------------------------------------------- #
# Recursos cacheados
# --------------------------------------------------------------------------- #


@st.cache_resource(show_spinner="Carregando índice e modelo de embedding...")
def obter_base():
    indice, chunks, manifesto = carregar_indice()
    carregar_embedder(manifesto.modelo_embedding)  # pré-aquece o modelo
    return indice, chunks, manifesto


@st.cache_resource(show_spinner=False)
def obter_cliente(api_key: str) -> Groq:
    return Groq(api_key=api_key)


# --------------------------------------------------------------------------- #
# Groq
# --------------------------------------------------------------------------- #


def montar_mensagens(pergunta: str, contexto: str, historico: list[dict]) -> list[dict]:
    mensagens: list[dict] = [{"role": "system", "content": PROMPT_SISTEMA}]

    for mensagem in historico[-MAX_TURNOS_HISTORICO:]:
        mensagens.append({"role": mensagem["role"], "content": mensagem["content"]})

    mensagens.append(
        {
            "role": "user",
            "content": f"CONTEXTO:\n{contexto}\n\nPERGUNTA:\n{pergunta}",
        }
    )
    return mensagens


def responder_em_stream(
    cliente: Groq,
    mensagens: list[dict],
    modelo: str,
    temperatura: float,
    max_tokens: int,
) -> Iterator[str]:
    """Chama a API da Groq em modo streaming e devolve apenas o conteúdo final."""
    parametros: dict = {
        "model": modelo,
        "messages": mensagens,
        "temperature": temperatura,
        "max_completion_tokens": max_tokens,
        "stream": True,
    }
    if modelo in MODELOS_REASONING:
        # Mantém o raciocínio fora da resposta exibida ao usuário.
        parametros["reasoning_effort"] = GROQ_REASONING_EFFORT
        parametros["reasoning_format"] = "hidden"

    stream = cliente.chat.completions.create(**parametros)
    for pedaco in stream:
        if not pedaco.choices:
            continue
        conteudo = pedaco.choices[0].delta.content
        if conteudo:
            yield conteudo


def consulta_de_recuperacao(pergunta: str, historico: list[dict]) -> str:
    """Anexa a última pergunta do usuário para dar contexto a follow-ups curtos."""
    if len(pergunta.split()) > 6:
        return pergunta
    anteriores = [m["content"] for m in historico if m["role"] == "user"]
    return f"{anteriores[-1]} {pergunta}" if anteriores else pergunta


# --------------------------------------------------------------------------- #
# Interface
# --------------------------------------------------------------------------- #


def renderizar_fontes(resultados: list[Resultado]) -> None:
    if not resultados:
        return
    with st.expander(f"Fontes consultadas ({len(resultados)})"):
        for posicao, resultado in enumerate(resultados, start=1):
            st.markdown(f"**[Fonte {posicao}]** {resultado.chunk.referencia} · similaridade {resultado.score:.3f}")
            st.caption(resultado.chunk.texto)


def barra_lateral(manifesto) -> dict:
    with st.sidebar:
        st.subheader("Documentos indexados")
        for documento in manifesto.documentos:
            st.markdown(f"- {documento['arquivo']} ({documento['chunks']} chunks)")
        st.caption(
            f"{manifesto.total_chunks} chunks · {manifesto.modelo_embedding} · "
            f"atualizado em {manifesto.atualizado_em[:16].replace('T', ' ')}"
        )

        st.divider()
        st.subheader("Parâmetros")

        api_key = GROQ_API_KEY or st.session_state.get("api_key", "")
        if not GROQ_API_KEY:
            api_key = st.text_input(
                "GROQ_API_KEY",
                value=api_key,
                type="password",
                help="Defina no arquivo .env para não precisar informar aqui.",
            )
            st.session_state["api_key"] = api_key

        indice_modelo = MODELOS_DISPONIVEIS.index(GROQ_MODEL) if GROQ_MODEL in MODELOS_DISPONIVEIS else 0
        modelo = st.selectbox("Modelo Groq", MODELOS_DISPONIVEIS, index=indice_modelo)
        top_k = st.slider("Trechos recuperados (top-k)", 1, 12, TOP_K)
        min_score = st.slider("Similaridade mínima", 0.0, 1.0, MIN_SCORE, step=0.01)
        temperatura = st.slider("Temperatura", 0.0, 1.0, GROQ_TEMPERATURE, step=0.05)

        st.divider()
        if st.button("Limpar conversa", use_container_width=True):
            st.session_state["mensagens"] = []
            st.rerun()

    return {
        "api_key": api_key,
        "modelo": modelo,
        "top_k": top_k,
        "min_score": min_score,
        "temperatura": temperatura,
    }


def main() -> None:
    st.set_page_config(page_title="Chat com PDF · Groq RAG", page_icon="📄", layout="centered")
    st.title("📄 Chat com o documento")

    if not indice_existe():
        st.error(
            "Índice não encontrado. Execute a Etapa 1 antes de abrir o chat:\n\n"
            "```bash\npython ingestao.py --pdf documentos/documento.pdf\n```"
        )
        st.stop()

    try:
        indice, chunks, manifesto = obter_base()
    except (FileNotFoundError, RuntimeError) as exc:
        st.error(str(exc))
        st.stop()

    config = barra_lateral(manifesto)

    if not config["api_key"]:
        st.warning("Informe a GROQ_API_KEY na barra lateral ou no arquivo .env para conversar.")
        st.stop()

    st.session_state.setdefault("mensagens", [])

    for mensagem in st.session_state["mensagens"]:
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])
            if mensagem["role"] == "assistant":
                renderizar_fontes(mensagem.get("fontes", []))

    pergunta = st.chat_input("Pergunte algo sobre o documento...")
    if not pergunta:
        return

    st.session_state["mensagens"].append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    with st.chat_message("assistant"):
        with st.spinner("Buscando trechos relevantes..."):
            consulta = consulta_de_recuperacao(pergunta, st.session_state["mensagens"][:-1])
            resultados = buscar(
                consulta,
                indice,
                chunks,
                k=config["top_k"],
                min_score=config["min_score"],
                nome_modelo=manifesto.modelo_embedding,
            )

        if not resultados:
            resposta = (
                "Não encontrei nenhum trecho do documento com similaridade suficiente para essa pergunta. "
                "Reformule com termos usados no documento ou reduza a similaridade mínima na barra lateral."
            )
            st.markdown(resposta)
            st.session_state["mensagens"].append({"role": "assistant", "content": resposta, "fontes": []})
            return

        contexto = montar_contexto(resultados)
        historico = st.session_state["mensagens"][:-1]
        mensagens = montar_mensagens(pergunta, contexto, historico)

        try:
            cliente = obter_cliente(config["api_key"])
            resposta = st.write_stream(
                responder_em_stream(
                    cliente,
                    mensagens,
                    modelo=config["modelo"],
                    temperatura=config["temperatura"],
                    max_tokens=GROQ_MAX_COMPLETION_TOKENS,
                )
            )
        except APIError as exc:
            logger.exception("Falha na chamada à API da Groq")
            st.error(f"Erro na API da Groq: {getattr(exc, 'message', str(exc))}")
            st.session_state["mensagens"].pop()
            return

        renderizar_fontes(resultados)

    st.session_state["mensagens"].append(
        {"role": "assistant", "content": resposta, "fontes": resultados}
    )


if __name__ == "__main__":
    main()
