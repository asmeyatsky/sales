"""Query and handler for retrieving all stakeholders for a given account."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.types import AccountId

from searce_scout.stakeholder_discovery.application.dtos.stakeholder_dtos import (
    StakeholderDTO,
)
from searce_scout.stakeholder_discovery.domain.ports.stakeholder_repository_port import (
    StakeholderRepositoryPort,
)


@dataclass(frozen=True)
class GetStakeholdersForAccountQuery:
    account_id: str


class GetStakeholdersForAccountHandler:
    """Returns all discovered stakeholders for a given account."""

    def __init__(self, stakeholder_repository: StakeholderRepositoryPort) -> None:
        self._stakeholder_repository = stakeholder_repository

    async def execute(
        self, query: GetStakeholdersForAccountQuery
    ) -> list[StakeholderDTO]:
        stakeholders = await self._stakeholder_repository.find_by_account(
            AccountId(query.account_id)
        )
        return [StakeholderDTO.from_domain(s) for s in stakeholders]
