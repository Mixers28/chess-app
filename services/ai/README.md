# chess-ai

Stateless chess AI inference service — the backend behind the game service's AI
boundary (build-plan Phase 3). Given a FEN, a difficulty, and optional constraints, it
returns **one legal move**. It holds no game state: `services/api` stays authoritative
and re-validates every move with python-chess.

## Difficulties

| Difficulty  | Strategy | Strength knob (`level`) |
|-------------|----------|-------------------------|
| `random`    | Uniform random legal move | — |
| `heuristic` | Greedy 1-ply material + check bias | — |
| `search`    | Negamax + alpha-beta to fixed depth | search depth (also `constraints.max_depth`) |
| `stockfish` | UCI engine via python-chess (only if a binary is configured) | UCI Skill Level 0–20 |

`random`/`heuristic`/`search` are pure Python and always available. `stockfish` appears
only when `AI_STOCKFISH_PATH` points at a real binary (the Docker image bundles one);
otherwise requesting it returns `503 engine_unavailable`.

## API

```
POST /v1/move          {fen, difficulty, level?, constraints?, correlation_id?} -> move
GET  /v1/difficulties  -> {difficulties, stockfish_available}
GET  /health           -> liveness
GET  /ready            -> {ready, stockfish_available}
```

`POST /v1/move` returns `{uci, san, difficulty, engine, evaluation, depth, think_ms,
correlation_id}`. Errors: `422 invalid_position`, `409 game_already_over`,
`400 unknown_difficulty`, `503 engine_unavailable`.

## Quickstart

```bash
make install   # from repo root, or: python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
make test      # baseline-bot + API tests (no engine needed)

# Run with Stockfish locally (optional):
export AI_STOCKFISH_PATH=$(which stockfish)
.venv/bin/uvicorn app.main:app --port 8001
```

## Extending with a custom model

A custom engine (e.g. **chess-sim**) plugs in by implementing the `Bot` interface
(`app/bots/base.py`) and registering under a new difficulty in `app/registry.py`.
Nothing else — the service contract and the game-service caller stay unchanged. This is
the intended integration point once that model is strong enough and exposed statelessly.
