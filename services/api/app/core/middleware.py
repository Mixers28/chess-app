from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, request_id_var

logger = get_logger("app.request")
REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign/propagate a request id, bind it for logging, and log each request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            logger.exception(
                "request_failed",
                extra={"extra": {"method": request.method, "path": request.url.path}},
            )
            raise
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            request_id_var.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request_completed",
            extra={
                "extra": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": elapsed_ms,
                }
            },
        )
        return response
