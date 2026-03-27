"""
Simple API key authentication middleware.

Validates the X-API-Key header against the configured api_key setting.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from searce_scout.scout_orchestrator.config.settings import ScoutSettings


async def api_key_auth(request: Request, settings: ScoutSettings) -> None:
    """Validate the X-API-Key header.

    Raises:
        HTTPException: 503 if no API key is configured on the server.
        HTTPException: 401 if the key is missing or does not match.
    """
    if not settings.api_key:
        raise HTTPException(status_code=503, detail="API key not configured")
    api_key = request.headers.get("X-API-Key")
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
