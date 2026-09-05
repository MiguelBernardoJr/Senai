"""Testes do módulo history (SQLite). Banco isolado em arquivo temporário, sem rede real."""

import src.history as history
from src.schemas import City, CurrentWeather, DailyTemperature, WeatherContext

CITY = City(
    name="Pirapozinho",
    admin1="São Paulo",
    country="Brasil",
    latitude=-22.27417,
    longitude=-51.49889,
    timezone="America/Sao_Paulo",
)


def _ctx(temperature: float = 27.4) -> WeatherContext:
    return WeatherContext(
        city=CITY,
        current=CurrentWeather(
            temperature=temperature,
            feels_like=temperature + 1.5,
            humidity=58,
            precipitation=0.0,
            wind_speed=11.5,
            weather_code=2,
            description="Parcialmente nublado",
            is_day=True,
        ),
        max_today=29.8,
        min_today=17.1,
        rain_chance_today=10,
        uv_max_today=9.1,
    )


def _use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "test_clima.db")
    history.init_db()


def test_save_search_and_get_recent_searches(tmp_path, monkeypatch):
    _use_tmp_db(tmp_path, monkeypatch)
    ctx = _ctx()

    history.save_search(ctx)
    recent = history.get_recent_searches(CITY)

    assert len(recent) == 1
    assert recent[0]["temperatura"] == 27.4
    assert recent[0]["umidade"] == 58
    assert recent[0]["buscado_em"]


def test_get_recent_searches_empty_for_unknown_city(tmp_path, monkeypatch):
    _use_tmp_db(tmp_path, monkeypatch)

    assert history.get_recent_searches(CITY) == []


def test_update_history_uses_real_series_when_available(tmp_path, monkeypatch):
    _use_tmp_db(tmp_path, monkeypatch)
    fake_series = [
        DailyTemperature(date="2026-09-01", temp_max=30.0, temp_min=18.0),
        DailyTemperature(date="2026-09-02", temp_max=31.0, temp_min=19.0),
    ]
    monkeypatch.setattr(history, "get_daily_history", lambda city, **kwargs: fake_series)

    history.update_history(_ctx())
    series = history.get_temperature_series(CITY)

    assert len(series) == 2
    assert series[0]["origem"] == "open-meteo"
    assert series[0]["temp_max"] == 30.0


def test_update_history_falls_back_to_simulated_when_api_fails_and_no_history(tmp_path, monkeypatch):
    _use_tmp_db(tmp_path, monkeypatch)

    def _boom(city, **kwargs):
        raise ConnectionError("sem rede")

    monkeypatch.setattr(history, "get_daily_history", _boom)

    history.update_history(_ctx())
    series = history.get_temperature_series(CITY)

    assert len(series) == history.PAST_DAYS + history.FORECAST_DAYS
    assert all(item["origem"] == "simulado" for item in series)


def test_update_history_does_not_overwrite_real_data_on_transient_failure(tmp_path, monkeypatch):
    _use_tmp_db(tmp_path, monkeypatch)
    real_series = [DailyTemperature(date="2026-09-01", temp_max=30.0, temp_min=18.0)]
    monkeypatch.setattr(history, "get_daily_history", lambda city, **kwargs: real_series)
    history.update_history(_ctx())

    def _boom(city, **kwargs):
        raise ConnectionError("sem rede agora")

    monkeypatch.setattr(history, "get_daily_history", _boom)
    history.update_history(_ctx())

    series = history.get_temperature_series(CITY)
    assert len(series) == 1
    assert series[0]["origem"] == "open-meteo"


def test_update_history_replaces_rows_on_repeated_real_fetch(tmp_path, monkeypatch):
    _use_tmp_db(tmp_path, monkeypatch)
    first = [DailyTemperature(date="2026-09-01", temp_max=30.0, temp_min=18.0)]
    monkeypatch.setattr(history, "get_daily_history", lambda city, **kwargs: first)
    history.update_history(_ctx())

    updated = [DailyTemperature(date="2026-09-01", temp_max=32.5, temp_min=20.0)]
    monkeypatch.setattr(history, "get_daily_history", lambda city, **kwargs: updated)
    history.update_history(_ctx())

    series = history.get_temperature_series(CITY)
    assert len(series) == 1
    assert series[0]["temp_max"] == 32.5
