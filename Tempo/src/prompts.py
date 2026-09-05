"""Prompts do LLM: recomendação estruturada e pergunta livre."""

from __future__ import annotations

from src.schemas import WeatherContext

SYSTEM_PROMPT = (
    "Você é um assistente brasileiro que recomenda roupa, comida e atividades a partir "
    "de dados meteorológicos reais. Você recebe os dados já medidos — nunca invente, "
    "altere ou estime números. Escreva em português do Brasil, direto e prático, sem "
    "floreio. Responda SOMENTE com o objeto JSON solicitado, sem markdown e sem texto "
    "fora do JSON."
)

FREE_QA_SYSTEM_PROMPT = (
    "Você é um assistente brasileiro que recomenda roupa, comida e atividades a partir "
    "de dados meteorológicos reais. Você recebe os dados já medidos — nunca invente, "
    "altere ou estime números. Escreva em português do Brasil, direto e prático, sem "
    "floreio. Responda em texto corrido, sem JSON e sem markdown."
)


def _weather_block(ctx: WeatherContext) -> str:
    admin1 = f"{ctx.city.admin1}, " if ctx.city.admin1 else ""
    uv = ctx.uv_max_today if ctx.uv_max_today is not None else "não disponível"
    return (
        f"- Cidade: {ctx.city.name}, {admin1}{ctx.city.country}\n"
        f"- Condição: {ctx.current.description}\n"
        f"- Temperatura: {ctx.current.temperature}°C\n"
        f"- Sensação térmica: {ctx.current.feels_like}°C\n"
        f"- Umidade: {ctx.current.humidity}%\n"
        f"- Precipitação agora: {ctx.current.precipitation} mm\n"
        f"- Vento: {ctx.current.wind_speed} km/h\n"
        f"- Máxima hoje: {ctx.max_today}°C\n"
        f"- Mínima hoje: {ctx.min_today}°C\n"
        f"- Chance de chuva hoje: {ctx.rain_chance_today}%\n"
        f"- Índice UV máximo hoje: {uv}\n"
        f"- Período: {'dia' if ctx.current.is_day else 'noite'}"
    )


def build_recommendation_prompt(ctx: WeatherContext) -> str:
    """Serializa o `WeatherContext` + instrução de campos e limites para a saída estruturada."""
    return (
        "Dados meteorológicos medidos agora:\n"
        f"{_weather_block(ctx)}\n\n"
        "Gere uma recomendação em JSON com exatamente estes campos:\n"
        '- "resumo": 1 frase sobre o tempo agora.\n'
        '- "roupa": 2 a 4 frases sobre o que vestir.\n'
        '- "comida": 2 a 4 frases sobre o que comer, citando pelo menos 1 prato específico.\n'
        '- "sugestoes": lista de 3 a 5 itens curtos (no máximo 120 caracteres cada).\n'
        '- "alerta": um alerta real (UV alto, tempestade, frio extremo) ou null se não houver risco.\n\n'
        "Responda SOMENTE o objeto JSON, sem crase, sem markdown, sem texto antes ou depois."
    )


def build_free_qa_prompt(ctx: WeatherContext, question: str) -> str:
    """Contexto do clima + pergunta do usuário. Saída esperada é texto livre, não JSON."""
    return (
        f"Dados meteorológicos medidos agora em {ctx.city.name}, {ctx.city.country}:\n"
        f"{_weather_block(ctx)}\n\n"
        f"Pergunta do usuário: {question}\n\n"
        "Responda em texto livre, direto, em português do Brasil. Se a pergunta não tiver "
        "relação com clima, responda normalmente, mas nunca invente dado meteorológico — "
        "use apenas os dados acima."
    )
