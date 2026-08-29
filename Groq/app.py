"""
Chatbot simples com Streamlit + API da Groq.

Como rodar:
    pip install -r requirements.txt
    streamlit run app.py

Configuração da chave de API (escolha uma das opções):
    1) Variável de ambiente:   export GROQ_API_KEY="sua_chave_aqui"
    2) Secrets do Streamlit:   crie .streamlit/secrets.toml com:
           GROQ_API_KEY = "sua_chave_aqui"
    3) Campo na barra lateral (menos seguro, útil só para testes rápidos)
"""

import os
import streamlit as st
from groq import Groq, APIError, APIConnectionError, RateLimitError

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Chatbot Groq",
    page_icon="💬",
    layout="centered",
)

MODELOS_DISPONIVEIS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "gemma2-9b-it",
]

DEFAULT_SYSTEM_PROMPT = "Você é um assistente útil, direto e educado. Responda em português do Brasil, salvo pedido contrário."


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def obter_api_key() -> str | None:
    """Resolve a chave de API: env var > secrets.toml > input manual na sidebar."""
    chave = os.environ.get("GROQ_API_KEY")
    if not chave:
        try:
            chave = st.secrets.get("GROQ_API_KEY")
        except Exception:
            chave = None
    if not chave:
        chave = st.session_state.get("manual_api_key")
    return chave


def inicializar_estado():
    if "mensagens" not in st.session_state:
        st.session_state.mensagens = []  # lista de dicts: {"role": ..., "content": ...}
    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = DEFAULT_SYSTEM_PROMPT


def montar_historico_para_api() -> list[dict]:
    """Monta a lista de mensagens no formato esperado pela API, incluindo o system prompt."""
    historico = [{"role": "system", "content": st.session_state.system_prompt}]
    historico.extend(st.session_state.mensagens)
    return historico


def chamar_groq(client: Groq, modelo: str, temperatura: float, max_tokens: int) -> str:
    """Faz a chamada de chat completion (streaming) e retorna a resposta completa."""
    stream = client.chat.completions.create(
        model=modelo,
        messages=montar_historico_para_api(),
        temperature=temperatura,
        max_tokens=max_tokens,
        stream=True,
    )

    placeholder = st.empty()
    resposta_completa = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        resposta_completa += delta
        placeholder.markdown(resposta_completa + "▌")
    placeholder.markdown(resposta_completa)
    return resposta_completa


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------
def main():
    inicializar_estado()

    st.title("💬 Chatbot com Groq")
    st.caption("Streamlit + API da Groq — respostas em streaming")

    # --- Sidebar: configurações ---
    with st.sidebar:
        st.header("Configurações")

        api_key = obter_api_key()
        if not api_key:
            st.warning("Nenhuma GROQ_API_KEY encontrada em ambiente ou secrets.")
            st.session_state.manual_api_key = st.text_input(
                "Cole sua GROQ_API_KEY", type="password"
            )
            api_key = st.session_state.get("manual_api_key")

        modelo = st.selectbox("Modelo", MODELOS_DISPONIVEIS, index=0)
        temperatura = st.slider("Temperatura", 0.0, 1.5, 0.7, 0.1)
        max_tokens = st.slider("Máx. tokens na resposta", 128, 4096, 1024, 128)

        st.divider()
        st.session_state.system_prompt = st.text_area(
            "System prompt",
            value=st.session_state.system_prompt,
            height=100,
        )

        st.divider()
        if st.button("🗑️ Limpar conversa", use_container_width=True):
            st.session_state.mensagens = []
            st.rerun()

    if not api_key:
        st.info("Informe sua chave da API Groq na barra lateral para começar a conversar.")
        st.stop()

    client = Groq(api_key=api_key)

    # --- Histórico exibido ---
    for msg in st.session_state.mensagens:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- Entrada do usuário ---
    prompt_usuario = st.chat_input("Digite sua mensagem...")
    if prompt_usuario:
        st.session_state.mensagens.append({"role": "user", "content": prompt_usuario})
        with st.chat_message("user"):
            st.markdown(prompt_usuario)

        with st.chat_message("assistant"):
            try:
                resposta = chamar_groq(client, modelo, temperatura, max_tokens)
                st.session_state.mensagens.append({"role": "assistant", "content": resposta})
            except RateLimitError:
                st.error("Limite de requisições da API Groq atingido. Tente novamente em instantes.")
            except APIConnectionError:
                st.error("Falha de conexão com a API da Groq. Verifique sua rede.")
            except APIError as e:
                st.error(f"Erro retornado pela API da Groq: {e}")


if __name__ == "__main__":
    main()
