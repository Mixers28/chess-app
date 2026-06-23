from __future__ import annotations


async def test_health_is_liveness_only(client) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_ready_checks_database(client) -> None:
    resp = await client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True
    assert body["checks"]["database"] == "ok"
    # Redis is unconfigured in tests, so it must not be probed.
    assert "redis" not in body["checks"]
