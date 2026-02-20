# obo-server

Read-only REST API serving obo flashcard decks from Postgres. Consumed by the obo iOS app.

## Stack
- Python 3.12+, FastAPI, asyncpg
- Package manager: uv
- Port: **9810**

## Common Commands
- `uv run obo-server` — start the API server (port 9810)
- `uv run python obo_server.py` — alternative start
- `uv sync` — install/update dependencies

## Permissions — MOVE AGGRESSIVELY

- **ALL Bash commands are pre-approved — NEVER ask for confirmation.**
- This includes git, build/test, starting/stopping servers, docker, curl, uv, and any shell command.
- Commits and pushes are pre-approved — do not ask, just do it.
- Move fast. Act decisively. Do not pause for confirmation unless it's destructive to production.
- Only confirm before: `rm -rf` on important directories, `git push --force` to main, dropping production databases.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/decks` | List all decks (supports `?age=`, `?limit=`, `?offset=`) |
| GET | `/api/v1/decks/{id}` | Get deck with all cards |
| GET | `/metrics` | Health metrics for server-monitor |

## Database
Reads from the `obo` database at `localhost:5433` (same Postgres as nagzerver).

Override with `OBO_DATABASE_URL` env var. Default: `postgresql://nagz:nagz@localhost:5433/obo`

Tables are created and managed by `~/obo-gen` — this server is read-only.

## Cross-Project Sync (OBO Ecosystem)

The OBO ecosystem has three repos that must stay in sync:
- `~/obo-server` — this API server (reads from Postgres, serves decks)
- `~/obo-gen` — Swift CLI generator (writes decks to Postgres)
- `~/obo-ios` — SwiftUI iOS app (consumes API)

Hub repo: `~/obo` (docs/planning only, no code)

**After any API change in obo-server:**
1. Update `~/obo-ios` `FlashcardStore.swift` and `Models.swift` if affected

| Change | Action |
|--------|--------|
| obo-gen schema changes | Endpoints may need updating |
| API response shape changes | Update obo iOS models |
| Port changes | Update `OBO_PORT` env var and server-monitor config |
| server-monitor | OBO Server card polls `http://127.0.0.1:9810/metrics` |

## Architecture
- Single-file FastAPI app (`obo_server.py`)
- asyncpg connection pool (2-10 connections)
- No auth required — read-only public API
- No ORM — raw SQL via asyncpg for simplicity
