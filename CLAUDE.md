# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

The repo holds the two authoritative planning documents, two backend services, and the iOS app. **Phase 0/1/3 game backend** (`services/api/`), **Phase 3 AI service** (`services/ai/`), and the **Phase 2 iOS client** (`apps/ios/`) are all implemented. Online multiplayer (Phase 4) is not yet built. When extending, follow the build-plan phase sequence (see below) and each service's README.

```
services/api/                          # FastAPI modular monolith (Phase 0/1 + Phase 3 orchestration) — IMPLEMENTED
services/ai/                            # Stateless AI inference (Phase 3) — IMPLEMENTED
apps/ios/                              # SwiftUI iOS client (Phase 2) — IMPLEMENTED
  project.yml                          # xcodegen spec — regenerate with `xcodegen generate` from apps/ios/
  Packages/ChessCore/                  # SPM library (models, API client, state reducer, move generator)
  Sources/ChessApp/                    # SwiftUI app shell (features: Game, GameList, NewGame)
docs/                                  # Generated .docx deliverables (do not hand-edit)
  Chess_App_Product_Requirements.docx
  Chess_App_Phased_Build_Plan.docx
.document-build/
  create_planning_docs.py              # Source of truth for both docs; build via python-docx
  vendor/                              # Vendored deps (python-docx, lxml, PIL, pdf2image)
  render-plan/, render-prd/            # Empty render output dirs
```

## Working with the planning docs

The `.docx` files are **build artifacts**. Never edit them directly — edit `create_planning_docs.py` and regenerate. Content lives in `build_prd()` and `build_phase_plan()`; everything above those is reusable Word-styling helpers (fonts, tables, callouts, code blocks).

Regenerate both docs (deps are vendored, so set `PYTHONPATH`):

```bash
PYTHONPATH=.document-build/vendor python3 .document-build/create_planning_docs.py
```

This rewrites both files in `docs/` and prints their paths. `TODAY` is hardcoded (`date(2026, 6, 13)`); update it in the script rather than relying on the system clock.

## Backend (`services/api/`)

FastAPI modular monolith targeting Python 3.13 (3.11+). All commands run from `services/api/`:

```bash
make install      # python3 -m venv .venv + pip install -e '.[dev]'   (needs python ≥3.11)
make test         # pytest — SQLite in-memory, NO Postgres/Redis needed
make lint         # ruff check
make typecheck    # mypy app
make migrate      # alembic upgrade head against $CHESS_DATABASE_URL
make run          # uvicorn (needs a reachable Postgres)
```

Run a single test: `.venv/bin/pytest tests/test_games_api.py::test_full_game_to_checkmate`.
Settings are env-driven with the `CHESS_` prefix (see `.env.example`); `app/core/config.py` is the typed source of truth.

Implementation notes that span files:
- **Tests run on SQLite** (in-memory, via aiosqlite) while production uses Postgres/asyncpg. Keep SQL portable. Per-game serialization uses `SELECT ... FOR UPDATE` (`service._lock_game`) which Postgres honors and SQLite ignores; correctness then rests on the `(game_id, command_id)` and `(game_id, ply)` unique constraints, so never drop those.
- **`app/games/chess_engine.py` is the only place python-chess is touched.** All legality/outcome/FEN/SAN/PGN logic lives there; the service and API stay rules-agnostic.
- **`app/auth/identity.py` is the identity seam** (`X-Dev-User` header → `CHESS_DEV_USER_ID`). It is the single function Phase 4 replaces with Sign in with Apple — don't leak auth assumptions elsewhere.
- **Domain errors → HTTP** mapping is centralized in `app/api/errors.py` (404 / 422 illegal / 409 stale|finished / 403 auth). Raise domain errors from `app/games/errors.py`; never raise `HTTPException` from the service layer.
- Migrations are an explicit release step, never a startup hook. CI (`.github/workflows/api.yml`) verifies `alembic upgrade head` then `downgrade base` against a clean Postgres.

### AI-game orchestration (Phase 3, `app/ai/`)

