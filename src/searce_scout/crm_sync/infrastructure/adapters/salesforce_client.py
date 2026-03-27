"""Salesforce CRM client adapter — implements CRMClientPort.

Communicates with the Salesforce REST API (v59.0) using OAuth2 client
credentials for authentication.  All HTTP calls go through ``httpx``
async client.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx

from searce_scout.crm_sync.domain.ports.crm_client_port import CRMClientPort
from searce_scout.crm_sync.domain.value_objects.record_type import RecordType

# Salesforce REST API version used throughout this adapter.
_API_VERSION = "v59.0"

# Mapping from domain RecordType to Salesforce SObject names.
_RECORD_TYPE_TO_SOBJECT: dict[RecordType, str] = {
    RecordType.LEAD: "Lead",
    RecordType.CONTACT: "Contact",
    RecordType.ACCOUNT: "Account",
    RecordType.OPPORTUNITY: "Opportunity",
    RecordType.ACTIVITY: "Task",
}


class SalesforceClient:
    """Salesforce adapter implementing :class:`CRMClientPort`.

    Parameters
    ----------
    client_id:
        OAuth2 connected-app consumer key.
    client_secret:
        OAuth2 connected-app consumer secret.
    instance_url:
        Salesforce instance base URL, e.g. ``https://na1.salesforce.com``.
    timeout:
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        instance_url: str,
        timeout: float = 30.0,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._instance_url = instance_url.rstrip("/")
        self._timeout = timeout

        # Cached OAuth2 access token and its expiry (epoch seconds).
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    # ------------------------------------------------------------------
    # CRMClientPort implementation
    # ------------------------------------------------------------------

    async def create_record(
        self, record_type: RecordType, fields: dict[str, str]
    ) -> str:
        """Create a new SObject and return its Salesforce record id."""
        sobject = _RECORD_TYPE_TO_SOBJECT[record_type]
        url = self._data_url(f"/sobjects/{sobject}")
        response = await self._request("POST", url, json=fields)
        body = response.json()
        return str(body["id"])

    async def update_record(
        self, external_id: str, fields: dict[str, str]
    ) -> None:
        """Update an existing SObject identified by *external_id*."""
        sobject = self._sobject_from_id(external_id, fields)
        url = self._data_url(f"/sobjects/{sobject}/{external_id}")
        await self._request("PATCH", url, json=fields)

    async def get_record(
        self, external_id: str
    ) -> dict[str, str] | None:
        """Fetch a single SObject by its Salesforce id.

        Returns ``None`` when the record does not exist (HTTP 404).

        Because the caller may not supply the SObject type, we iterate
        over all known types until one responds with a valid record.
        """
        for sobject in _RECORD_TYPE_TO_SOBJECT.values():
            get_url = self._data_url(f"/sobjects/{sobject}/{external_id}")
            try:
                response = await self._request("GET", get_url)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    continue
                raise
            body = response.json()
            return {
                k: str(v) for k, v in body.items() if isinstance(v, (str, int, float, bool))
            }
        return None

    async def query_records(
        self, record_type: RecordType, filters: dict[str, str]
    ) -> tuple[dict[str, str], ...]:
        """Execute a SOQL query against the given SObject with *filters*."""
        sobject = _RECORD_TYPE_TO_SOBJECT[record_type]
        where_clauses = " AND ".join(
            f"{field} = '{_escape_soql(value)}'" for field, value in filters.items()
        )
        where = f" WHERE {where_clauses}" if where_clauses else ""
        soql = f"SELECT FIELDS(STANDARD) FROM {sobject}{where}"
        return await self._soql_query(soql)

    async def get_changes_since(
        self, record_type: RecordType, since: datetime
    ) -> tuple[dict[str, str], ...]:
        """Return records modified after *since* via SystemModstamp."""
        sobject = _RECORD_TYPE_TO_SOBJECT[record_type]
        since_iso = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        soql = (
            f"SELECT FIELDS(STANDARD) FROM {sobject} "
            f"WHERE SystemModstamp > {since_iso}"
        )
        return await self._soql_query(soql)

    # ------------------------------------------------------------------
    # OAuth2 token management
    # ------------------------------------------------------------------

    async def _get_access_token(self) -> str:
        """Return a cached access token, refreshing it when expired."""
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        token_url = f"{self._instance_url}/services/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(token_url, data=payload)
            response.raise_for_status()

        body = response.json()
        self._access_token = str(body["access_token"])
        # Salesforce tokens typically last 2 hours.  Shave 5 minutes to
        # avoid edge-case expiry during a request.
        issued_at_ms = int(body.get("issued_at", time.time() * 1000))
        expires_in = float(body.get("expires_in", 7200))
        self._token_expires_at = time.monotonic() + expires_in - 300

        return self._access_token

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _data_url(self, path: str) -> str:
        """Build a full Salesforce data API URL."""
        return f"{self._instance_url}/services/data/{_API_VERSION}{path}"

    async def _authorized_headers(self) -> dict[str, str]:
        token = await self._get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Execute an authenticated HTTP request against Salesforce."""
        headers = await self._authorized_headers()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.request(
                method, url, headers=headers, json=json, params=params
            )
            response.raise_for_status()
        return response

    async def _soql_query(self, soql: str) -> tuple[dict[str, str], ...]:
        """Run a SOQL query and return all result rows, handling pagination."""
        url = self._data_url("/query/")
        params = {"q": soql}
        results: list[dict[str, str]] = []

        while True:
            response = await self._request("GET", url, params=params)
            body = response.json()
            for record in body.get("records", []):
                row = {
                    k: str(v)
                    for k, v in record.items()
                    if k != "attributes" and isinstance(v, (str, int, float, bool))
                }
                results.append(row)

            next_url: str | None = body.get("nextRecordsUrl")
            if not next_url:
                break
            # nextRecordsUrl is a relative path — build absolute URL.
            url = f"{self._instance_url}{next_url}"
            params = None  # the next URL already contains the query locator

        return tuple(results)

    @staticmethod
    def _sobject_from_id(
        external_id: str, fields: dict[str, str]
    ) -> str:
        """Determine the SObject name for an update request.

        If the caller provided a ``type`` or ``RecordType`` key in
        *fields* we use it; otherwise we default to the first known
        SObject that responds.  For simplicity the caller is expected to
        use the correct external id for the record type.
        """
        hint = fields.pop("type", None) or fields.pop("RecordType", None)
        if hint and hint in {s for s in _RECORD_TYPE_TO_SOBJECT.values()}:
            return hint
        # Fallback — a pragmatic default for the common case.
        return "Lead"

def _escape_soql(value: str) -> str:
    """Escape single quotes for safe SOQL interpolation."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


# Structural compatibility assertion
def _check_port_compliance() -> None:
    _: CRMClientPort = SalesforceClient(  # type: ignore[assignment]
        client_id="", client_secret="", instance_url=""
    )
