"""
RecordType enumeration.

Classifies CRM records by their logical type.
"""

from enum import Enum, unique


@unique
class RecordType(Enum):
    LEAD = "LEAD"
    CONTACT = "CONTACT"
    ACCOUNT = "ACCOUNT"
    OPPORTUNITY = "OPPORTUNITY"
    ACTIVITY = "ACTIVITY"
