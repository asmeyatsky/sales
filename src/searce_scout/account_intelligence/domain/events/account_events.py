"""Domain events emitted by the Account Intelligence bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.domain_event import DomainEvent

from searce_scout.account_intelligence.domain.value_objects.signal_type import (
    SignalStrength,
    SignalType,
)
from searce_scout.account_intelligence.domain.value_objects.tech_stack import (
    CloudProvider,
)


@dataclass(frozen=True)
class AccountResearchedEvent(DomainEvent):
    company_name: str = ""


@dataclass(frozen=True)
class BuyingSignalDetectedEvent(DomainEvent):
    signal_type: SignalType = SignalType.NEW_EXECUTIVE
    strength: SignalStrength = SignalStrength.WEAK


@dataclass(frozen=True)
class TechStackAuditedEvent(DomainEvent):
    primary_cloud: CloudProvider | None = None
    is_migration_target: bool = False
