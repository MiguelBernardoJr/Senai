"""Clima-Groq — UI Streamlit. Apenas orquestra; sem regra de negócio e sem HTTP direto."""

from __future__ import annotations

import logging

import streamlit as st

from src.config import load_settings
from src.llm import ask_free, ask_structured
from src.schemas import City, WeatherContext
from src.weather import geocode_city, get_forecast

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Clima-Groq", page_icon="🌤️", layout="centered")

settings = load_settings()


@st.cache_data(ttl=900, show_spinner=False)
def _cached_geocode(name: str):
    return geocode_city(name)


@st.cache_data(ttl=900, show_spinner=False)
def _cached_forecast(city: City):
    return get_forecast(city)

st.session_state.setdefault("context", None)
st.session_state.setdefault("recommendation", None)
st.session_state.setdefault("messages", [])
st.session_state.setdefault("city_candidates", None)
st.session_state.setdefault("used_offline", False)


def _location_label(city: City) -> str:
    place = f"{city.name} — {city.admin1}, {city.country}" if city.admin1 else f"{city.name} — {city.country}"
    return place


def _load_weather(city: City) -> None:
    with st.spinner("Buscando previsão..."):
        try:
            ctx = _cached_forecast(city)
        except Exception:
            logger.exception("Falha ao buscar previsão para %s", city.name)
            st.error("Não foi possível consultar a previsão agora. Tente novamente em instantes.")
            return

    with st.spinner("Gerando recomendação..."):
        recommendation, used_offline = ask_structured(ctx, settings)

    st.session_state.context = ctx
    st.session_state.recommendation = recommendation
    st.session_state.used_offline = used_offline
    st.session_state.messages = []
    st.session_state.city_candidates = None


st.title("🌤️ Clima-Groq")
st.caption("Digite uma cidade para ver o clima real e receber sugestões de roupa, comida e atividades.")

with st.form("city_form"):
    city_name = st.text_input("Cidade", placeholder="Ex.: Pirapozinho")
    submitted = st.form_submit_button("Consultar")

if submitted:
    if not city_name.strip():
        st.warning("Digite o nome de uma cidade.")
    else:
        with st.spinner("Buscando cidade..."):
            try:
                candidates = _cached_geocode(city_name.strip())
            except Exception:
                logger.exception("Falha ao consultar geocoding para %r", city_name)
                st.error("Não foi possível consultar o serviço de clima agora. Tente novamente em instantes.")
                candidates = None

        if candidates is not None:
            if len(candidates) == 0:
                st.error(f"Não encontramos '{city_name}'. Verifique o nome e tente novamente.")
                st.session_state.city_candidates = None
            elif len(candidates) == 1:
                _load_weather(candidates[0])
            else:
                st.session_state.city_candidates = candidates

if st.session_state.city_candidates:
    st.info("Encontramos mais de uma cidade com esse nome. Escolha a correta:")
    options = st.session_state.city_candidates
    choice = st.selectbox(
        "Cidade",
        options=range(len(options)),
        format_func=lambda i: _location_label(options[i]),
        key="city_choice",
    )
    if st.button("Confirmar cidade"):
        _load_weather(options[choice])

ctx: WeatherContext | None = st.session_state.context
rec = st.session_state.recommendation

if ctx and rec:
    st.subheader(_location_label(ctx.city))

    cols = st.columns(4)
    cols[0].metric("Temperatura", f"{ctx.current.temperature:.1f} °C")
    cols[1].metric("Sensação", f"{ctx.current.feels_like:.1f} °C")
    cols[2].metric("Umidade", f"{ctx.current.humidity}%")
    cols[3].metric("Vento", f"{ctx.current.wind_speed:.0f} km/h")

    st.caption(
        f"{ctx.current.description} · máx {ctx.max_today:.1f} °C / mín {ctx.min_today:.1f} °C "
        f"· chance de chuva {ctx.rain_chance_today}%"
    )

    if st.session_state.used_offline:
        st.info("Modo offline — sugestões geradas por regras locais.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 👕 O que vestir")
        st.write(rec.roupa)
    with col2:
        st.markdown("#### 🍲 O que comer")
        st.write(rec.comida)

    st.markdown("#### 💡 Sugestões para hoje")
    for sugestao in rec.sugestoes:
        st.markdown(f"- {sugestao}")

    if rec.alerta:
        st.warning(f"⚠️ {rec.alerta}")

    st.markdown("#### 💬 Pergunte qualquer coisa sobre o dia")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    question = st.chat_input("Ex.: posso levar a bicicleta hoje?")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                history = [
                    {"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]
                ]
                answer, used_offline_chat = ask_free(ctx, question, history, settings)
                st.write(answer)
                if used_offline_chat:
                    st.caption("Modo offline — resposta gerada localmente.")
        st.session_state.messages.append({"role": "assistant", "content": answer})

st.divider()
st.caption(
    f"Dados meteorológicos: [Open-Meteo](https://open-meteo.com/) (CC BY 4.0) · "
    f"Modelo: {settings.groq_model if settings.groq_api_key else 'modo offline (sem chave configurada)'}"
)
