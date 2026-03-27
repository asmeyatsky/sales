"""
CRMClientPort — output port for communicating with an external CRM system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from searce_scout.crm_sync.domain.value_objects.record_type import RecordType


class CRMClientPort(Protocol):
    async def create_record(
        self, record_type: RecordType, fields: dict[str, str]
    ) -> str: ...

    async def update_record(
        self, external_id: str, fields: dict[str, str]
    ) -> None: ...

    async def get_record(
        self, external_id: str
    ) -> dict[str, str] | None: ...

    async def query_records(
        self, record_type: RecordType, filters: dict[str, str]
    ) -> tuple[dict[str, str], ...]: ...

    async def get_changes_since(
        self, record_type: RecordType, since: datetime
    ) -> tuple[dict[str, str], ...]: ...
