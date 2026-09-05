"""Carrega variáveis de ambiente e expõe as configurações da aplicação."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from dotenv import load_dotenv
import os

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openai/gpt-oss-120b"


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None
    groq_model: str
    openrouter_api_key: str | None
    openrouter_model: str
    llm_provider: str


def load_settings() -> Settings:
    """Lê o `.env` e retorna as configurações. Nunca lança se faltar chave —
    a ausência de chave é tratada mais tarde pelo modo offline (RN-05)."""
    settings = Settings(
        groq_api_key=os.getenv("GROQ_API_KEY") or None,
        groq_model=os.getenv("GROQ_MODEL", DEFAULT_MODEL),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY") or None,
        openrouter_model=os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL),
        llm_provider=os.getenv("LLM_PROVIDER", "groq"),
    )
    if not settings.groq_api_key and not settings.openrouter_api_key:
        logger.warning("Nenhuma chave de LLM configurada — app rodará em modo offline.")
    return settings
