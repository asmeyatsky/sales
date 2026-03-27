"""
Audit logging middleware for SOC 2 compliance.

Logs every API request with timestamp, method, path, status code,
hashed API key, client IP, and response duration.  Sensitive credentials
are never written to the log -- only a truncated SHA-256 hash of the key.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

audit_logger = logging.getLogger("searce_scout.audit")


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Emit a structured audit log entry for every HTTP request."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.monotonic()
        api_key = request.headers.get("X-API-Key", "")
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:12] if api_key else "none"

        response: Response = await call_next(request)

        duration_ms = (time.monotonic() - start) * 1000
        audit_logger.info(
            "api_request",
            extra={
                "timestamp": datetime.now(UTC).isoformat(),
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "api_key_hash": key_hash,
                "client_ip": request.client.host if request.client else "unknown",
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response
