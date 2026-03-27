"""Domain events for the Outreach bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class SequenceStartedEvent(DomainEvent):
    """Raised when an outreach sequence transitions to ACTIVE."""

    stakeholder_id: str = ""


@dataclass(frozen=True)
class StepExecutedEvent(DomainEvent):
    """Raised when a sequence step is executed."""

    step_number: int = 0
    step_type: str = ""
    success: bool = False


@dataclass(frozen=True)
class ReplyReceivedEvent(DomainEvent):
    """Raised when a reply is received and classified."""

    classification: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class SequenceStoppedEvent(DomainEvent):
    """Raised when a sequence is stopped (manually or due to a reply)."""

    reason: str = ""


@dataclass(frozen=True)
class SequenceCompletedEvent(DomainEvent):
    """Raised when all steps in a sequence have been completed."""
