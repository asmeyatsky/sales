"""Domain events emitted by the Stakeholder Discovery bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.domain_event import DomainEvent

from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    ValidationStatus,
)


@dataclass(frozen=True)
class StakeholderIdentifiedEvent(DomainEvent):
    person_name: str = ""
    job_title: str = ""
    account_id: str = ""


@dataclass(frozen=True)
class ContactValidatedEvent(DomainEvent):
    email_status: ValidationStatus = ValidationStatus.UNVALIDATED
    phone_status: ValidationStatus = ValidationStatus.UNVALIDATED


@dataclass(frozen=True)
class StakeholderScoredEvent(DomainEvent):
    relevance_score: float = 0.0
    persona_match: str = ""