For `mode: "ai"` games the api calls `services/ai` for the opponent's move. Load-bearing rules:
- **The AI move is its own committed transition, after the human's.** The route commits the human move, then `AIOrchestrator.maybe_play` runs in a **separate session/transaction**, so an AI failure can never roll back the human's move. Don't merge these into one transaction.
- **Idempotent + non-corrupting:** the AI move is applied via `GameService.submit_move` with a deterministic `command_id` (`ai:<game>:<sequence>`), so a retry/duplicate can't double-move. It reuses the same turn/sequence/legality validation as human moves — the AI is not trusted.
- **Failure handling:** `AIClient` has timeout + retries + a circuit breaker. On failure the orchestrator falls back to a local random legal move (`CHESS_AI_FALLBACK_TO_RANDOM`, default on); with fallback off it leaves the game at the AI's turn (human move intact) for retry via `POST /v1/games/{id}/ai-move`.
- The orchestrator **always exists** even with no `CHESS_AI_BASE_URL` (it uses the fallback), so ai-mode is playable in dev with no AI service running. The AI side is a reserved synthetic user (`app/ai/constants.AI_USER_ID`); per-move telemetry (`engine`, `think_ms`) lives on `moves`, opponent config on `ai_games`.

## AI service (`services/ai/`)

Separate deployable, also FastAPI. Stateless: `POST /v1/move {fen, difficulty, level?, constraints?} → {uci, san, evaluation, ...}`. Own venv/commands (`make install && make test` from `services/ai/`, no DB or engine needed for tests). Conventions that matter:
- **Difficulty → bot** mapping lives in `app/registry.py`. Bots implement the `Bot` ABC (`app/bots/base.py`, `async choose(board, constraints, level) -> ChosenMove`). `random`/`heuristic`/`search` are always available; `stockfish` only registers when `AI_STOCKFISH_PATH` resolves to a binary (bundled in the Docker image; absent → `503`).
- **A custom model (chess-sim) plugs in here** — implement `Bot`, register a difficulty. The service contract and the api caller don't change. This is the intended chess-sim integration point, not a direct HTTP dependency.
- The service is **defense-in-depth, not the authority**: it re-checks legality before returning, but the api re-validates every move with python-chess regardless.
- The single UCI engine process is owned by `app/engine/manager.py` (serialized behind a lock, blocking calls in a worker thread) and degrades gracefully when no binary is present.

## Intended product architecture (from the planning docs)

These constraints come from the PRD and build plan and should govern any future implementation work. The single most important rule across the whole product is **server authority**.

- **Clients send commands, not state.** Every move command carries a client-generated `command_id` and the `expected_sequence` the client believes it is extending. The server validates, commits, then emits a new monotonic `sequence`. This makes commands idempotent and replay-safe; stale/duplicate/out-of-turn commands are rejected without corrupting state.
- **Stack:** SwiftUI iOS app ↔ (HTTPS + WebSocket) ↔ FastAPI **modular monolith** + separate worker + separate AI service. `python-chess` runs in-process in the API and is the sole authority for legality, outcomes, FEN, SAN, and PGN.
- **Durability split:** PostgreSQL (via SQLAlchemy 2 + Alembic) owns all durable state — users, games, moves, ratings. Redis is for coordination only (queues, presence, locks, pub/sub, transient state) and **must always be reconstructable or disposable** — never the source of truth.
- **The app never talks to a model/engine directly.** The game service calls the AI service with FEN + difficulty + correlation metadata, and re-validates every returned move with python-chess before applying it.
- **Baseline bots (random → heuristic → shallow search) ship before any custom ML model.** A stable AI-service contract protects the schedule if the ML model isn't ready. No automatic training on raw games; no automatic model promotion.
- Public API is versioned (`/v1`) with an explicit WebSocket message schema from the first client.

### Target repository structure (when implementation begins)

The build plan prescribes this layout — follow it rather than inventing a new one:

```
apps/ios/                # SwiftUI app + Xcode project (Swift 6, async/await)
services/api/            # FastAPI modular monolith
  app/{api,auth,games,matchmaking,ai,db,core}/
  tests/
services/worker/         # background analysis jobs
services/ai/             # inference service + baseline bots
deploy/                  # compose.yaml + coolify/ runbooks
docs/, .github/workflows/
```

Boundaries (auth / games / matchmaking / ai) stay clear in code, but they are **one deployable** — do not split into microservices without a measured need. Deployment target is Coolify + Docker Compose.

## Build sequencing

Work proceeds in vertical slices (Phases 0–8 in the build plan); each phase must leave the product runnable, tested, and deployable, and each has a written exit gate. Phase 0 = repo/CI/containers/observability baseline; Phase 1 = authoritative chess core (no Redis needed); later phases add the iOS board, AI, friend multiplayer, matchmaking, review, and the ML pipeline. The immediate "first scaffold" target is Phase 0 plus the smallest Phase 1 slice: create-game, get-game, and submit-move backed by python-chess and PostgreSQL. Consult `docs/Chess_App_Phased_Build_Plan.docx` (regenerate to read, or read the `build_phase_plan()` source) for the per-phase deliverables and exit gates before starting a phase.
