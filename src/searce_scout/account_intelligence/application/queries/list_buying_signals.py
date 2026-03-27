"""Query and handler for listing buying signals for an account."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.types import AccountId

from searce_scout.account_intelligence.application.dtos.account_dtos import (
    BuyingSignalDTO,
)
from searce_scout.account_intelligence.domain.ports.account_repository_port import (
    AccountRepositoryPort,
)


@dataclass(frozen=True)
class ListBuyingSignalsQuery:
    account_id: str


class ListBuyingSignalsHandler:
    """Returns all buying signals for a given account."""

    def __init__(self, account_repository: AccountRepositoryPort) -> None:
        self._account_repository = account_repository

    async def execute(self, query: ListBuyingSignalsQuery) -> list[BuyingSignalDTO]:
        account = await self._account_repository.get_by_id(
            AccountId(query.account_id)
        )
        if account is None:
            return []
        return [
            BuyingSignalDTO.from_domain(signal)
            for signal in account.buying_signals
        ]
