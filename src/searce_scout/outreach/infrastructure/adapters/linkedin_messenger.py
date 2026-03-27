"""Infrastructure adapter for LinkedIn messaging operations.

Implements LinkedInMessengerPort using httpx to call the LinkedIn
messaging and invitations API.  Handles rate-limiting with exponential
back-off and maps results to the shared SendResult value object.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from searce_scout.shared_kernel.value_objects import URL
from searce_scout.outreach.domain.ports.email_sender_port import SendResult
from searce_scout.outreach.domain.ports.linkedin_messenger_port import (
    LinkedInMessengerPort,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.linkedin.com/v2"
_INVITATION_ENDPOINT = "/invitations"
_MESSAGING_ENDPOINT = "/messages"
_MAX_RETRIES = 4
_INITIAL_BACKOFF_SECONDS = 1.0


class LinkedInMessenger:
    """LinkedIn messaging adapter implementing :class:`LinkedInMessengerPort`.

    Parameters
    ----------
    access_token:
        A valid LinkedIn OAuth2 access token with messaging permissions.
    base_url:
        Override the LinkedIn API base URL (useful for testing).
    timeout:
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        access_token: str,
        *,
        base_url: str = _BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self._access_token = access_token
        self._base_url = base_url
        self._timeout = timeout

    # -- LinkedInMessengerPort interface ------------------------------------

    async def send_connection_request(
        self, profile_url: URL, note: str
    ) -> SendResult:
        """Send a LinkedIn connection request with a personalized note.

        Returns a :class:`SendResult` indicating success or failure.
        """
        async with self._build_client() as client:
            member_urn = self._extract_member_urn(profile_url)
            payload: dict[str, Any] = {
                "invitee": {
                    "com.linkedin.voyager.growth.invitation.InviteeProfile": {
                        "profileId": member_urn,
                    }
                },
                "message": {"text": note[:300]},  # LinkedIn caps notes at ~300 chars
            }

            try:
                data = await self._post_with_backoff(
                    client, _INVITATION_ENDPOINT, json_body=payload
                )
                invitation_id = data.get("id", data.get("value", ""))
                logger.info(
                    "LinkedIn connection request sent. invitation_id=%s, profile=%s",
                    invitation_id,
                    profile_url.value,
                )
                return SendResult(success=True, message_id=str(invitation_id))

            except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
                error_detail = str(exc)
                logger.error(
                    "Failed to send LinkedIn connection request to %s: %s",
                    profile_url.value,
                    error_detail,
                )
                return SendResult(success=False, error=error_detail)

    async def send_message(self, profile_url: URL, body: str) -> SendResult:
        """Send a LinkedIn direct message to a connected profile.

        Returns a :class:`SendResult` indicating success or failure.
        """
        async with self._build_client() as client:
            member_urn = self._extract_member_urn(profile_url)
            payload: dict[str, Any] = {
                "recipients": [member_urn],
                "body": body,
            }

            try:
                data = await self._post_with_backoff(
                    client, _MESSAGING_ENDPOINT, json_body=payload
                )
                message_id = data.get("id", data.get("value", ""))
                logger.info(
                    "LinkedIn message sent. message_id=%s, profile=%s",
                    message_id,
                    profile_url.value,
                )
                return SendResult(success=True, message_id=str(message_id))

            except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
                error_detail = str(exc)
                logger.error(
                    "Failed to send LinkedIn message to %s: %s",
                    profile_url.value,
                    error_detail,
                )
                return SendResult(success=False, error=error_detail)

    # -- Internal helpers ---------------------------------------------------

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )

    @staticmethod
    def _extract_member_urn(profile_url: URL) -> str:
        """Derive a LinkedIn member URN from a profile URL.

        If the URL already contains a URN-style ID it is returned as-is.
        Otherwise a best-effort extraction of the vanity name / member-id
        from the URL path is performed.
        """
        path = profile_url.value.rstrip("/")
        # e.g. https://www.linkedin.com/in/johndoe -> johndoe
        parts = path.split("/")
        member_slug = parts[-1] if parts else path
        return f"urn:li:member:{member_slug}"

    async def _post_with_backoff(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        json_body: dict[str, Any],
    ) -> dict[str, Any]:
        """POST with exponential back-off on rate-limit / transient errors."""
        backoff = _INITIAL_BACKOFF_SECONDS

        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await client.post(path, json=json_body)

                if response.status_code == 429:
                    retry_after = float(
                        response.headers.get("Retry-After", str(backoff))
                    )
                    logger.warning(
                        "LinkedIn rate-limited (429). Retrying in %.1fs (attempt %d/%d).",
                        retry_after,
                        attempt + 1,
                        _MAX_RETRIES,
                    )
                    await asyncio.sleep(retry_after)
                    backoff *= 2
                    continue

                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]

            except httpx.TransportError as exc:
                if attempt == _MAX_RETRIES:
                    raise
                logger.warning(
                    "Transient HTTP error: %s. Retrying in %.1fs (attempt %d/%d).",
                    exc,
                    backoff,
                    attempt + 1,
                    _MAX_RETRIES,
                )
                await asyncio.sleep(backoff)
                backoff *= 2

        raise httpx.HTTPError("Max retries exceeded for LinkedIn messaging API request")


# Structural compatibility check with the port Protocol.
_check: type[LinkedInMessengerPort] = LinkedInMessenger  # type: ignore[assignment]
