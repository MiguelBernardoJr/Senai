"""Interpretação do clima via LLM (Groq, com fallback OpenRouter) — mesmo SDK `openai`,
trocando `base_url`, `api_key` e `model` (seção 8 da especificação).

Se os dois provedores falharem (rede, quota, JSON inválido mesmo após retry), a
recomendação estruturada cai para `fallback.build_recommendation` (RN-05).
"""

from __future__ import annotations

import json
import logging

from openai import OpenAI
from pydantic import ValidationError

from src.config import Settings
from src.fallback import build_recommendation, offline_chat_reply
from src.prompts import (
    FREE_QA_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_free_qa_prompt,
    build_recommendation_prompt,
)
from src.schemas import Recommendation, WeatherContext

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MAX_TOKENS = 1000
REINFORCED_SUFFIX = "\n\nResponda SOMENTE com o objeto JSON, sem markdown, sem texto antes ou depois."


def get_client(provider: str, settings: Settings) -> tuple[OpenAI, str] | None:
    """Monta um cliente `openai` apontado para o provedor pedido. `None` se faltar chave."""
    if provider == "groq":
        if not settings.groq_api_key:
            return None
        return OpenAI(api_key=settings.groq_api_key, base_url=GROQ_BASE_URL), settings.groq_model
    if provider == "openrouter":
        if not settings.openrouter_api_key:
            return None
        return OpenAI(api_key=settings.openrouter_api_key, base_url=OPENROUTER_BASE_URL), settings.openrouter_model
    raise ValueError(f"Provedor de LLM desconhecido: {provider!r}")


def _provider_order(settings: Settings) -> list[str]:
    primary = settings.llm_provider
    fallback_provider = "openrouter" if primary == "groq" else "groq"
    return [primary, fallback_provider]


def _complete(client: OpenAI, model: str, system: str, user: str, temperature: float) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=MAX_TOKENS,
    )
    return response.choices[0].message.content or ""


def _parse_recommendation(content: str) -> Recommendation:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:] if lines and lines[0].startswith("```") else lines
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    data = json.loads(cleaned)
    return Recommendation.model_validate(data)


def _structured_with_retry(client: OpenAI, model: str, ctx: WeatherContext) -> Recommendation | None:
    prompt = build_recommendation_prompt(ctx)
    try:
        content = _complete(client, model, SYSTEM_PROMPT, prompt, temperature=0.7)
        return _parse_recommendation(content)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Recomendação com JSON inválido na 1ª tentativa (%s), tentando retry", exc)
    except Exception:
        logger.exception("Falha ao consultar %s na 1ª tentativa", model)
        return None

    try:
        content = _complete(client, model, SYSTEM_PROMPT, prompt + REINFORCED_SUFFIX, temperature=0.0)
        return _parse_recommendation(content)
    except Exception as exc:
        logger.warning("Recomendação falhou também no retry (%s)", exc)
        return None


def ask_structured(ctx: WeatherContext, settings: Settings) -> tuple[Recommendation, bool]:
    """Pede a recomendação estruturada ao LLM. Retorna `(recommendation, used_offline)`."""
    for provider in _provider_order(settings):
        client_info = get_client(provider, settings)
        if client_info is None:
            continue
        client, model = client_info
        recommendation = _structured_with_retry(client, model, ctx)
        if recommendation is not None:
            return recommendation, False

    logger.warning("Todos os provedores de LLM falharam — usando fallback local.")
    return build_recommendation(ctx), True


def ask_free(
    ctx: WeatherContext, question: str, history: list[dict[str, str]], settings: Settings
) -> tuple[str, bool]:
    """Responde uma pergunta livre com o clima no contexto. Retorna `(resposta, used_offline)`."""
    prompt = build_free_qa_prompt(ctx, question)
    messages = [{"role": "system", "content": FREE_QA_SYSTEM_PROMPT}, *history, {"role": "user", "content": prompt}]

    for provider in _provider_order(settings):
        client_info = get_client(provider, settings)
        if client_info is None:
            continue
        client, model = client_info
        try:
            response = client.chat.completions.create(
                model=model, messages=messages, temperature=0.3, max_tokens=MAX_TOKENS
            )
            return response.choices[0].message.content or "", False
        except Exception:
            logger.exception("Falha ao consultar %s para pergunta livre", model)
            continue

    return offline_chat_reply(ctx), True
