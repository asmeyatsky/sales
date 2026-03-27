"""
GetSyncStatusQuery and handler.

Retrieves the current sync status for a local record.
"""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.crm_sync.domain.ports.sync_log_repository_port import (
    SyncLogRepositoryPort,
)

from searce_scout.crm_sync.application.dtos.crm_dtos import CRMRecordDTO


@dataclass(frozen=True)
class GetSyncStatusQuery:
    local_id: str


class GetSyncStatusHandler:
    """Returns the CRMRecordDTO for the given local_id, or None if not found."""

    def __init__(self, sync_log_repository: SyncLogRepositoryPort) -> None:
        self._sync_log_repository = sync_log_repository

    async def execute(self, query: GetSyncStatusQuery) -> CRMRecordDTO | None:
        records = await self._sync_log_repository.find_by_local_id(query.local_id)
        if not records:
            return None
        # Return the most recently synced record (last in the tuple)
        return CRMRecordDTO.from_domain(records[-1])
