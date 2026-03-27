"""
FieldMapperService — pure domain service.

Translates field tuples between the local domain model representation
and the CRM-specific field names using FieldMapping definitions.
"""

from __future__ import annotations

from searce_scout.crm_sync.domain.entities.field_mapping import FieldMapping
from searce_scout.crm_sync.domain.value_objects.sync_direction import SyncDirection


class FieldMapperService:
    """Bidirectional field translation between local and CRM schemas."""

    def map_to_crm(
        self,
        fields: tuple[tuple[str, str], ...],
        mappings: tuple[FieldMapping, ...],
    ) -> dict[str, str]:
        """Convert local field tuples to a CRM field dict.

        Only mappings with direction PUSH or BIDIRECTIONAL are applied.
        Fields without a matching mapping are silently skipped.
        """
        local_dict = dict(fields)
        result: dict[str, str] = {}

        for mapping in mappings:
            if mapping.direction not in (
                SyncDirection.PUSH,
                SyncDirection.BIDIRECTIONAL,
            ):
                continue
            if mapping.local_field in local_dict:
                result[mapping.crm_field] = local_dict[mapping.local_field]

        return result

    def map_from_crm(
        self,
        crm_data: dict[str, str],
        mappings: tuple[FieldMapping, ...],
    ) -> tuple[tuple[str, str], ...]:
        """Convert a CRM field dict to local field tuples.

        Only mappings with direction PULL or BIDIRECTIONAL are applied.
        CRM fields without a matching mapping are silently skipped.
        """
        result: list[tuple[str, str]] = []

        for mapping in mappings:
            if mapping.direction not in (
                SyncDirection.PULL,
                SyncDirection.BIDIRECTIONAL,
            ):
                continue
            if mapping.crm_field in crm_data:
                result.append((mapping.local_field, crm_data[mapping.crm_field]))

        return tuple(result)
