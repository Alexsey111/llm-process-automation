"""Клиент LLM: OpenAI-совместимый провайдер, режим structured output, повторные попытки."""
import json
import logging
import re
from typing import Any

from openai import OpenAI

from .config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_RETRIES,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    USE_JSON_MODE,
)

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not LLM_API_KEY:
            raise RuntimeError("LLM_API_KEY is not set (см. .env.example)")
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=LLM_TIMEOUT)
    return _client


def extract_json_object(raw: str) -> dict[str, Any]:
    """Вытаскивает первый JSON-объект из ответа LLM, срезая markdown-обёртки."""
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]

    return json.loads(raw)


def call_llm_extract(system_prompt: str, user_text: str) -> dict[str, Any]:
    """Вызывает LLM и возвращает распарсенный dict. Бросает исключение, если JSON невалиден после всех попыток."""
    client = get_client()
    kwargs: dict[str, Any] = {
        "model": LLM_MODEL,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    }

    last_error: Exception | None = None
    for attempt in range(LLM_MAX_RETRIES + 1):
        if USE_JSON_MODE and attempt == 0:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = client.chat.completions.create(**kwargs)
            raw = response.choices[0].message.content or ""
            return extract_json_object(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            # Невалидный JSON — пробуем ещё раз без json_mode (строже держим промпт)
            last_error = exc
            kwargs.pop("response_format", None)
            logger.warning("LLM вернула невалидный JSON (попытка %d): %s", attempt + 1, exc)
        except Exception as exc:  # сетевые/квотные ошибки — сразу наверх
            last_error = exc
            logger.error("Ошибка вызова LLM: %s", exc)
            raise LLMError(f"LLM call failed: {exc}") from exc

    raise LLMError(f"LLM returned invalid JSON after retries: {last_error}")


class LLMError(Exception):
    pass