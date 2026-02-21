"""OBO Server — REST API for flashcard decks stored in Postgres."""

from __future__ import annotations

import logging
import os
import pathlib
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger("obo_server")

STATIC_DIR = pathlib.Path(__file__).parent / "static"

# ---------------------------------------------------------------------------
# Database configuration — individual env vars with sensible defaults,
# composed into a DSN.  OBO_DATABASE_URL overrides everything if set.
# ---------------------------------------------------------------------------

_DB_HOST = os.environ.get("OBO_DB_HOST", "localhost")
_DB_PORT = os.environ.get("OBO_DB_PORT", "5432")
_DB_USER = os.environ.get("OBO_DB_USER", "postgres")
_DB_PASSWORD = os.environ.get("OBO_DB_PASSWORD", "postgres")
_DB_NAME = os.environ.get("OBO_DB_NAME", "obo")

DATABASE_URL = os.environ.get(
    "OBO_DATABASE_URL",
    f"postgresql://{_DB_USER}:{_DB_PASSWORD}@{_DB_HOST}:{_DB_PORT}/{_DB_NAME}",
)
PORT = int(os.environ.get("OBO_PORT", "9810"))

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CardResponse(BaseModel):
    position: int
    question: str
    answer: str


class DeckSummary(BaseModel):
    id: int
    topic: str
    age_range: str
    voice: str | None
    card_count: int
    created_at: str


class DeckDetail(BaseModel):
    id: int
    topic: str
    age_range: str
    voice: str | None
    card_count: int
    created_at: str
    cards: list[CardResponse]


class DecksResponse(BaseModel):
    decks: list[DeckSummary]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_pool() -> asyncpg.Pool:
    """Return the global connection pool or raise if it was never created."""
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    return pool


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    yield
    if pool:
        await pool.close()


app = FastAPI(
    title="OBO Deck API",
    version="0.1.0",
    description="Read-only API for obo flashcard decks",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint.  Returns DB connectivity status."""
    result: dict = {"status": "ok"}
    try:
        p = _require_pool()
        db_ok = await p.fetchval("SELECT 1")
        result["database"] = "connected" if db_ok == 1 else "unexpected"
    except RuntimeError:
        result["database"] = "pool_not_initialized"
    except Exception as exc:
        result["status"] = "degraded"
        result["database"] = f"error: {exc}"
    return result


@app.get("/api/v1/decks", response_model=DecksResponse)
async def list_decks(
    age: str | None = Query(None, description="Filter by age range (e.g. 6-8)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all saved decks, optionally filtered by age range."""
    p = _require_pool()

    try:
        if age:
            rows = await p.fetch(
                "SELECT id, topic, age_range, voice, card_count, created_at "
                "FROM decks WHERE age_range = $1 ORDER BY id DESC LIMIT $2 OFFSET $3",
                age, limit, offset,
            )
            total = await p.fetchval(
                "SELECT COUNT(*) FROM decks WHERE age_range = $1", age
            )
        else:
            rows = await p.fetch(
                "SELECT id, topic, age_range, voice, card_count, created_at "
                "FROM decks ORDER BY id DESC LIMIT $1 OFFSET $2",
                limit, offset,
            )
            total = await p.fetchval("SELECT COUNT(*) FROM decks")

        decks = [
            DeckSummary(
                id=r["id"],
                topic=r["topic"],
                age_range=r["age_range"],
                voice=r["voice"],
                card_count=r["card_count"],
                created_at=r["created_at"].isoformat(),
            )
            for r in rows
        ]
        return DecksResponse(decks=decks, total=total)
    except Exception as exc:
        logger.exception("Error listing decks")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Database error: {exc}"},
        )


@app.get("/api/v1/decks/{deck_id}", response_model=DeckDetail)
async def get_deck(deck_id: int):
    """Get a single deck with all its cards."""
    p = _require_pool()

    try:
        row = await p.fetchrow(
            "SELECT id, topic, age_range, voice, card_count, created_at "
            "FROM decks WHERE id = $1",
            deck_id,
        )
        if row is None:
            raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

        card_rows = await p.fetch(
            "SELECT position, question, answer FROM cards "
            "WHERE deck_id = $1 ORDER BY position",
            deck_id,
        )

        return DeckDetail(
            id=row["id"],
            topic=row["topic"],
            age_range=row["age_range"],
            voice=row["voice"],
            card_count=row["card_count"],
            created_at=row["created_at"].isoformat(),
            cards=[
                CardResponse(position=c["position"], question=c["question"], answer=c["answer"])
                for c in card_rows
            ],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error fetching deck %s", deck_id)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Database error: {exc}"},
        )


@app.get("/metrics")
async def metrics():
    """Health/metrics endpoint for server-monitor."""
    p = _require_pool()

    try:
        total_decks = await p.fetchval("SELECT COUNT(*) FROM decks")
        total_cards = await p.fetchval("SELECT COUNT(*) FROM cards")
        return {
            "metrics": [
                {"key": "total_decks", "label": "Total Decks", "value": total_decks, "unit": "count"},
                {"key": "total_cards", "label": "Total Cards", "value": total_cards, "unit": "count"},
            ]
        }
    except Exception as exc:
        logger.exception("Error fetching metrics")
        return JSONResponse(
            status_code=500,
            content={"metrics": [], "error": f"Database error: {exc}"},
        )


# ---------------------------------------------------------------------------
# Web UI
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def run() -> None:
    uvicorn.run("obo_server:app", host="127.0.0.1", port=PORT, reload=False)


if __name__ == "__main__":
    run()
