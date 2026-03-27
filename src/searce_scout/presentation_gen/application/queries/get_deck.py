"""
GetDeckQuery and handler.

Retrieves a single SlideDeck by its identifier.
"""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.types import DeckId

from searce_scout.presentation_gen.domain.ports.deck_repository_port import (
    DeckRepositoryPort,
)

from searce_scout.presentation_gen.application.dtos.presentation_dtos import DeckDTO


@dataclass(frozen=True)
class GetDeckQuery:
    deck_id: str


class GetDeckHandler:
    """Returns a DeckDTO for the requested deck, or None if not found."""

    def __init__(self, deck_repository: DeckRepositoryPort) -> None:
        self._deck_repository = deck_repository

    async def execute(self, query: GetDeckQuery) -> DeckDTO | None:
        deck = await self._deck_repository.get_by_id(DeckId(query.deck_id))
        if deck is None:
            return None
        return DeckDTO.from_domain(deck)
