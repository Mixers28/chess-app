#!/usr/bin/env python3
"""End-to-end integration test for the full Docker Compose stack.

Run against a live stack:
    python3 deploy/integration_test.py [base_url]

Default base_url: http://localhost:8000
Exit code 0 = all tests passed, non-zero = failure.
"""
from __future__ import annotations

import sys
import time
import uuid
import json
import urllib.request
import urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
AI_BASE = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8001"
USER = "integration-test-user"

_failures: list[str] = []


def _req(method: str, url: str, body: dict | None = None, expect: int = 200) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "X-Dev-User": USER},
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code

    payload = json.loads(raw) if raw else {}
    if status != expect:
        raise AssertionError(f"{method} {url} → {status} (expected {expect})\n{raw.decode()[:400]}")
    return payload  # type: ignore[return-value]


def check(name: str, fn):
    try:
        fn()
        print(f"  ✓  {name}")
    except Exception as exc:
        print(f"  ✗  {name}: {exc}")
        _failures.append(name)


# ---------------------------------------------------------------------------

def test_health():
    r = _req("GET", f"{BASE}/health")
    assert r.get("status") == "ok", r

def _ai_available() -> bool:
    try:
        urllib.request.urlopen(f"{AI_BASE}/health", timeout=2)
        return True
    except Exception:
        return False

def test_ai_health():
    if not _ai_available():
        print("    (chess-ai not reachable — skipped)", end="")
        return
    r = _req("GET", f"{AI_BASE}/health")
    assert r.get("status") == "ok", r

def test_ai_ready_reports_stockfish():
    if not _ai_available():
        print("    (chess-ai not reachable — skipped)", end="")
        return
    r = _req("GET", f"{AI_BASE}/ready")
    assert r.get("ready") is True, r
    assert "stockfish_available" in r, r

def test_api_ready():
    r = _req("GET", f"{BASE}/ready")
    assert r.get("ready") is True, r
    assert r["checks"].get("database") == "ok", r

def test_local_game_create_and_move():
    game = _req("POST", f"{BASE}/v1/games", {"mode": "local"}, expect=201)
    gid = game["game_id"]
    assert game["sequence"] == 0
    assert game["status"] == "active"

    # e2e4 (white)
    s1 = _req("POST", f"{BASE}/v1/games/{gid}/moves", {
        "command_id": str(uuid.uuid4()), "expected_sequence": 0, "move": "e2e4"
    })
    assert s1["sequence"] == 1
    assert s1["turn"] == "black"
    assert s1["last_move"]["uci"] == "e2e4"

    # e7e5 (black)
    s2 = _req("POST", f"{BASE}/v1/games/{gid}/moves", {
        "command_id": str(uuid.uuid4()), "expected_sequence": 1, "move": "e7e5"
    })
    assert s2["sequence"] == 2
    assert s2["turn"] == "white"

def test_idempotent_command_id():
    game = _req("POST", f"{BASE}/v1/games", {"mode": "local"}, expect=201)
    gid = game["game_id"]
    cmd = str(uuid.uuid4())

    r1 = _req("POST", f"{BASE}/v1/games/{gid}/moves", {
        "command_id": cmd, "expected_sequence": 0, "move": "d2d4"
    })
    # Submit same command_id again — should replay idempotently
    r2 = _req("POST", f"{BASE}/v1/games/{gid}/moves", {
        "command_id": cmd, "expected_sequence": 0, "move": "d2d4"
    })
    assert r1["sequence"] == r2["sequence"]

def test_stale_sequence_returns_recovery_snapshot():
    game = _req("POST", f"{BASE}/v1/games", {"mode": "local"}, expect=201)
    gid = game["game_id"]

    _req("POST", f"{BASE}/v1/games/{gid}/moves", {
        "command_id": str(uuid.uuid4()), "expected_sequence": 0, "move": "e2e4"
    })
    # Send with the old (stale) sequence — must 409 with a canonical recovery snapshot.
    raw_req = urllib.request.Request(
        f"{BASE}/v1/games/{gid}/moves",
        data=json.dumps({"command_id": str(uuid.uuid4()), "expected_sequence": 0, "move": "d2d4"}).encode(),
        headers={"Content-Type": "application/json", "X-Dev-User": USER},
        method="POST",
    )
    try:
        with urllib.request.urlopen(raw_req) as r:
            body = json.loads(r.read())
            raise AssertionError(f"Expected 409, got 200: {body}")
    except urllib.error.HTTPError as e:
        assert e.code == 409, f"Expected 409, got {e.code}"
        body = json.loads(e.read())
        # 409 body: {"error":"stale_sequence", "state": <GameState>, ...}
        recovery = body.get("state", body)
        assert recovery["sequence"] == 1, f"recovery snapshot: {body}"
        assert recovery["status"] == "active"

