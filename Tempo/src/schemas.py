"""Contratos internos (Pydantic) para clima e recomendação."""

from __future__ import annotations

from pydantic import BaseModel


class City(BaseModel):
    name: str
    admin1: str | None = None
    country: str
    latitude: float
    longitude: float
    timezone: str


class CurrentWeather(BaseModel):
    temperature: float
    feels_like: float
    humidity: int
    precipitation: float
    wind_speed: float
    weather_code: int
    description: str
    is_day: bool


class WeatherContext(BaseModel):
    city: City
    current: CurrentWeather
    max_today: float
    min_today: float
    rain_chance_today: int
    uv_max_today: float | None = None


class Recommendation(BaseModel):
    resumo: str
    roupa: str
    comida: str
    sugestoes: list[str]
    alerta: str | None = None
