"""Query and handler for retrieving a single account profile."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.types import AccountId

from searce_scout.account_intelligence.application.dtos.account_dtos import (
    AccountProfileDTO,
)
from searce_scout.account_intelligence.domain.ports.account_repository_port import (
    AccountRepositoryPort,
)


@dataclass(frozen=True)
class GetAccountProfileQuery:
    account_id: str


class GetAccountProfileHandler:
    """Returns the profile DTO for a single account, or None if not found."""

    def __init__(self, account_repository: AccountRepositoryPort) -> None:
        self._account_repository = account_repository

    async def execute(self, query: GetAccountProfileQuery) -> AccountProfileDTO | None:
        account = await self._account_repository.get_by_id(
            AccountId(query.account_id)
        )
        if account is None:
            return None
        return AccountProfileDTO.from_domain(account)
