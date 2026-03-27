"""
ConflictResolutionService — pure domain service.

Resolves field-level conflicts between the local record and the
remote CRM record according to a chosen strategy. No I/O.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class ResolutionStrategy(Enum):
    LAST_WRITE_WINS = "LAST_WRITE_WINS"
    LOCAL_PRIORITY = "LOCAL_PRIORITY"
    REMOTE_PRIORITY = "REMOTE_PRIORITY"
    MANUAL_FLAG = "MANUAL_FLAG"


class ConflictResolutionService:
    """Merge local and remote field sets using a given strategy."""

    def resolve(
        self,
        local_fields: tuple[tuple[str, str], ...],
        remote_fields: dict[str, str],
        strategy: ResolutionStrategy,
    ) -> tuple[tuple[str, str], ...]:
        """Return the merged field set based on *strategy*.

        - LAST_WRITE_WINS / REMOTE_PRIORITY: remote values override local.
        - LOCAL_PRIORITY: local values are kept; new remote-only fields added.
        - MANUAL_FLAG: returns the local fields unchanged (conflict left for
          manual review).
        """
        if strategy is ResolutionStrategy.MANUAL_FLAG:
            return local_fields

        local_dict = dict(local_fields)

        if strategy is ResolutionStrategy.LOCAL_PRIORITY:
            # Keep all local values; add any remote-only keys.
            merged = dict(local_dict)
            for key, value in remote_fields.items():
                if key not in merged:
                    merged[key] = value
            return tuple(sorted(merged.items()))

        # REMOTE_PRIORITY and LAST_WRITE_WINS both let remote win.
        merged = dict(local_dict)
        merged.update(remote_fields)
        return tuple(sorted(merged.items()))
