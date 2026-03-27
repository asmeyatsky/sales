"""HubSpot CRM client adapter — implements CRMClientPort.

Communicates with the HubSpot CRM API v3 using a private app API key
for authentication.  All HTTP calls go through ``httpx`` async client.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from searce_scout.crm_sync.domain.ports.crm_client_port import CRMClientPort
from searce_scout.crm_sync.domain.value_objects.record_type import RecordType

_HUBSPOT_BASE_URL = "https://api.hubapi.com"

# Mapping from domain RecordType to HubSpot object type identifiers.
_RECORD_TYPE_TO_OBJECT: dict[RecordType, str] = {
    RecordType.LEAD: "contacts",
    RecordType.CONTACT: "contacts",
    RecordType.ACCOUNT: "companies",
    RecordType.OPPORTUNITY: "deals",
    RecordType.ACTIVITY: "tasks",
}


class HubSpotClient:
    """HubSpot adapter implementing :class:`CRMClientPort`.

    Parameters
    ----------
    api_key:
        HubSpot private app access token.
    timeout:
        HTTP request timeout in seconds.
    """

    def __init__(self, *, api_key: str, timeout: float = 30.0) -> None:
        self._api_key = api_key
        self._timeout = timeout

    # ------------------------------------------------------------------
    # CRMClientPort implementation
    # ------------------------------------------------------------------

    async def create_record(
        self, record_type: RecordType, fields: dict[str, str]
    ) -> str:
        """Create a new CRM object and return its HubSpot id."""
        object_type = _RECORD_TYPE_TO_OBJECT[record_type]
        url = f"{_HUBSPOT_BASE_URL}/crm/v3/objects/{object_type}"
        payload = {"properties": fields}
        response = await self._request("POST", url, json=payload)
        body = response.json()
        return str(body["id"])

    async def update_record(
        self, external_id: str, fields: dict[str, str]
    ) -> None:
        """Update an existing HubSpot object identified by *external_id*."""
        object_type = self._resolve_object_type(external_id, fields)
        url = f"{_HUBSPOT_BASE_URL}/crm/v3/objects/{object_type}/{external_id}"
        payload = {"properties": fields}
        await self._request("PATCH", url, json=payload)

    async def get_record(
        self, external_id: str
    ) -> dict[str, str] | None:
        """Fetch a single CRM object by its HubSpot id.

        Returns ``None`` when the record does not exist (HTTP 404).
        """
        for object_type in dict.fromkeys(_RECORD_TYPE_TO_OBJECT.values()):
            url = f"{_HUBSPOT_BASE_URL}/crm/v3/objects/{object_type}/{external_id}"
            try:
                response = await self._request("GET", url)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    continue
                raise
            body = response.json()
            properties: dict[str, str] = {
                k: str(v)
                for k, v in body.get("properties", {}).items()
                if v is not None
            }
            properties["id"] = str(body["id"])
            return properties
        return None

    async def query_records(
        self, record_type: RecordType, filters: dict[str, str]
    ) -> tuple[dict[str, str], ...]:
        """Search for CRM objects matching the given *filters*."""
        object_type = _RECORD_TYPE_TO_OBJECT[record_type]
        filter_groups = [
            {
                "filters": [
                    {
                        "propertyName": prop,
                        "operator": "EQ",
                        "value": value,
                    }
                    for prop, value in filters.items()
                ]
            }
        ]
        return await self._search(object_type, filter_groups)

    async def get_changes_since(
        self, record_type: RecordType, since: datetime
    ) -> tuple[dict[str, str], ...]:
        """Return records modified after *since* using the search API."""
        object_type = _RECORD_TYPE_TO_OBJECT[record_type]
        # HubSpot expects epoch-millisecond timestamps for date filters.
        since_ms = str(
            int(since.astimezone(timezone.utc).timestamp() * 1000)
        )
        filter_groups = [
            {
                "filters": [
                    {
                        "propertyName": "hs_lastmodifieddate",
                        "operator": "GTE",
                        "value": since_ms,
                    }
                ]
            }
        ]
        return await self._search(object_type, filter_groups)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json: dict | None = None,  # type: ignore[type-arg]
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Execute an authenticated HTTP request against HubSpot."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.request(
                method,
                url,
                headers=self._auth_headers(),
                json=json,
                params=params,
            )
            response.raise_for_status()
        return response

    async def _search(
        self,
        object_type: str,
        filter_groups: list[dict],  # type: ignore[type-arg]
    ) -> tuple[dict[str, str], ...]:
        """Run a HubSpot search with cursor-based pagination."""
        url = f"{_HUBSPOT_BASE_URL}/crm/v3/objects/{object_type}/search"
        results: list[dict[str, str]] = []
        after: str | None = None

        while True:
            payload: dict = {  # type: ignore[type-arg]
                "filterGroups": filter_groups,
                "limit": 100,
            }
            if after is not None:
                payload["after"] = after

            response = await self._request("POST", url, json=payload)
            body = response.json()

            for item in body.get("results", []):
                row: dict[str, str] = {
                    k: str(v)
                    for k, v in item.get("properties", {}).items()
                    if v is not None
                }
                row["id"] = str(item["id"])
                results.append(row)

            paging = body.get("paging")
            if paging and paging.get("next"):
                after = paging["next"].get("after")
                if after is None:
                    break
            else:
                break

        return tuple(results)

    @staticmethod
    def _resolve_object_type(
        external_id: str, fields: dict[str, str]
    ) -> str:
        """Best-effort object type resolution for updates.

        Callers are expected to supply the correct *external_id* for the
        HubSpot object.  If a ``hs_object_type`` hint is present in
        *fields* we use it; otherwise we fall back to ``contacts``.
        """
        hint = fields.pop("hs_object_type", None)
        if hint and hint in {v for v in _RECORD_TYPE_TO_OBJECT.values()}:
            return hint
        return "contacts"


# Structural compatibility assertion
def _check_port_compliance() -> None:
    _: CRMClientPort = HubSpotClient(api_key="")  # type: ignore[assignment]
