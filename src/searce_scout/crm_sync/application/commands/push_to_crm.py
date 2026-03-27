"""
PushToCRMCommand and handler.

Maps local fields to CRM-specific fields and creates or updates the record
in the external CRM system, then logs the result.
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
from searce_scout.crm_sync.domain.value_objects.sync_status import SyncStatus

from searce_scout.crm_sync.application.dtos.crm_dtos import CRMRecordDTO


@dataclass(frozen=True)
class PushToCRMCommand:
    local_id: str
    record_type: str
    provider: str
    fields: dict[str, str]


class PushToCRMHandler:
    """Pushes a local record to the external CRM system."""

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

    async def execute(self, cmd: PushToCRMCommand) -> CRMRecordDTO:
        """Map local fields, push to CRM, persist sync log, and publish events."""
        provider = CRMProvider(cmd.provider)
        record_type = RecordType(cmd.record_type)
        local_fields = tuple(cmd.fields.items())

        # Map local field names to CRM field names
        crm_fields = self._field_mapper_service.map_to_crm(
            fields=local_fields,
            mappings=self._field_mappings,
        )

        # Look up existing record to determine create vs update
        existing_records = await self._sync_log_repository.find_by_local_id(
            cmd.local_id
        )

        existing_record: CRMRecord | None = None
        for rec in existing_records:
            if rec.provider == provider and rec.record_type == record_type:
                existing_record = rec
                break

        now = datetime.now(UTC)

        if existing_record and existing_record.external_id:
            # Update existing CRM record
            await self._crm_client.update_record(
                external_id=existing_record.external_id,
                fields=crm_fields,
            )
            record = existing_record.update_fields(local_fields)
            record = record.mark_synced(
                external_id=existing_record.external_id,
                synced_at=now,
            )
        else:
            # Create new CRM record
            external_id = await self._crm_client.create_record(
                record_type=record_type,
                fields=crm_fields,
            )
            record_id = (
                existing_record.record_id
                if existing_record
                else CRMRecordId(str(uuid4()))
            )
            record = CRMRecord(
                record_id=record_id,
                provider=provider,
                record_type=record_type,
                local_id=cmd.local_id,
                fields=local_fields,
                sync_status=SyncStatus.PENDING,
            )
            record = record.mark_synced(external_id=external_id, synced_at=now)

        await self._sync_log_repository.save(record)
        await self._event_bus.publish(record.domain_events)

        return CRMRecordDTO.from_domain(record)
