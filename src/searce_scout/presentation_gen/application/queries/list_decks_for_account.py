"""
ListDecksForAccountQuery and handler.

Retrieves all SlideDeck aggregates belonging to a given account.
"""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.types import AccountId

from searce_scout.presentation_gen.domain.ports.deck_repository_port import (
    DeckRepositoryPort,
)

from searce_scout.presentation_gen.application.dtos.presentation_dtos import DeckDTO


@dataclass(frozen=True)
class ListDecksForAccountQuery:
    account_id: str


class ListDecksForAccountHandler:
    """Returns all DeckDTOs for the specified account."""

    def __init__(self, deck_repository: DeckRepositoryPort) -> None:
        self._deck_repository = deck_repository

    async def execute(self, query: ListDecksForAccountQuery) -> list[DeckDTO]:
        decks = await self._deck_repository.find_by_account(
            AccountId(query.account_id)
        )
        return [DeckDTO.from_domain(d) for d in decks]
