"""
Base Domain Event

Architectural Intent:
- Foundation for event-driven cross-context communication
- All domain events are immutable (frozen dataclasses)
- Events are collected on aggregates and dispatched by the application layer
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True)
class DomainEvent:
    aggregate_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    event_id: str = field(default_factory=lambda: str(uuid4()))
