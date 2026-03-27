"""
CRMProvider enumeration.

Identifies the external CRM system that a record is synced with.
"""

from enum import Enum, unique


@unique
class CRMProvider(Enum):
    SALESFORCE = "SALESFORCE"
    HUBSPOT = "HUBSPOT"
