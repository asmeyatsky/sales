"""
SyncStatus enumeration.

Tracks the synchronisation lifecycle of a CRM record.
"""

from enum import Enum, unique


@unique
class SyncStatus(Enum):
    PENDING = "PENDING"
    SYNCED = "SYNCED"
    CONFLICT = "CONFLICT"
    FAILED = "FAILED"
