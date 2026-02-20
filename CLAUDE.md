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

## Cross-Project Integration

| Change | Action |
|--------|--------|
| obo-gen schema changes | Endpoints may need updating |
| Port changes | Update `OBO_PORT` env var and server-monitor config |
| server-monitor | Can switch OBO Decks card from postgres collector to HTTP collector at `http://127.0.0.1:9810/metrics` |

## Architecture
- Single-file FastAPI app (`obo_server.py`)
- asyncpg connection pool (2-10 connections)
- No auth required — read-only public API
- No ORM — raw SQL via asyncpg for simplicity
