"""Уровень 1 контроля качества: парсинг ответа LLM в Pydantic-схему."""
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def validate_schema(model: type[T], data: dict) -> tuple[T | None, str | None]:
    """Возвращает (result, None) при успехе или (None, сообщение_об_ошибке) при неудаче."""
    try:
        return model.model_validate(data), None
    except ValidationError as exc:
        errors = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or '<root>'}: {e['msg']}"
            for e in exc.errors()
        )
        return None, f"Schema validation failed: {errors}"