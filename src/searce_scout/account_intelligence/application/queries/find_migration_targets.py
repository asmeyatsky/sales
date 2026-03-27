"""Query and handler for finding accounts that are migration targets."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.account_intelligence.application.dtos.account_dtos import (
    AccountProfileDTO,
)
from searce_scout.account_intelligence.domain.ports.account_repository_port import (
    AccountRepositoryPort,
)


@dataclass(frozen=True)
class FindMigrationTargetsQuery:
    min_score: float = 0.7


class FindMigrationTargetsHandler:
    """Returns all accounts whose migration opportunity score meets the threshold."""

    def __init__(self, account_repository: AccountRepositoryPort) -> None:
        self._account_repository = account_repository

    async def execute(self, query: FindMigrationTargetsQuery) -> list[AccountProfileDTO]:
        accounts = await self._account_repository.list_high_intent(query.min_score)
        return [AccountProfileDTO.from_domain(a) for a in accounts]
