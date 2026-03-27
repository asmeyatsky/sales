"""
ResolveConflictCommand and handler.

Resolves a field-level sync conflict for a CRMRecord using a chosen
resolution strategy, then pushes the resolved data back to the CRM.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import CRMRecordId

from searce_scout.crm_sync.domain.ports.crm_client_port import CRMClientPort
from searce_scout.crm_sync.domain.ports.sync_log_repository_port import (
    SyncLogRepositoryPort,
)
from searce_scout.crm_sync.domain.services.conflict_resolution import (
    ConflictResolutionService,
    ResolutionStrategy,
)

from searce_scout.crm_sync.application.dtos.crm_dtos import CRMRecordDTO


@dataclass(frozen=True)
class ResolveConflictCommand:
    record_id: str
    strategy: str


class ResolveConflictHandler:
    """Resolves a sync conflict and pushes the resolved data to the CRM."""

    def __init__(
        self,
        conflict_resolution_service: ConflictResolutionService,
        crm_client: CRMClientPort,
        sync_log_repository: SyncLogRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._conflict_resolution_service = conflict_resolution_service
        self._crm_client = crm_client
        self._sync_log_repository = sync_log_repository
        self._event_bus = event_bus

    async def execute(self, cmd: ResolveConflictCommand) -> CRMRecordDTO:
        """Load the conflicted record, resolve, push to CRM, and mark synced."""
        record_id = CRMRecordId(cmd.record_id)
        strategy = ResolutionStrategy(cmd.strategy)

        record = await self._sync_log_repository.get_by_id(record_id)
        if record is None:
            raise ValueError(f"CRM record not found: {cmd.record_id}")

        # Fetch current remote state for conflict resolution
        remote_fields: dict[str, str] = {}
        if record.external_id:
            remote_data = await self._crm_client.get_record(record.external_id)
            if remote_data is not None:
                remote_fields = remote_data

        # Resolve using the domain service
        resolved_fields = self._conflict_resolution_service.resolve(
            local_fields=record.fields,
            remote_fields=remote_fields,
            strategy=strategy,
        )

        # Update the record with resolved fields
        record = record.update_fields(resolved_fields)

        # Push resolved data to CRM
        if record.external_id:
            resolved_dict = dict(resolved_fields)
            await self._crm_client.update_record(
                external_id=record.external_id,
                fields=resolved_dict,
            )

        # Mark as synced
        now = datetime.now(UTC)
        record = record.mark_synced(
            external_id=record.external_id or "",
            synced_at=now,
        )

        await self._sync_log_repository.save(record)
        await self._event_bus.publish(record.domain_events)

        return CRMRecordDTO.from_domain(record)
