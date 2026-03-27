"""Infrastructure adapter for ZoomInfo contact enrichment.

Implements ContactEnrichmentPort using httpx to call the ZoomInfo Enrich
API.  Serves as an alternative enrichment source alongside the Apollo
adapter, presenting the identical domain interface.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from searce_scout.shared_kernel.value_objects import EmailAddress, PersonName, PhoneNumber
from searce_scout.stakeholder_discovery.domain.entities.contact_info import ContactInfo
from searce_scout.stakeholder_discovery.domain.ports.contact_enrichment_port import (
    ContactEnrichmentPort,
)
from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    ValidationStatus,
)

logger = logging.getLogger(__name__)

_AUTH_URL = "https://api.zoominfo.com/authenticate"
_BASE_URL = "https://api.zoominfo.com"
_ENRICH_ENDPOINT = "/enrich/contact"
_EMAIL_VALIDATE_ENDPOINT = "/lookup/email-verification"
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 1.0

_ZOOMINFO_STATUS_MAP: dict[str, ValidationStatus] = {
    "valid": ValidationStatus.VALID,
    "invalid": ValidationStatus.INVALID,
    "accept_all": ValidationStatus.CATCH_ALL,
    "catch_all": ValidationStatus.CATCH_ALL,
    "unknown": ValidationStatus.UNKNOWN,
    "unverified": ValidationStatus.UNVALIDATED,
}


class ZoomInfoEnrichmentAdapter:
    """ZoomInfo enrichment adapter implementing :class:`ContactEnrichmentPort`.

    Parameters
    ----------
    api_key:
        ZoomInfo API key (used alongside *api_secret* for JWT auth).
    api_secret:
        ZoomInfo API secret.
    base_url:
        Override the ZoomInfo API base URL (useful for testing).
    timeout:
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        *,
        base_url: str = _BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url
        self._timeout = timeout
        self._jwt_token: str | None = None

    # -- ContactEnrichmentPort interface ------------------------------------

    async def enrich_contact(
        self, person_name: PersonName, company_name: str
    ) -> ContactInfo:
        """Enrich a contact using ZoomInfo's person-enrichment endpoint."""
        async with self._build_client() as client:
            token = await self._ensure_jwt(client)
            headers = {"Authorization": f"Bearer {token}"}

            payload: dict[str, Any] = {
                "matchPersonInput": [
                    {
                        "firstName": person_name.first_name,
                        "lastName": person_name.last_name,
                        "companyName": company_name,
                    }
                ],
                "outputFields": [
                    "email",
                    "phone",
                    "emailStatus",
                    "phoneStatus",
                ],
            }

            data = await self._post_with_backoff(
                client, _ENRICH_ENDPOINT, headers=headers, json_body=payload
            )

            results: list[dict[str, Any]] = data.get("data", [])
            person = results[0] if results else {}
            return self._map_to_contact_info(person)

    async def validate_email(self, email: EmailAddress) -> ValidationStatus:
        """Validate an email via ZoomInfo's email-verification endpoint."""
        async with self._build_client() as client:
            token = await self._ensure_jwt(client)
            headers = {"Authorization": f"Bearer {token}"}

            payload: dict[str, Any] = {"emailAddress": email.value}
            data = await self._post_with_backoff(
                client, _EMAIL_VALIDATE_ENDPOINT, headers=headers, json_body=payload
            )

            status_str: str = data.get("status", "unknown").lower()
            return _ZOOMINFO_STATUS_MAP.get(status_str, ValidationStatus.UNKNOWN)

    # -- Internal helpers ---------------------------------------------------

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={"Content-Type": "application/json"},
        )

    async def _ensure_jwt(self, client: httpx.AsyncClient) -> str:
        """Authenticate with ZoomInfo and cache the JWT token."""
        if self._jwt_token is not None:
            return self._jwt_token

        response = await client.post(
            _AUTH_URL,
            json={"username": self._api_key, "password": self._api_secret},
        )
        response.raise_for_status()
        self._jwt_token = response.json()["jwt"]
        return self._jwt_token  # type: ignore[return-value]

    async def _post_with_backoff(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any],
    ) -> dict[str, Any]:
        """POST with exponential back-off on rate-limit / transient errors."""
        backoff = _INITIAL_BACKOFF_SECONDS

        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await client.post(
                    path, headers=headers, json=json_body
                )

                if response.status_code == 429:
                    retry_after = float(
                        response.headers.get("Retry-After", str(backoff))
                    )
                    logger.warning(
                        "ZoomInfo rate-limited (429). Retrying in %.1fs (attempt %d/%d).",
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

        raise httpx.HTTPError("Max retries exceeded for ZoomInfo API request")

    @staticmethod
    def _map_to_contact_info(person: dict[str, Any]) -> ContactInfo:
        """Map a ZoomInfo person record to a domain :class:`ContactInfo`."""
        raw_email: str | None = person.get("email")
        raw_phone: str | None = person.get("phone") or person.get("directPhone")
        raw_email_status: str = person.get("emailStatus", "unknown").lower()
        raw_phone_status: str = person.get("phoneStatus", "unknown").lower()

        email: EmailAddress | None = None
        if raw_email:
            try:
                email = EmailAddress(value=raw_email)
            except Exception:
                logger.debug("ZoomInfo returned invalid email: %s", raw_email)

        phone: PhoneNumber | None = None
        if raw_phone:
            try:
                phone = PhoneNumber(value=raw_phone)
            except Exception:
                logger.debug("ZoomInfo returned invalid phone: %s", raw_phone)

        email_status = _ZOOMINFO_STATUS_MAP.get(
            raw_email_status, ValidationStatus.UNKNOWN
        )
        phone_status = _ZOOMINFO_STATUS_MAP.get(
            raw_phone_status, ValidationStatus.UNKNOWN
        )

        return ContactInfo(
            email=email,
            phone=phone,
            email_status=email_status,
            phone_status=phone_status,
            source="zoominfo",
            validated_at=datetime.now(UTC),
        )


# Structural compatibility check with the port Protocol.
_check: type[ContactEnrichmentPort] = ZoomInfoEnrichmentAdapter  # type: ignore[assignment]
