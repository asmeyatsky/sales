"""
CRM Sync DTOs.

Pydantic models for transferring CRM synchronisation data across the
application boundary. Decouples the domain model from API / transport concerns.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from searce_scout.crm_sync.domain.entities.crm_record import CRMRecord


class SyncConflictDTO(BaseModel):
    record_id: str
    field_name: str
    local_value: str
    remote_value: str


class CRMRecordDTO(BaseModel):
    record_id: str
    provider: str
    record_type: str
    external_id: str | None
    local_id: str
    fields: dict[str, str]
    sync_status: str
    last_synced_at: datetime | None

    @classmethod
    def from_domain(cls, record: CRMRecord) -> CRMRecordDTO:
        return cls(
            record_id=record.record_id,
            provider=record.provider.value,
            record_type=record.record_type.value,
            external_id=record.external_id,
            local_id=record.local_id,
            fields=dict(record.fields),
            sync_status=record.sync_status.value,
            last_synced_at=record.last_synced_at,
        )
