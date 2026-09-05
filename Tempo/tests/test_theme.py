"""Testes do fundo dinâmico: todo weather_code conhecido deve gerar CSS válido."""

from src.theme import background_css
from src.weather import WMO_CODES


def test_background_css_contains_gradient_for_every_known_code():
    for code in WMO_CODES:
        css = background_css(code, is_day=True)
        assert "<style>" in css
        assert "background:" in css

        css_night = background_css(code, is_day=False)
        assert "<style>" in css_night


def test_storm_code_adds_lightning_animation():
    css = background_css(95, is_day=True)
    assert "raio" in css


def test_clear_day_vs_night_differ():
    day = background_css(0, is_day=True)
    night = background_css(0, is_day=False)
    assert day != night
