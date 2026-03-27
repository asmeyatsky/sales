"""
Presentation domain events.

Events raised by the Presentation Gen bounded context when decks
are generated or exported.
"""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.domain_event import DomainEvent


@dataclass(frozen=True)
class DeckGeneratedEvent(DomainEvent):
    slide_count: int = 0


@dataclass(frozen=True)
class DeckExportedEvent(DomainEvent):
    google_slides_url: str = ""
