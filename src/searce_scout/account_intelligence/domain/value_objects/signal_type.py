"""Signal type and strength enumerations for buying signals."""

from __future__ import annotations

from enum import Enum


class SignalType(Enum):
    NEW_EXECUTIVE = "NEW_EXECUTIVE"
    HIRING_SPREE = "HIRING_SPREE"
    DIGITAL_TRANSFORMATION_GOAL = "DIGITAL_TRANSFORMATION_GOAL"
    CLOUD_MIGRATION_MENTION = "CLOUD_MIGRATION_MENTION"
    FUNDING_ROUND = "FUNDING_ROUND"
    TECH_DEBT_COMPLAINT = "TECH_DEBT_COMPLAINT"
    VENDOR_CONTRACT_EXPIRY = "VENDOR_CONTRACT_EXPIRY"


class SignalStrength(Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    CRITICAL = "CRITICAL"
