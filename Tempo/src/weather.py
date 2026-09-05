"""Acesso à Open-Meteo (geocoding + previsão) e parsing para os contratos internos.

Camada de dados: não decide nada, não chama LLM. A UI não chama HTTP direto —
sempre passa por `geocode_city()` e `get_forecast()`.
"""

from __future__ import annotations

import logging

import requests

from src.schemas import City, CurrentWeather, WeatherContext

logger = logging.getLogger(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_SECONDS = 10

WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("Céu limpo", "☀️"),
    1: ("Predominantemente limpo", "🌤️"),
    2: ("Parcialmente nublado", "⛅"),
    3: ("Encoberto", "☁️"),
    45: ("Névoa", "🌫️"),
    48: ("Névoa com geada", "🌫️"),
    51: ("Garoa fraca", "🌦️"),
    53: ("Garoa moderada", "🌦️"),
    55: ("Garoa forte", "🌦️"),
    56: ("Garoa congelante fraca", "🌦️"),
    57: ("Garoa congelante forte", "🌦️"),
    61: ("Chuva fraca", "🌧️"),
    63: ("Chuva moderada", "🌧️"),
    65: ("Chuva forte", "🌧️"),
    66: ("Chuva congelante fraca", "🌧️"),
    67: ("Chuva congelante forte", "🌧️"),
    71: ("Neve fraca", "🌨️"),
    73: ("Neve moderada", "🌨️"),
    75: ("Neve forte", "🌨️"),
    77: ("Grãos de neve", "🌨️"),
    80: ("Pancadas de chuva fracas", "🌦️"),
    81: ("Pancadas de chuva moderadas", "🌦️"),
    82: ("Pancadas de chuva violentas", "⛈️"),
    85: ("Pancadas de neve fracas", "🌨️"),
    86: ("Pancadas de neve fortes", "🌨️"),
    95: ("Tempestade", "⛈️"),
    96: ("Tempestade com granizo fraco", "⛈️"),
    99: ("Tempestade com granizo forte", "⛈️"),
}

UNKNOWN_WEATHER = ("Condição não identificada", "❓")


def describe_weather_code(code: int) -> tuple[str, str]:
    """Traduz um `weather_code` da WMO para (descrição, ícone) em pt-BR."""
    return WMO_CODES.get(code, UNKNOWN_WEATHER)


def parse_geocode_results(data: dict) -> list[City]:
    """Converte o JSON de `/v1/search` em uma lista de `City`. Lista vazia = não encontrada."""
    results = data.get("results") or []
    return [
        City(
            name=r["name"],
            admin1=r.get("admin1"),
            country=r["country"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            timezone=r["timezone"],
        )
        for r in results
    ]


def to_context(city: City, raw: dict) -> WeatherContext:
    """Converte o JSON de `/v1/forecast` + a `City` já resolvida em `WeatherContext`."""
    current = raw["current"]
    daily = raw["daily"]
    description, _icon = describe_weather_code(current["weather_code"])

    current_weather = CurrentWeather(
        temperature=current["temperature_2m"],
        feels_like=current["apparent_temperature"],
        humidity=current["relative_humidity_2m"],
        precipitation=current["precipitation"],
        wind_speed=current["wind_speed_10m"],
        weather_code=current["weather_code"],
        description=description,
        is_day=bool(current["is_day"]),
    )

    uv_values = daily.get("uv_index_max")
    uv_max_today = uv_values[0] if uv_values else None

    return WeatherContext(
        city=city,
        current=current_weather,
        max_today=daily["temperature_2m_max"][0],
        min_today=daily["temperature_2m_min"][0],
        rain_chance_today=daily["precipitation_probability_max"][0],
        uv_max_today=uv_max_today,
    )


def geocode_city(name: str, count: int = 5) -> list[City]:
    """Resolve um nome de cidade em candidatos com lat/lon (RN-06 trata a ambiguidade)."""
    params = {"name": name, "count": count, "language": "pt", "format": "json"}
    try:
        response = requests.get(GEOCODING_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Falha ao consultar geocoding da Open-Meteo para %r", name)
        raise
    return parse_geocode_results(response.json())


def get_forecast(city: City) -> WeatherContext:
    """Busca a previsão atual + 3 dias para uma `City` já resolvida."""
    params = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
        "precipitation,weather_code,wind_speed_10m,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max,uv_index_max,sunrise,sunset",
        "timezone": "auto",
        "forecast_days": 3,
    }
    try:
        response = requests.get(FORECAST_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Falha ao consultar previsão da Open-Meteo para %s", city.name)
        raise
    return to_context(city, response.json())
