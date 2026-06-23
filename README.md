# Chess App

A native iOS chess trainer: authoritative online play plus an adaptive AI coach. See
`docs/` for the Product Requirements and Phased Build Plan (generated from
`.document-build/create_planning_docs.py`).

## Status

| Area                | State |
|---------------------|-------|
| Planning docs       | ✅ `docs/*.docx` |
| Backend Phase 0/1/3 | ✅ `services/api` — authoritative chess core + AI orchestration |
| AI service Phase 3  | ✅ `services/ai` — baseline bots + optional Stockfish |
| iOS client Phase 2  | ✅ `apps/ios` — SwiftUI board, typed API client, game state |
| Online multiplayer  | ⏳ Phase 4 (not started) |

## Running locally

There are two ways to start the backend. Pick one based on what you have available.

---

### Option A — SQLite (no Docker, fastest start)

Needs Python 3.11+. A one-time venv setup, then two commands.

```bash
# 1. Install deps (run once)
make install

# 2. Apply migrations to a local SQLite file
CHESS_DATABASE_URL=sqlite+aiosqlite:///./dev.db make migrate

# 3. Start the API
CHESS_DATABASE_URL=sqlite+aiosqlite:///./dev.db make run
```

The API is now at **http://localhost:8000**. Health check:

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

> The AI service (`services/ai`) is optional for this path. Without it, VS-AI games
> still work — the orchestrator falls back to a local random legal move.

---

### Option B — Docker Compose (full stack, closest to production)

Needs Docker Desktop (or Colima). Starts Postgres, the API, and the AI service
(including Stockfish) in one command.

```bash
make up
# or directly:
docker compose -f deploy/compose.yaml up --build
```

Wait for all three services to report healthy, then:

```bash
curl http://localhost:8000/ready
# → {"ready":true,"checks":{"database":"ok"}}
```

To stop and remove volumes: `make down`

---

### Running the iOS app against the local backend

Open the Xcode project:

```
apps/ios/ChessApp.xcodeproj
```

The app reads two environment variables set in the shared Xcode scheme
(`ChessApp.xcscheme`):

| Variable | Default | Purpose |
|---|---|---|
| `CHESS_API_URL` | `http://localhost:8000` | Backend base URL |
| `CHESS_DEV_USER_ID` | `dev-user-ios` | Dev identity (replaces Sign in with Apple in Phase 4) |

These are already configured in the scheme. Run the `ChessApp` target on the
**iPhone 17 Pro** simulator (or any iOS 17+ device on the same network).

> If running on a **physical device**, change `CHESS_API_URL` to your Mac's local
> network IP, e.g. `http://192.168.1.x:8000`, and make sure the API is bound to
> `0.0.0.0` (it is by default via `make run`).

---

## Repository layout

```
apps/ios/                # SwiftUI iOS client (Phase 2)
  project.yml            # xcodegen spec — run `xcodegen generate` from apps/ios/
  Packages/ChessCore/    # SPM library: models, API client, state reducer, move gen
  Sources/ChessApp/      # App shell: Game, GameList, NewGame features
services/api/            # FastAPI game backend (Phase 0/1/3)
services/ai/             # Stateless AI inference service (Phase 3)
deploy/                  # compose.yaml + integration test + Coolify notes
docs/                    # Generated planning documents (do not hand-edit)
.document-build/         # Source for planning docs (python-docx)
```

## Backend commands (from repo root)

```bash
make install      # create venv + install api deps
make run          # start API (set CHESS_DATABASE_URL first)
make migrate      # alembic upgrade head (set CHESS_DATABASE_URL first)
make test         # pytest — SQLite in-memory, no services needed
make lint         # ruff
make typecheck    # mypy
make up           # docker compose up --build (full stack)
make down         # docker compose down -v
```

See `services/api/README.md` and `services/ai/README.md` for per-service details.