def test_illegal_move_returns_422():
    game = _req("POST", f"{BASE}/v1/games", {"mode": "local"}, expect=201)
    gid = game["game_id"]
    raw_req = urllib.request.Request(
        f"{BASE}/v1/games/{gid}/moves",
        data=json.dumps({"command_id": str(uuid.uuid4()), "expected_sequence": 0, "move": "e2e5"}).encode(),
        headers={"Content-Type": "application/json", "X-Dev-User": USER},
        method="POST",
    )
    try:
        with urllib.request.urlopen(raw_req) as r:
            raise AssertionError(f"Expected 422, got 200")
    except urllib.error.HTTPError as e:
        assert e.code == 422, f"Expected 422, got {e.code}"

def test_ai_game_auto_replies():
    game = _req("POST", f"{BASE}/v1/games",
                {"mode": "ai", "difficulty": "random", "color": "white"}, expect=201)
    gid = game["game_id"]
    assert game["mode"] == "ai"
    # AI is black; sequence is 0 before human's first move.
    assert game["sequence"] == 0

    # Human plays e2e4; AI should reply automatically.
    state = _req("POST", f"{BASE}/v1/games/{gid}/moves", {
        "command_id": str(uuid.uuid4()), "expected_sequence": 0, "move": "e2e4"
    })
    # sequence advanced by 2 (human + AI), back to white's turn
    assert state["sequence"] == 2, f"Expected seq 2, got {state['sequence']}"
    assert state["turn"] == "white"
    assert state["status"] == "active"

    moves = _req("GET", f"{BASE}/v1/games/{gid}/moves")
    assert len(moves) == 2, f"Expected 2 moves, got {len(moves)}"
    assert moves[0]["engine"] is None         # human move has no engine tag
    assert moves[1]["engine"] is not None     # AI move has engine tag

def test_ai_game_human_as_black():
    game = _req("POST", f"{BASE}/v1/games",
                {"mode": "ai", "difficulty": "random", "color": "black"}, expect=201)
    # AI (white) should have already moved during creation.
    assert game["sequence"] == 1, f"Expected seq 1 after AI first move, got {game['sequence']}"
    assert game["turn"] == "black"
    assert game["last_move"] is not None

def test_resign():
    game = _req("POST", f"{BASE}/v1/games", {"mode": "local"}, expect=201)
    gid = game["game_id"]
    state = _req("POST", f"{BASE}/v1/games/{gid}/resign", {
        "command_id": str(uuid.uuid4()), "expected_sequence": 0
    })
    assert state["status"] in ("finished", "resigned"), f"unexpected status: {state['status']}"
    assert state["result"] in ("0-1", "1-0"), f"unexpected result: {state['result']}"

def test_list_moves_after_game():
    game = _req("POST", f"{BASE}/v1/games", {"mode": "local"}, expect=201)
    gid = game["game_id"]
    for cmd, seq, move in [
        (str(uuid.uuid4()), 0, "e2e4"),
        (str(uuid.uuid4()), 1, "e7e5"),
        (str(uuid.uuid4()), 2, "g1f3"),
    ]:
        _req("POST", f"{BASE}/v1/games/{gid}/moves",
             {"command_id": cmd, "expected_sequence": seq, "move": move})
    moves = _req("GET", f"{BASE}/v1/games/{gid}/moves")
    assert len(moves) == 3
    assert moves[0]["san"] == "e4"
    assert moves[1]["san"] == "e5"
    assert moves[2]["san"] == "Nf3"


# ---------------------------------------------------------------------------
# Run

def wait_for_stack(timeout: int = 60) -> None:
    """Poll /health until the api is up (compose --wait may already handle this)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{BASE}/health", timeout=2)
            return
        except Exception:
            time.sleep(2)
    raise SystemExit(f"API at {BASE} did not become healthy within {timeout}s")


if __name__ == "__main__":
    print(f"Integration test: {BASE}  AI: {AI_BASE}")
    wait_for_stack()

    suite = [
        ("Health: api", test_health),
        ("Health: chess-ai", test_ai_health),
        ("Ready: chess-ai reports stockfish_available", test_ai_ready_reports_stockfish),
        ("Ready: api + postgres", test_api_ready),
        ("Local game: create + two moves", test_local_game_create_and_move),
        ("Idempotent command_id", test_idempotent_command_id),
        ("Stale sequence → 409 with recovery snapshot", test_stale_sequence_returns_recovery_snapshot),
        ("Illegal move → 422", test_illegal_move_returns_422),
        ("AI game: auto-replies after human move", test_ai_game_auto_replies),
        ("AI game: human-as-black → AI moves first", test_ai_game_human_as_black),
        ("Resign → finished + result", test_resign),
        ("List moves: SAN correct across multiple plies", test_list_moves_after_game),
    ]

    print(f"\nRunning {len(suite)} tests …\n")
    for name, fn in suite:
        check(name, fn)

    print(f"\n{'─' * 60}")
    if _failures:
        print(f"FAILED  {len(_failures)} / {len(suite)}: {', '.join(_failures)}")
        sys.exit(1)
    else:
        print(f"PASSED  {len(suite)} / {len(suite)}")
