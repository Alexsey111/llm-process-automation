"""Конфигурация приложения. Значения берутся из окружения / файла .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


# --- Пути ---
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "automation.db"))
INPUTS_DIR = BASE_DIR / "inputs"
RESULTS_DIR = BASE_DIR / "results"

# --- LLM (OpenAI-совместимый провайдер, по умолчанию DeepSeek) ---
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "900"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
# JSON mode провайдера (если недоступен — автоматически деградируем до prompt-only)
USE_JSON_MODE = _as_bool(os.getenv("USE_JSON_MODE"), default=True)
# Число повторных вызовов LLM при невалидном JSON
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))