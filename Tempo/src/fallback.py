"""Regras determinísticas de recomendação, sem LLM (RN-05).

Usadas quando o modelo falha ou, na F3, enquanto `llm.py` ainda não existe.
Base de decisão: sensação térmica, chance de chuva, vento e UV (seção 6 da especificação).
"""

from __future__ import annotations

from src.schemas import Recommendation, WeatherContext

RAIN_THRESHOLD = 50
WIND_THRESHOLD = 30.0
UV_THRESHOLD = 8.0
EXTREME_COLD_THRESHOLD = 5.0
STORM_CODES = {95, 96, 99}


def _clothing_and_food(feels_like: float) -> tuple[str, str]:
    if feels_like < 10:
        return (
            "Casaco pesado, roupas em camadas, touca e luvas.",
            "Um caldo ou sopa quente cai bem, fondue ou um chocolate quente para esquentar.",
        )
    if feels_like <= 17:
        return (
            "Jaqueta leve ou moletom, calça comprida.",
            "Massa, um ensopado ou feijoada; uma sopa leve também é uma boa pedida.",
        )
    if feels_like <= 24:
        return (
            "Camiseta, com uma camada extra para a noite.",
            "Uma refeição comum resolve bem, como um risoto ou grelhados.",
        )
    if feels_like <= 31:
        return (
            "Roupa leve e clara, de tecido respirável.",
            "Saladas e peixe grelhado são leves para o calor; frutas e sucos ajudam a refrescar.",
        )
    return (
        "Roupa mínima e leve, boné e protetor solar.",
        "Prefira comida fria como ceviche, gelados e beba bastante água.",
    )


def build_recommendation(ctx: WeatherContext) -> Recommendation:
    """Monta uma `Recommendation` só com regras locais, sem chamar nenhum LLM."""
    current = ctx.current
    roupa, comida = _clothing_and_food(current.feels_like)

    sugestoes: list[str] = []

    if ctx.rain_chance_today >= RAIN_THRESHOLD:
        roupa += " Leve guarda-chuva ou capa de chuva e prefira calçado fechado."
        sugestoes.append("Chance alta de chuva — leve guarda-chuva e prefira calçado fechado.")

    if current.wind_speed > WIND_THRESHOLD:
        roupa += " Um corta-vento ajuda com o vento forte."
        sugestoes.append("Vento forte hoje — um corta-vento faz diferença.")

    if ctx.uv_max_today is not None and ctx.uv_max_today >= UV_THRESHOLD:
        sugestoes.append("Índice UV alto — use protetor solar e evite o sol entre 10h e 16h.")

    if not current.is_day:
        sugestoes.append("Já é noite — vale uma camada extra de roupa.")

    if ctx.rain_chance_today < RAIN_THRESHOLD and 18 <= current.feels_like <= 31:
        sugestoes.append("Boa janela para uma caminhada ou atividade ao ar livre.")

    sugestoes.append("Confira a previsão de novo antes de sair por muito tempo.")
    sugestoes = sugestoes[:5]
    while len(sugestoes) < 3:
        sugestoes.append("Beba água regularmente ao longo do dia.")

    alerta: str | None = None
    if current.weather_code in STORM_CODES:
        alerta = "Risco de tempestade — evite ficar exposto ao ar livre."
    elif ctx.uv_max_today is not None and ctx.uv_max_today >= UV_THRESHOLD:
        alerta = "Índice UV muito alto hoje — exposição prolongada ao sol não é recomendada."
    elif current.feels_like < EXTREME_COLD_THRESHOLD:
        alerta = "Frio extremo — reduza o tempo exposto ao ar livre."

    resumo = (
        f"{current.description} em {ctx.city.name}, {current.temperature:.0f}°C "
        f"agora (sensação de {current.feels_like:.0f}°C)."
    )

    return Recommendation(
        resumo=resumo,
        roupa=roupa,
        comida=comida,
        sugestoes=sugestoes,
        alerta=alerta,
    )


def offline_chat_reply(ctx: WeatherContext) -> str:
    """Resposta fixa para o chat livre quando nenhum LLM está disponível (RN-05)."""
    current = ctx.current
    return (
        "No momento não consigo responder livremente (modo offline). "
        f"O clima agora em {ctx.city.name} é {current.description.lower()}, "
        f"{current.temperature:.0f}°C (sensação de {current.feels_like:.0f}°C), "
        f"com {ctx.rain_chance_today}% de chance de chuva hoje."
    )
