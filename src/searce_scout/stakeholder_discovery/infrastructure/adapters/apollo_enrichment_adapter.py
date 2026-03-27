"""Infrastructure adapter for Apollo.io contact enrichment.

Implements ContactEnrichmentPort using httpx to call the Apollo People
Enrichment API.  Maps Apollo JSON responses to domain ContactInfo entities
and ValidationStatus value objects.
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

_BASE_URL = "https://api.apollo.io/v1"
_PEOPLE_MATCH_ENDPOINT = "/people/match"
_EMAIL_VERIFY_ENDPOINT = "/people/email_verify"
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 1.0

# Mapping from Apollo email status strings to domain ValidationStatus.
_APOLLO_EMAIL_STATUS_MAP: dict[str, ValidationStatus] = {
    "valid": ValidationStatus.VALID,
    "invalid": ValidationStatus.INVALID,
    "catch_all": ValidationStatus.CATCH_ALL,
    "unknown": ValidationStatus.UNKNOWN,
    "unverified": ValidationStatus.UNVALIDATED,
}


class ApolloEnrichmentAdapter:
    """Apollo.io enrichment adapter implementing :class:`ContactEnrichmentPort`.

    Parameters
    ----------
    api_key:
        Apollo.io API key.
    base_url:
        Override the Apollo API base URL (useful for testing).
    timeout:
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout

    # -- ContactEnrichmentPort interface ------------------------------------

    async def enrich_contact(
        self, person_name: PersonName, company_name: str
    ) -> ContactInfo:
        """Look up a person in Apollo and return enriched contact details."""
        async with self._build_client() as client:
            payload: dict[str, Any] = {
                "first_name": person_name.first_name,
                "last_name": person_name.last_name,
                "organization_name": company_name,
            }
            data = await self._post_with_backoff(
                client, _PEOPLE_MATCH_ENDPOINT, json_body=payload
            )

            person: dict[str, Any] = data.get("person", {})
            return self._map_to_contact_info(person)

    async def validate_email(self, email: EmailAddress) -> ValidationStatus:
        """Verify an email address via Apollo's email-verification endpoint."""
        async with self._build_client() as client:
            payload: dict[str, Any] = {"email": email.value}
            data = await self._post_with_backoff(
                client, _EMAIL_VERIFY_ENDPOINT, json_body=payload
            )

            status_str: str = data.get("status", "unknown").lower()
            return _APOLLO_EMAIL_STATUS_MAP.get(status_str, ValidationStatus.UNKNOWN)

    # -- Internal helpers ---------------------------------------------------

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={"X-Api-Key": self._api_key, "Content-Type": "application/json"},
        )

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
                        "Apollo rate-limited (429). Retrying in %.1fs (attempt %d/%d).",
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

        raise httpx.HTTPError("Max retries exceeded for Apollo API request")

    @staticmethod
    def _map_to_contact_info(person: dict[str, Any]) -> ContactInfo:
        """Map an Apollo person record to a domain :class:`ContactInfo`."""
        raw_email: str | None = person.get("email")
        raw_phone: str | None = person.get("phone_number") or person.get(
            "sanitized_phone"
        )
        raw_email_status: str = person.get("email_status", "unknown").lower()
        raw_phone_status: str = person.get("phone_status", "unknown").lower()

        email: EmailAddress | None = None
        if raw_email:
            try:
                email = EmailAddress(value=raw_email)
            except Exception:
                logger.debug("Apollo returned invalid email: %s", raw_email)

        phone: PhoneNumber | None = None
        if raw_phone:
            try:
                phone = PhoneNumber(value=raw_phone)
            except Exception:
                logger.debug("Apollo returned invalid phone: %s", raw_phone)

        email_status = _APOLLO_EMAIL_STATUS_MAP.get(
            raw_email_status, ValidationStatus.UNKNOWN
        )
        phone_status = _APOLLO_EMAIL_STATUS_MAP.get(
            raw_phone_status, ValidationStatus.UNKNOWN
        )

        return ContactInfo(
            email=email,
            phone=phone,
            email_status=email_status,
            phone_status=phone_status,
            source="apollo",
            validated_at=datetime.now(UTC),
        )


# Structural compatibility check with the port Protocol.
_check: type[ContactEnrichmentPort] = ApolloEnrichmentAdapter  # type: ignore[assignment]
