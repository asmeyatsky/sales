"""
DeckRepositoryPort — persistence port for the SlideDeck aggregate.
"""

from __future__ import annotations

from typing import Protocol

from searce_scout.shared_kernel.types import AccountId, DeckId

from searce_scout.presentation_gen.domain.entities.slide_deck import SlideDeck


class DeckRepositoryPort(Protocol):
    async def save(self, deck: SlideDeck) -> None: ...

    async def get_by_id(self, deck_id: DeckId) -> SlideDeck | None: ...

    async def find_by_account(
        self, account_id: AccountId
    ) -> tuple[SlideDeck, ...]: ...
