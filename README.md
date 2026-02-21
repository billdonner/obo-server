# OBO Server

Read-only REST API and web UI for OBO flashcard decks, powered by FastAPI and PostgreSQL.

**Live:** https://bd-obo-server.fly.dev

## Quick Start

```bash
cd ~/obo-server && uv sync
uv run obo-server
# API at http://127.0.0.1:9810/api/v1/decks
# Web UI at http://127.0.0.1:9810/
```

## Stack

- Python 3.12+, [FastAPI](https://fastapi.tiangolo.com/), [asyncpg](https://magicstack.github.io/asyncpg/)
- Embedded web UI — single HTML file, no build step
- Package manager: [uv](https://docs.astral.sh/uv/)

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web UI — browse decks and flip through cards |
| GET | `/api/v1/decks` | List decks (`?age=`, `?limit=`, `?offset=`) |
| GET | `/api/v1/decks/{id}` | Get deck with all cards |
| GET | `/metrics` | Health metrics (server-monitor format) |

## Web UI

The embedded web app at `/` lets you browse decks and flip through flashcards in the browser. It's a single `static/index.html` with vanilla JS — no React, no Vite, no build step.

Features:
- Deck list with age-range filter dropdown
- Click a deck to see all cards as flip-cards (click to flip question/answer)
- Responsive layout (mobile + desktop)
- Empty state when no decks exist

## Database

Reads from the `obo` Postgres database. Tables are created and populated by [obo-gen](https://github.com/billdonner/obo-gen) — this server is read-only.

Default DSN: `postgresql://nagz:nagz@localhost:5433/obo` (override with `OBO_DATABASE_URL`).

## Deployment

Deployed to [Fly.io](https://fly.io) via the [Flyz](https://github.com/billdonner/Flyz) infrastructure repo:

```bash
~/Flyz/scripts/deploy.sh obo-server
```

## Related Repos

| Repo | Description |
|------|-------------|
| [obo](https://github.com/billdonner/obo) | Hub — specs and documentation |
| [obo-gen](https://github.com/billdonner/obo-gen) | Swift CLI deck generator |
| [obo-ios](https://github.com/billdonner/obo-ios) | SwiftUI iOS flashcard app |
| [Flyz](https://github.com/billdonner/Flyz) | Fly.io deployment configs |
