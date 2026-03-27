"""
CRMRecord aggregate root.

Represents a record that is synchronised between Searce Scout
and an external CRM (Salesforce / HubSpot). Tracks sync status,
field values, and emits domain events on state transitions.
All mutations return new frozen instances.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from searce_scout.shared_kernel.domain_event import DomainEvent
from searce_scout.shared_kernel.types import CRMRecordId

from searce_scout.crm_sync.domain.events.crm_events import (
    RecordSyncedEvent,
    SyncConflictDetectedEvent,
)
from searce_scout.crm_sync.domain.value_objects.crm_provider import CRMProvider
from searce_scout.crm_sync.domain.value_objects.record_type import RecordType
from searce_scout.crm_sync.domain.value_objects.sync_status import SyncStatus


@dataclass(frozen=True)
class CRMRecord:
    record_id: CRMRecordId
    provider: CRMProvider
    record_type: RecordType
    local_id: str
    fields: tuple[tuple[str, str], ...]
    sync_status: SyncStatus = SyncStatus.PENDING
    external_id: str | None = None
    last_synced_at: datetime | None = None
    domain_events: tuple[DomainEvent, ...] = ()

    def mark_synced(self, external_id: str, synced_at: datetime) -> CRMRecord:
        """Transition to SYNCED, recording the external CRM id and timestamp."""
        event = RecordSyncedEvent(
            aggregate_id=self.record_id,
            provider=self.provider.value,
            record_type=self.record_type.value,
            external_id=external_id,
        )
        return replace(
            self,
            external_id=external_id,
            sync_status=SyncStatus.SYNCED,
            last_synced_at=synced_at,
            domain_events=self.domain_events + (event,),
        )

    def mark_conflict(self, reason: str) -> CRMRecord:
        """Transition to CONFLICT and emit a SyncConflictDetectedEvent.

        *reason* is recorded as the ``field_name`` of the event so the
        consumer can identify which field triggered the conflict.
        """
        event = SyncConflictDetectedEvent(
            aggregate_id=self.record_id,
            field_name=reason,
            local_value="",
            remote_value="",
        )
        return replace(
            self,
            sync_status=SyncStatus.CONFLICT,
            domain_events=self.domain_events + (event,),
        )

    def update_fields(
        self, new_fields: tuple[tuple[str, str], ...]
    ) -> CRMRecord:
        """Replace the field set and reset status to PENDING."""
        return replace(
            self,
            fields=new_fields,
            sync_status=SyncStatus.PENDING,
        )
