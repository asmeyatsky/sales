"""
CRM Sync domain events.

Events raised when records are synced to or from an external CRM,
or when a field-level conflict is detected.
"""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class RecordSyncedEvent(DomainEvent):
    provider: str = ""
    record_type: str = ""
    external_id: str = ""


@dataclass(frozen=True)
class SyncConflictDetectedEvent(DomainEvent):
    field_name: str = ""
    local_value: str = ""
    remote_value: str = ""
