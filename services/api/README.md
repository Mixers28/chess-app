# chess-api

Authoritative chess game backend — FastAPI modular monolith. Phase 0 (foundation)
+ the Phase 1 vertical slice (authoritative chess core) from the build plan.

## Layout

```
app/
  core/      settings, JSON logging, request-id middleware
  db/        async SQLAlchemy engine/session, models (users, games, moves)
  auth/      development identity seam (replaced by Sign in with Apple in Phase 4)
  games/     chess_engine (python-chess adapter), command service, schemas, errors
  api/       health/readiness, error→HTTP mapping, v1 routes
migrations/  Alembic env + initial schema
tests/       engine unit tests + API/service integration tests (SQLite in-memory)
```

## Quickstart

```bash
make install          # venv + editable install with dev extras
make test             # pytest (SQLite in-memory, no services needed)
make lint typecheck   # ruff + mypy
```

### Run with SQLite (no Postgres needed — quickest for dev)

```bash
export CHESS_DATABASE_URL=sqlite+aiosqlite:///./dev.db
make migrate          # creates dev.db and applies all migrations
make run              # starts uvicorn on :8000 with --reload
```

The AI orchestrator works without the AI service running — it falls back to a local
random legal move, so VS-AI games are playable with no extra setup.

### Run with Postgres (via Docker Compose)

```bash
docker compose -f ../../deploy/compose.yaml up postgres -d
export CHESS_DATABASE_URL=postgresql+asyncpg://chess:chess@localhost:5432/chess
make migrate && make run
```

### Run the full stack (api + ai service + postgres)

From the repo root:

```bash
make up    # builds images and starts all three services with health-checked ordering
```

## The authoritative protocol (Phase 1)

Clients send **commands**, not state. A move command carries a client-generated
`command_id` (idempotency key) and the `expected_sequence` it believes it is
extending. The server validates against canonical state and emits a new `sequence`
only after the transition commits.

| Command                          | Method | Path                          |
|----------------------------------|--------|-------------------------------|
| Create game                      | POST   | `/v1/games`                   |
| Get canonical state              | GET    | `/v1/games/{id}`              |
| Submit move (UCI)                | POST   | `/v1/games/{id}/moves`        |
| Resign                           | POST   | `/v1/games/{id}/resign`       |
| List moves                       | GET    | `/v1/games/{id}/moves`        |
| Drive AI turn (retry)            | POST   | `/v1/games/{id}/ai-move`      |

Rejections are deterministic: `404` not found, `422` illegal move, `409`
stale/finished (stale returns the canonical recovery snapshot), `403` authorization.
Duplicate `command_id`s replay idempotently. python-chess (`games/chess_engine.py`)
is the sole authority for legality, outcomes, FEN, SAN, and PGN.

> Identity is a development seam in Phase 1: the `X-Dev-User` header (or
> `CHESS_DEV_USER_ID`) names the actor. `local` games assign both colors to the
> creator so a full game is playable before online multiplayer (Phase 4).

## AI games (Phase 3)

Create with `{"mode": "ai", "difficulty": "search", "level": null, "color": "white"}`.
The api calls `services/ai` (`CHESS_AI_BASE_URL`) for the opponent's move **after** the
human move commits, in a separate transaction, and re-validates it with python-chess
before applying — so a `POST /moves` in an ai game returns the state *after* the AI has
replied. If the human picks `black`, the AI moves first during create.

Resilience (`app/ai/`): timeout + retries + circuit breaker; on failure it falls back to
a local random legal move (`CHESS_AI_FALLBACK_TO_RANDOM`), or — with fallback off —
leaves the game at the AI's turn for retry via `POST /v1/games/{id}/ai-move`. The AI
move is idempotent (deterministic `command_id`), so it can never double-move. Without
`CHESS_AI_BASE_URL` set, ai games still work via the fallback. Per-move telemetry
(`engine`, `think_ms`) is on `moves`; opponent config on `ai_games`.
