"""Точка входа FastAPI-приложения."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db.database import init_db
from .api.ingest import router

logging.basicConfig(level=logging.INFO)

VERSION = "1.0.0"


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
    version=VERSION,
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {
        "service": app.title,
        "version": VERSION,
        "docs": "/docs",
        "endpoints": ["POST /ingest", "GET /audit", "GET /results", "GET /health"],
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}