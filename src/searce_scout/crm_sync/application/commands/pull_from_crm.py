"""
PullFromCRMCommand and handler.

Fetches changes from the external CRM since a given timestamp, maps
CRM fields back to local fields, and persists updated CRMRecord aggregates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import CRMRecordId

from searce_scout.crm_sync.domain.entities.crm_record import CRMRecord
from searce_scout.crm_sync.domain.entities.field_mapping import FieldMapping
from searce_scout.crm_sync.domain.ports.crm_client_port import CRMClientPort
from searce_scout.crm_sync.domain.ports.sync_log_repository_port import (
    SyncLogRepositoryPort,
)
from searce_scout.crm_sync.domain.services.field_mapper import FieldMapperService
from searce_scout.crm_sync.domain.value_objects.crm_provider import CRMProvider
from searce_scout.crm_sync.domain.value_objects.record_type import RecordType

from searce_scout.crm_sync.application.dtos.crm_dtos import CRMRecordDTO


@dataclass(frozen=True)
class PullFromCRMCommand:
    provider: str
    record_type: str
    since: str  # ISO datetime


class PullFromCRMHandler:
    """Pulls changes from the external CRM and updates local records."""

    def __init__(
        self,
        crm_client: CRMClientPort,
        field_mapper_service: FieldMapperService,
        sync_log_repository: SyncLogRepositoryPort,
        event_bus: EventBusPort,
        field_mappings: tuple[FieldMapping, ...],
    ) -> None:
        self._crm_client = crm_client
        self._field_mapper_service = field_mapper_service
        self._sync_log_repository = sync_log_repository
        self._event_bus = event_bus
        self._field_mappings = field_mappings

    async def execute(self, cmd: PullFromCRMCommand) -> list[CRMRecordDTO]:
        """Fetch remote changes, map fields, create/update local records."""
        provider = CRMProvider(cmd.provider)
        record_type = RecordType(cmd.record_type)
        since = datetime.fromisoformat(cmd.since)

        # Fetch changed records from the CRM
        remote_records = await self._crm_client.get_changes_since(
            record_type=record_type,
            since=since,
        )

        now = datetime.now(UTC)
        results: list[CRMRecordDTO] = []
        all_events: list = []

        for crm_data in remote_records:
            # Map CRM fields to local fields
            local_fields = self._field_mapper_service.map_from_crm(
                crm_data=crm_data,
                mappings=self._field_mappings,
            )

            # The external_id is expected in the CRM data under "Id" or "id"
            external_id = crm_data.get("Id") or crm_data.get("id", "")

            # Try to find an existing local record for this external id
            # We search by local_id which may match, or create a new record
            record = CRMRecord(
                record_id=CRMRecordId(str(uuid4())),
                provider=provider,
                record_type=record_type,
                local_id=external_id,  # use external_id as local_id for pulled records
                fields=local_fields,
            )
            record = record.mark_synced(external_id=external_id, synced_at=now)

            await self._sync_log_repository.save(record)
            all_events.extend(record.domain_events)
            results.append(CRMRecordDTO.from_domain(record))

        if all_events:
            await self._event_bus.publish(tuple(all_events))

        return results
