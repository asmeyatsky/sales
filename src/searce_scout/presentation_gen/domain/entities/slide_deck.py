"""
SlideDeck aggregate root.

The central aggregate for the Presentation Gen bounded context.
Manages an ordered collection of slides and tracks lifecycle events
(generation, export). All mutations return new frozen instances.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from searce_scout.shared_kernel.domain_event import DomainEvent
from searce_scout.shared_kernel.types import AccountId, DeckId
from searce_scout.shared_kernel.value_objects import URL

from searce_scout.presentation_gen.domain.events.presentation_events import (
    DeckExportedEvent,
)
from searce_scout.presentation_gen.domain.value_objects.slide import Slide
from searce_scout.presentation_gen.domain.value_objects.template_id import TemplateId


@dataclass(frozen=True)
class SlideDeck:
    deck_id: DeckId
    account_id: AccountId
    slides: tuple[Slide, ...]
    template_id: TemplateId
    google_slides_url: URL | None = None
    generated_at: datetime | None = None
    exported_at: datetime | None = None
    domain_events: tuple[DomainEvent, ...] = ()

    def add_slide(self, slide: Slide) -> SlideDeck:
        """Append a slide and return a new SlideDeck instance."""
        return replace(self, slides=self.slides + (slide,))

    def set_exported(self, url: URL) -> SlideDeck:
        """Mark the deck as exported to Google Slides, recording a DeckExportedEvent."""
        event = DeckExportedEvent(
            aggregate_id=self.deck_id,
            google_slides_url=url.value,
        )
        return replace(
            self,
            google_slides_url=url,
            exported_at=event.occurred_at,
            domain_events=self.domain_events + (event,),
        )

    def slide_count(self) -> int:
        """Return the number of slides in this deck."""
        return len(self.slides)
