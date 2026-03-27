"""
ListConflictsQuery and handler.

Returns all CRM records that are currently in CONFLICT status,
requiring manual or automated resolution.
"""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.crm_sync.domain.ports.sync_log_repository_port import (
    SyncLogRepositoryPort,
)
from searce_scout.crm_sync.domain.value_objects.sync_status import SyncStatus

from searce_scout.crm_sync.application.dtos.crm_dtos import CRMRecordDTO


@dataclass(frozen=True)
class ListConflictsQuery:
    pass


class ListConflictsHandler:
    """Returns all CRMRecordDTOs that have CONFLICT sync status."""

    def __init__(self, sync_log_repository: SyncLogRepositoryPort) -> None:
        self._sync_log_repository = sync_log_repository

    async def execute(self, query: ListConflictsQuery) -> list[CRMRecordDTO]:
        # Use find_pending to get records, then filter for CONFLICT status.
        # The repository port does not expose a find_by_status method,
        # so we retrieve pending records and filter client-side.
        # In a production system, a dedicated query would be preferred.
        pending = await self._sync_log_repository.find_pending()
        conflicts = [r for r in pending if r.sync_status == SyncStatus.CONFLICT]
        return [CRMRecordDTO.from_domain(r) for r in conflicts]
