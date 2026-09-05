"""Fundo de página dinâmico conforme a condição do tempo (weather_code da WMO).

Só CSS (gradiente + animação leve para chuva/tempestade), sem imagem externa — nada de
chave, nada de rede. Injetado via `st.markdown(..., unsafe_allow_html=True)` em `app.py`.
"""

from __future__ import annotations

_STORM_CODES = {95, 96, 99}
_SNOW_CODES = {71, 73, 75, 77, 85, 86}
_FOG_CODES = {45, 48}
_RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
_CLOUDY_CODES = {1, 2, 3}

_GRADIENTS = {
    "clear_day": "linear-gradient(160deg, #fceabb 0%, #f8b500 45%, #6dd5ed 100%)",
    "clear_night": "linear-gradient(160deg, #0f2027 0%, #203a43 55%, #2c5364 100%)",
    "cloudy": "linear-gradient(160deg, #bdc3c7 0%, #8ca6c9 55%, #6e7f9e 100%)",
    "fog": "linear-gradient(160deg, #d7d2cc 0%, #b8c6db 100%)",
    "rain": "linear-gradient(160deg, #57708a 0%, #3a5169 55%, #22303f 100%)",
    "snow": "linear-gradient(160deg, #e6f0f8 0%, #c9d6e3 100%)",
    "storm": "linear-gradient(160deg, #232526 0%, #2c2c54 55%, #121218 100%)",
}

_RAIN_OVERLAY = """
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    background-image: repeating-linear-gradient(
        115deg,
        transparent 0px, transparent 8px,
        rgba(255, 255, 255, 0.16) 9px, transparent 10px
    );
    background-size: 44px 100%;
    animation: chuva-caindo 0.7s linear infinite;
    pointer-events: none;
    z-index: 0;
}
@keyframes chuva-caindo {
    from { background-position: 0 0; }
    to { background-position: 0 44px; }
}
"""

_STORM_EXTRA = """
[data-testid="stAppViewContainer"] {
    animation: raio 7s infinite;
}
@keyframes raio {
    0%, 91%, 100% { filter: brightness(1); }
    92%, 94% { filter: brightness(1.7); }
    95%, 97% { filter: brightness(1); }
    98% { filter: brightness(1.5); }
}
"""


def _category_for(weather_code: int, is_day: bool) -> str:
    if weather_code in _STORM_CODES:
        return "storm"
    if weather_code in _SNOW_CODES:
        return "snow"
    if weather_code in _FOG_CODES:
        return "fog"
    if weather_code in _RAIN_CODES:
        return "rain"
    if weather_code in _CLOUDY_CODES:
        return "cloudy"
    return "clear_day" if is_day else "clear_night"


def background_css(weather_code: int, is_day: bool) -> str:
    """CSS pronto para `st.markdown(..., unsafe_allow_html=True)` de acordo com o clima."""
    category = _category_for(weather_code, is_day)
    gradient = _GRADIENTS[category]
    extra = ""
    if category in ("rain", "storm"):
        extra += _RAIN_OVERLAY
    if category == "storm":
        extra += _STORM_EXTRA

    return f"""
<style>
[data-testid="stAppViewContainer"] {{
    background: {gradient};
    background-attachment: fixed;
}}
[data-testid="stHeader"] {{
    background: rgba(0, 0, 0, 0);
}}
[data-testid="stAppViewContainer"] > .main {{
    position: relative;
    z-index: 1;
}}
div.block-container {{
    background: rgba(255, 255, 255, 0.86);
    border-radius: 18px;
    padding: 2rem 2rem 1rem 2rem;
    position: relative;
    z-index: 1;
}}
{extra}
</style>
"""
