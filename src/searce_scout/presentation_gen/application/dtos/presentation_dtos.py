"""
Presentation Gen DTOs.

Pydantic models for transferring presentation data across the application
boundary. Decouples the domain model from API / transport concerns.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from searce_scout.presentation_gen.domain.entities.slide_deck import SlideDeck
from searce_scout.presentation_gen.domain.value_objects.slide import Slide


class SlideDTO(BaseModel):
    slide_type: str
    title: str
    body: str
    speaker_notes: str
    order: int

    @classmethod
    def from_domain(cls, slide: Slide) -> SlideDTO:
        return cls(
            slide_type=slide.slide_type.value,
            title=slide.title,
            body=slide.body,
            speaker_notes=slide.speaker_notes,
            order=slide.order,
        )


class DeckDTO(BaseModel):
    deck_id: str
    account_id: str
    slide_count: int
    slides: list[SlideDTO]
    google_slides_url: str | None
    generated_at: datetime | None
    exported_at: datetime | None

    @classmethod
    def from_domain(cls, deck: SlideDeck) -> DeckDTO:
        return cls(
            deck_id=deck.deck_id,
            account_id=deck.account_id,
            slide_count=deck.slide_count(),
            slides=[SlideDTO.from_domain(s) for s in deck.slides],
            google_slides_url=deck.google_slides_url.value if deck.google_slides_url else None,
            generated_at=deck.generated_at,
            exported_at=deck.exported_at,
        )
