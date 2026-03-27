"""
SyncLogRepositoryPort — persistence port for CRMRecord aggregates.
"""

from __future__ import annotations

from typing import Protocol

from searce_scout.shared_kernel.types import CRMRecordId

from searce_scout.crm_sync.domain.entities.crm_record import CRMRecord


class SyncLogRepositoryPort(Protocol):
    async def save(self, record: CRMRecord) -> None: ...

    async def get_by_id(
        self, record_id: CRMRecordId
    ) -> CRMRecord | None: ...

    async def find_by_local_id(
        self, local_id: str
    ) -> tuple[CRMRecord, ...]: ...

    async def find_pending(self) -> tuple[CRMRecord, ...]: ...
