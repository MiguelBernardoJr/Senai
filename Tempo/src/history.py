"""Persistência local em SQLite: log de pesquisas e histórico diário de temperatura por cidade.

Adição pós-v1 (ver decisão D-10 em MEMORIA-PROJETO.md — a v1 original previa "sem banco
de dados"). Continua sem HTTP direto na UI: `app.py` chama estas funções, que por sua vez
chamam `weather.get_daily_history()` quando precisam de dado real.
"""

from __future__ import annotations

import logging
import random
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator

from src.schemas import City, DailyTemperature, WeatherContext
from src.weather import get_daily_history

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "clima_historico.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pesquisas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cidade TEXT NOT NULL,
    admin1 TEXT,
    pais TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    temperatura REAL NOT NULL,
    sensacao REAL NOT NULL,
    umidade INTEGER NOT NULL,
    buscado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historico_diario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cidade TEXT NOT NULL,
    pais TEXT NOT NULL,
    data TEXT NOT NULL,
    temp_max REAL NOT NULL,
    temp_min REAL NOT NULL,
    origem TEXT NOT NULL,
    UNIQUE(cidade, pais, data)
);
"""

PAST_DAYS = 7
FORECAST_DAYS = 8  # hoje + 7 dias futuros


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Cria as tabelas se ainda não existirem. Idempotente — pode ser chamado a cada rerun."""
    with _connection() as conn:
        conn.executescript(_SCHEMA)


def save_search(ctx: WeatherContext) -> None:
    """Registra a pesquisa (cidade, clima no momento e data/hora) no log local."""
    with _connection() as conn:
        conn.execute(
            "INSERT INTO pesquisas "
            "(cidade, admin1, pais, latitude, longitude, temperatura, sensacao, umidade, buscado_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ctx.city.name,
                ctx.city.admin1,
                ctx.city.country,
                ctx.city.latitude,
                ctx.city.longitude,
                ctx.current.temperature,
                ctx.current.feels_like,
                ctx.current.humidity,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )


def get_recent_searches(city: City, limit: int = 10) -> list[dict]:
    """Últimas pesquisas registradas para a cidade, mais recentes primeiro."""
    with _connection() as conn:
        rows = conn.execute(
            "SELECT temperatura, sensacao, umidade, buscado_em FROM pesquisas "
            "WHERE cidade = ? AND pais = ? ORDER BY buscado_em DESC LIMIT ?",
            (city.name, city.country, limit),
        ).fetchall()
    return [
        {"temperatura": r[0], "sensacao": r[1], "umidade": r[2], "buscado_em": r[3]} for r in rows
    ]


def _has_history(city: City) -> bool:
    with _connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM historico_diario WHERE cidade = ? AND pais = ?",
            (city.name, city.country),
        ).fetchone()
    return row[0] > 0


def _replace_daily_rows(city: City, series: list[DailyTemperature], origem: str) -> None:
    with _connection() as conn:
        for item in series:
            conn.execute(
                "INSERT OR REPLACE INTO historico_diario "
                "(cidade, pais, data, temp_max, temp_min, origem) VALUES (?, ?, ?, ?, ?, ?)",
                (city.name, city.country, item.date, item.temp_max, item.temp_min, origem),
            )


def _simulate_series(city: City, base_temp: float) -> list[DailyTemperature]:
    """Valores plausíveis quando a Open-Meteo está fora do ar e não há nenhum histórico
    salvo ainda para a cidade (RN-05 aplicado ao histórico: nunca deixa o gráfico vazio)."""
    rng = random.Random(f"{city.name}-{city.country}")
    today = date.today()
    series: list[DailyTemperature] = []
    for offset in range(-PAST_DAYS, FORECAST_DAYS - 1 + 1):
        day = today + timedelta(days=offset)
        drift = rng.uniform(-3.0, 3.0)
        series.append(
            DailyTemperature(
                date=day.isoformat(),
                temp_max=round(base_temp + 3 + drift, 1),
                temp_min=round(base_temp - 5 + drift, 1),
            )
        )
    return series


def update_history(ctx: WeatherContext) -> None:
    """Busca a série real (7 dias passados + hoje + 7 futuros) e atualiza `historico_diario`.

    Reescreve as linhas a cada busca (para os dias futuros virarem passado com o dado real
    quando chegar a data). Só usa valores simulados se a API falhar **e** ainda não houver
    nenhum histórico salvo para a cidade — não sobrescreve dado real por causa de uma falha
    passageira de rede.
    """
    city = ctx.city
    try:
        series = get_daily_history(city, past_days=PAST_DAYS, forecast_days=FORECAST_DAYS)
        _replace_daily_rows(city, series, origem="open-meteo")
        return
    except Exception:
        logger.warning("Histórico diário indisponível agora para %s.", city.name)

    if not _has_history(city):
        logger.warning("Sem histórico salvo para %s — usando valores simulados.", city.name)
        _replace_daily_rows(city, _simulate_series(city, ctx.current.temperature), origem="simulado")


def get_temperature_series(city: City) -> list[dict]:
    """Série (data, temp_max, temp_min, origem) para o gráfico de variação da cidade."""
    with _connection() as conn:
        rows = conn.execute(
            "SELECT data, temp_max, temp_min, origem FROM historico_diario "
            "WHERE cidade = ? AND pais = ? ORDER BY data",
            (city.name, city.country),
        ).fetchall()
    return [{"data": r[0], "temp_max": r[1], "temp_min": r[2], "origem": r[3]} for r in rows]
