import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import os


# =========================
# CONFIGURAÇÕES
# =========================

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    st.error("Chave da API Groq não encontrada.")
    st.stop()

client = Groq(api_key=API_KEY)


# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================

st.set_page_config(
    page_title="Chatbot Groq",
    page_icon="🤖",
    layout="centered"
)


# =========================
# TÍTULO
# =========================

st.title("🤖 Chatbot com Groq")
st.write("Converse com uma inteligência artificial utilizando Python + Streamlit + Groq.")


# =========================
# HISTÓRICO DA CONVERSA
# =========================

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": "Você é um assistente útil, educado e objetivo."
        }
    ]


# =========================
# EXIBIR MENSAGENS
# =========================

for message in st.session_state.messages:

    if message["role"] == "system":
        continue

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# =========================
# CAMPO DE PERGUNTA
# =========================

prompt = st.chat_input("Digite sua pergunta...")


if prompt:

    # Adiciona pergunta do usuário
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    # Mostra pergunta
    with st.chat_message("user"):
        st.markdown(prompt)


    # Gera resposta da IA
    with st.chat_message("assistant"):

        with st.spinner("Pensando..."):

            try:

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=st.session_state.messages,
                    temperature=0.7,
                    max_tokens=1024
                )

                answer = response.choices[0].message.content

                st.markdown(answer)

                # Salva resposta
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer
                    }
                )

            except Exception as e:

                st.error(f"Erro ao consultar a API: {e}")