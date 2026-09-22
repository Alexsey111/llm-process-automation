"""Точка входа FastAPI-приложения."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db.database import init_db
from .api.ingest import router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="LLM Business Automation Engine",
    description=(
        "Вход → LLM (structured JSON) → контроль качества (Pydantic + business rules) "
        "→ действие (SQLite + audit). Кейсы: financial (F) и insurance (H)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}