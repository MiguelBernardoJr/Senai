"""Testes das regras determinísticas de fallback (faixas de temperatura/chuva)."""

from src.fallback import build_recommendation
from src.schemas import City, CurrentWeather, WeatherContext

CITY = City(
    name="Pirapozinho",
    admin1="São Paulo",
    country="Brasil",
    latitude=-22.27417,
    longitude=-51.49889,
    timezone="America/Sao_Paulo",
)


def _ctx(
    feels_like: float,
    *,
    rain_chance_today: int = 10,
    wind_speed: float = 10.0,
    uv_max_today: float | None = 5.0,
    weather_code: int = 1,
    is_day: bool = True,
    temperature: float | None = None,
) -> WeatherContext:
    return WeatherContext(
        city=CITY,
        current=CurrentWeather(
            temperature=temperature if temperature is not None else feels_like,
            feels_like=feels_like,
            humidity=50,
            precipitation=0.0,
            wind_speed=wind_speed,
            weather_code=weather_code,
            description="Predominantemente limpo",
            is_day=is_day,
        ),
        max_today=feels_like + 5,
        min_today=feels_like - 5,
        rain_chance_today=rain_chance_today,
        uv_max_today=uv_max_today,
    )


def test_cold_band_below_10():
    rec = build_recommendation(_ctx(5.0))
    assert "casaco" in rec.roupa.lower()
    assert "sopa" in rec.comida.lower() or "caldo" in rec.comida.lower()


def test_band_10_to_17():
    rec = build_recommendation(_ctx(14.0))
    assert "jaqueta" in rec.roupa.lower() or "moletom" in rec.roupa.lower()
    assert "massa" in rec.comida.lower() or "feijoada" in rec.comida.lower() or "ensopado" in rec.comida.lower()


def test_band_18_to_24():
    rec = build_recommendation(_ctx(20.0))
    assert "camiseta" in rec.roupa.lower()
    assert "risoto" in rec.comida.lower() or "grelhados" in rec.comida.lower()


def test_band_25_to_31():
    rec = build_recommendation(_ctx(28.0))
    assert "leve" in rec.roupa.lower()
    assert "salada" in rec.comida.lower() or "peixe grelhado" in rec.comida.lower()


def test_band_above_31():
    rec = build_recommendation(_ctx(34.0))
    assert "protetor solar" in rec.roupa.lower()
    assert "ceviche" in rec.comida.lower() or "gelados" in rec.comida.lower()


def test_rain_modifier_adds_umbrella_advice():
    rec = build_recommendation(_ctx(20.0, rain_chance_today=80))
    assert "guarda-chuva" in rec.roupa.lower()
    assert any("chuva" in s.lower() for s in rec.sugestoes)


def test_no_rain_modifier_below_threshold():
    rec = build_recommendation(_ctx(20.0, rain_chance_today=10))
    assert "guarda-chuva" not in rec.roupa.lower()


def test_wind_modifier_adds_windbreaker_advice():
    rec = build_recommendation(_ctx(20.0, wind_speed=35.0))
    assert "corta-vento" in rec.roupa.lower()
    assert any("vento" in s.lower() for s in rec.sugestoes)


def test_uv_alto_gera_alerta_e_sugestao():
    rec = build_recommendation(_ctx(28.0, uv_max_today=9.0))
    assert rec.alerta is not None
    assert "uv" in rec.alerta.lower()
    assert any("uv" in s.lower() for s in rec.sugestoes)


def test_storm_weather_code_gera_alerta():
    rec = build_recommendation(_ctx(22.0, weather_code=95, uv_max_today=3.0))
    assert rec.alerta is not None
    assert "tempestade" in rec.alerta.lower()


def test_extreme_cold_gera_alerta():
    rec = build_recommendation(_ctx(2.0, uv_max_today=1.0))
    assert rec.alerta is not None
    assert "frio" in rec.alerta.lower()


def test_no_alert_in_mild_calm_weather():
    rec = build_recommendation(_ctx(20.0, rain_chance_today=10, wind_speed=5.0, uv_max_today=3.0))
    assert rec.alerta is None


def test_night_adds_extra_layer_suggestion():
    rec = build_recommendation(_ctx(20.0, is_day=False))
    assert any("noite" in s.lower() for s in rec.sugestoes)


def test_sugestoes_between_3_and_5_items_and_within_length_limit():
    rec = build_recommendation(_ctx(20.0, rain_chance_today=80, wind_speed=35.0, uv_max_today=9.0, is_day=False))
    assert 3 <= len(rec.sugestoes) <= 5
    assert all(len(s) <= 120 for s in rec.sugestoes)


def test_resumo_mentions_city_and_temperature():
    rec = build_recommendation(_ctx(20.0, temperature=21.3))
    assert "Pirapozinho" in rec.resumo
