"""Testes de parsing do módulo weather. JSON fixo, sem chamada de rede."""

from src.schemas import City
from src.weather import describe_weather_code, parse_geocode_results, to_context

GEOCODE_RESPONSE = {
    "results": [
        {
            "id": 3452925,
            "name": "Pirapozinho",
            "latitude": -22.27417,
            "longitude": -51.49889,
            "country": "Brasil",
            "country_code": "BR",
            "admin1": "São Paulo",
            "timezone": "America/Sao_Paulo",
        }
    ]
}

FORECAST_RESPONSE = {
    "current": {
        "time": "2026-09-05T14:30",
        "temperature_2m": 27.4,
        "apparent_temperature": 29.1,
        "relative_humidity_2m": 58,
        "precipitation": 0.0,
        "weather_code": 2,
        "wind_speed_10m": 11.5,
        "is_day": 1,
    },
    "current_units": {"temperature_2m": "°C", "wind_speed_10m": "km/h"},
    "daily": {
        "time": ["2026-09-05", "2026-09-06", "2026-09-07"],
        "temperature_2m_max": [29.8, 31.2, 24.0],
        "temperature_2m_min": [17.1, 18.4, 16.2],
        "precipitation_probability_max": [10, 5, 80],
        "uv_index_max": [9.1, 9.4, 5.2],
    },
}


def test_parse_geocode_results_returns_city():
    cities = parse_geocode_results(GEOCODE_RESPONSE)

    assert len(cities) == 1
    city = cities[0]
    assert city.name == "Pirapozinho"
    assert city.admin1 == "São Paulo"
    assert city.country == "Brasil"
    assert city.latitude == -22.27417
    assert city.longitude == -51.49889
    assert city.timezone == "America/Sao_Paulo"


def test_parse_geocode_results_empty_when_no_results():
    assert parse_geocode_results({}) == []
    assert parse_geocode_results({"results": []}) == []


def test_describe_weather_code_known():
    description, icon = describe_weather_code(2)
    assert description == "Parcialmente nublado"
    assert icon


def test_describe_weather_code_unknown():
    description, _icon = describe_weather_code(-1)
    assert description == "Condição não identificada"


def test_to_context_parses_forecast_and_city():
    city = City(
        name="Pirapozinho",
        admin1="São Paulo",
        country="Brasil",
        latitude=-22.27417,
        longitude=-51.49889,
        timezone="America/Sao_Paulo",
    )

    ctx = to_context(city, FORECAST_RESPONSE)

    assert ctx.city == city
    assert ctx.current.temperature == 27.4
    assert ctx.current.feels_like == 29.1
    assert ctx.current.humidity == 58
    assert ctx.current.precipitation == 0.0
    assert ctx.current.wind_speed == 11.5
    assert ctx.current.weather_code == 2
    assert ctx.current.description == "Parcialmente nublado"
    assert ctx.current.is_day is True
    assert ctx.max_today == 29.8
    assert ctx.min_today == 17.1
    assert ctx.rain_chance_today == 10
    assert ctx.uv_max_today == 9.1


def test_to_context_handles_missing_uv_index():
    city = City(
        name="Pirapozinho",
        country="Brasil",
        latitude=-22.27417,
        longitude=-51.49889,
        timezone="America/Sao_Paulo",
    )
    raw = {
        "current": FORECAST_RESPONSE["current"],
        "daily": {**FORECAST_RESPONSE["daily"], "uv_index_max": []},
    }

    ctx = to_context(city, raw)

    assert ctx.uv_max_today is None
