"""Infrastructure adapter for LinkedIn Sales Navigator profile search.

Implements LinkedInPort using httpx to call the LinkedIn Sales Navigator
REST API.  Handles pagination, rate-limiting (exponential back-off), and
maps raw JSON responses to domain LinkedInProfile value objects.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from searce_scout.shared_kernel.value_objects import PersonName, URL
from searce_scout.stakeholder_discovery.domain.ports.linkedin_port import (
    LinkedInPort,
    LinkedInProfile,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.linkedin.com/v2"
_SEARCH_ENDPOINT = "/salesNavigator/search/people"
_MAX_PAGE_SIZE = 25
_MAX_RETRIES = 4
_INITIAL_BACKOFF_SECONDS = 1.0


class LinkedInSalesNavAdapter:
    """LinkedIn Sales Navigator adapter implementing :class:`LinkedInPort`.

    Parameters
    ----------
    api_key:
        LinkedIn application client-id / API key.
    api_secret:
        LinkedIn application client-secret.
    base_url:
        Override the LinkedIn API base URL (useful for testing).
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
        self._access_token: str | None = None

    # -- LinkedInPort interface ---------------------------------------------

    async def search_decision_makers(
        self, company_name: str, titles: tuple[str, ...]
    ) -> tuple[LinkedInProfile, ...]:
        """Search LinkedIn Sales Navigator for decision-makers at *company_name*
        whose title matches one of *titles*.

        Returns a tuple of :class:`LinkedInProfile` domain objects.
        Paginates through the full result set automatically.
        """
        async with self._build_client() as client:
            access_token = await self._ensure_access_token(client)
            headers = {"Authorization": f"Bearer {access_token}"}

            profiles: list[LinkedInProfile] = []
            start = 0

            while True:
                params = self._build_search_params(company_name, titles, start)
                data = await self._request_with_backoff(
                    client, "GET", _SEARCH_ENDPOINT, headers=headers, params=params
                )

                elements: list[dict[str, Any]] = data.get("elements", [])
                if not elements:
                    break

                for element in elements:
                    profile = self._map_to_profile(element)
                    if profile is not None:
                        profiles.append(profile)

                total = data.get("paging", {}).get("total", 0)
                start += _MAX_PAGE_SIZE
                if start >= total:
                    break

            return tuple(profiles)

    # -- Internal helpers ---------------------------------------------------

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )

    async def _ensure_access_token(self, client: httpx.AsyncClient) -> str:
        """Return a cached access token or fetch a fresh one via client-credentials."""
        if self._access_token is not None:
            return self._access_token

        response = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "client_credentials",
                "client_id": self._api_key,
                "client_secret": self._api_secret,
            },
        )
        response.raise_for_status()
        self._access_token = response.json()["access_token"]
        return self._access_token  # type: ignore[return-value]

    @staticmethod
    def _build_search_params(
        company_name: str, titles: tuple[str, ...], start: int
    ) -> dict[str, Any]:
        return {
            "q": "search",
            "query": company_name,
            "titleFilter": ",".join(titles),
            "start": start,
            "count": _MAX_PAGE_SIZE,
        }

    async def _request_with_backoff(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        *,
        headers: dict[str, str],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute an HTTP request with exponential back-off on rate-limit / transient errors."""
        backoff = _INITIAL_BACKOFF_SECONDS

        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await client.request(
                    method, path, headers=headers, params=params
                )

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

        # Should be unreachable, but satisfy the type-checker.
        raise httpx.HTTPError("Max retries exceeded for LinkedIn API request")

    @staticmethod
    def _map_to_profile(element: dict[str, Any]) -> LinkedInProfile | None:
        """Map a single Sales Navigator search result to a domain LinkedInProfile."""
        try:
            first_name: str = element.get("firstName", "")
            last_name: str = element.get("lastName", "")
            title: str = element.get("title", "")
            profile_url: str = element.get("linkedInUrl", "") or element.get(
                "publicProfileUrl", ""
            )
            company: str = (
                element.get("currentCompany", {}).get("name", "")
                or element.get("company", "")
            )

            if not first_name or not last_name or not profile_url:
                return None

            return LinkedInProfile(
                name=PersonName(first_name=first_name, last_name=last_name),
                title=title,
                linkedin_url=URL(value=profile_url),
                company=company,
            )
        except Exception:
            logger.debug("Skipping unmappable LinkedIn element: %s", element, exc_info=True)
            return None


# Ensure structural compatibility with the port Protocol at import time.
_check: type[LinkedInPort] = LinkedInSalesNavAdapter  # type: ignore[assignment]
