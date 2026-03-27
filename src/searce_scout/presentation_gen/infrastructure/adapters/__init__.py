"""Infrastructure adapters for the Presentation Gen bounded context."""

from searce_scout.presentation_gen.infrastructure.adapters.deck_repository import (
    DeckRepository,
)
from searce_scout.presentation_gen.infrastructure.adapters.google_slides_renderer import (
    GoogleSlidesRenderer,
)

__all__ = [
    "DeckRepository",
    "GoogleSlidesRenderer",
]
