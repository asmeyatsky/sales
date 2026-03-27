"""
SyncDirection enumeration.

Defines the direction of data flow for a field mapping between
the local system and an external CRM.
"""

from enum import Enum, unique


@unique
class SyncDirection(Enum):
    PUSH = "PUSH"
    PULL = "PULL"
    BIDIRECTIONAL = "BIDIRECTIONAL"
