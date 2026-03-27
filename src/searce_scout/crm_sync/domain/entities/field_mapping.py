"""
FieldMapping entity.

Describes how a single local field maps to a CRM field for a
given provider and record type, including sync direction and an
optional transform expression.
"""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.crm_sync.domain.value_objects.crm_provider import CRMProvider
from searce_scout.crm_sync.domain.value_objects.record_type import RecordType
from searce_scout.crm_sync.domain.value_objects.sync_direction import SyncDirection


@dataclass(frozen=True)
class FieldMapping:
    mapping_id: str
    provider: CRMProvider
    record_type: RecordType
    local_field: str
    crm_field: str
    direction: SyncDirection
    transform: str | None = None
