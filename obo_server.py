"""OBO Server — REST API for flashcard decks stored in Postgres."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

DATABASE_URL = os.environ.get(
    "OBO_DATABASE_URL", "postgresql://nagz:nagz@localhost:5433/obo"
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

@app.get("/api/v1/decks", response_model=DecksResponse)
async def list_decks(
    age: str | None = Query(None, description="Filter by age range (e.g. 6-8)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all saved decks, optionally filtered by age range."""
    assert pool is not None

    if age:
        rows = await pool.fetch(
            "SELECT id, topic, age_range, voice, card_count, created_at "
            "FROM decks WHERE age_range = $1 ORDER BY id DESC LIMIT $2 OFFSET $3",
            age, limit, offset,
        )
        total = await pool.fetchval(
            "SELECT COUNT(*) FROM decks WHERE age_range = $1", age
        )
    else:
        rows = await pool.fetch(
            "SELECT id, topic, age_range, voice, card_count, created_at "
            "FROM decks ORDER BY id DESC LIMIT $1 OFFSET $2",
            limit, offset,
        )
        total = await pool.fetchval("SELECT COUNT(*) FROM decks")

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


@app.get("/api/v1/decks/{deck_id}", response_model=DeckDetail)
async def get_deck(deck_id: int):
    """Get a single deck with all its cards."""
    assert pool is not None

    row = await pool.fetchrow(
        "SELECT id, topic, age_range, voice, card_count, created_at "
        "FROM decks WHERE id = $1",
        deck_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

    card_rows = await pool.fetch(
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


@app.get("/metrics")
async def metrics():
    """Health/metrics endpoint for server-monitor."""
    assert pool is not None
    total_decks = await pool.fetchval("SELECT COUNT(*) FROM decks")
    total_cards = await pool.fetchval("SELECT COUNT(*) FROM cards")
    return {
        "metrics": [
            {"key": "total_decks", "label": "Total Decks", "value": total_decks, "unit": "count"},
            {"key": "total_cards", "label": "Total Cards", "value": total_cards, "unit": "count"},
        ]
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def run() -> None:
    uvicorn.run("obo_server:app", host="127.0.0.1", port=PORT, reload=False)


if __name__ == "__main__":
    run()
