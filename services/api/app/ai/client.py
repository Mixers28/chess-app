from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.core.logging import get_logger

logger = get_logger("app.ai.client")


class AIError(Exception):
    """Base class for AI client failures."""


class AIUnavailable(AIError):
    """Transient failure (timeout, connection error, 5xx, or open breaker). Retryable."""


class AIRejected(AIError):
    """The AI service rejected the request (4xx) — e.g. terminal position. Not retryable."""


@dataclass(frozen=True)
class AIMoveResult:
    uci: str
    engine: str
    evaluation: float | None
    think_ms: int


class CircuitBreaker:
    """Trips open after N consecutive failures and fails fast during a cooldown.

    Protects the game request path from hammering a sick AI service and from paying the
    full timeout on every call while it is down. Process-local; that is sufficient here
    because a tripped breaker simply routes to the fallback sooner.
    """

    def __init__(self, threshold: int, cooldown_s: float) -> None:
        self._threshold = threshold
        self._cooldown_s = cooldown_s
        self._failures = 0
        self._open_until = 0.0

    @property
    def is_open(self) -> bool:
        if self._open_until == 0.0:
            return False
        if time.monotonic() >= self._open_until:
            # Half-open: allow the next call through to probe recovery.
            self._open_until = 0.0
            self._failures = 0
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._open_until = 0.0

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._open_until = time.monotonic() + self._cooldown_s
            logger.warning(
                "ai_breaker_open",
                extra={"extra": {"cooldown_s": self._cooldown_s, "failures": self._failures}},
            )


class AIClient:
    """Async client for the AI service's ``POST /v1/move`` endpoint."""

    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        retries: int = 2,
        breaker: CircuitBreaker | None = None,
    ) -> None:
        self._http = http
        self._retries = retries
        self._breaker = breaker or CircuitBreaker(threshold=5, cooldown_s=10.0)

    async def request_move(
        self,
        *,
        fen: str,
        difficulty: str,
        level: int | None,
        correlation_id: str | None,
    ) -> AIMoveResult:
        if self._breaker.is_open:
            raise AIUnavailable("circuit breaker open")

        payload = {
            "fen": fen,
            "difficulty": difficulty,
            "level": level,
            "correlation_id": correlation_id,
        }

        last_exc: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                resp = await self._http.post("/v1/move", json=payload)
            except httpx.HTTPError as exc:
                last_exc = exc
                logger.warning("ai_request_error", extra={"extra": {"attempt": attempt}})
                continue  # retry transient transport errors

            if resp.status_code == 200:
                self._breaker.record_success()
                return self._parse(resp.json())
            if 400 <= resp.status_code < 500:
                # A client-side rejection (e.g. terminal position) won't change on retry.
                self._breaker.record_success()  # the service is healthy, our request wasn't valid
                raise AIRejected(f"ai service returned {resp.status_code}: {resp.text}")
            last_exc = AIUnavailable(f"ai service returned {resp.status_code}")

        self._breaker.record_failure()
        raise AIUnavailable(str(last_exc) if last_exc else "ai service unavailable")

    @staticmethod
    def _parse(body: dict) -> AIMoveResult:
        return AIMoveResult(
            uci=body["uci"],
            engine=body.get("engine", "unknown"),
            evaluation=body.get("evaluation"),
            think_ms=int(body.get("think_ms", 0)),
        )
