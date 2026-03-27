"""Query and handler for retrieving stakeholders with validated email addresses."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.types import AccountId

from searce_scout.stakeholder_discovery.application.dtos.stakeholder_dtos import (
    StakeholderDTO,
)
from searce_scout.stakeholder_discovery.domain.ports.stakeholder_repository_port import (
    StakeholderRepositoryPort,
)
from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    ValidationStatus,
)


@dataclass(frozen=True)
class GetValidatedContactsQuery:
    account_id: str


class GetValidatedContactsHandler:
    """Returns only stakeholders whose email has been validated (VALID status)."""

    def __init__(self, stakeholder_repository: StakeholderRepositoryPort) -> None:
        self._stakeholder_repository = stakeholder_repository

    async def execute(
        self, query: GetValidatedContactsQuery
    ) -> list[StakeholderDTO]:
        stakeholders = await self._stakeholder_repository.find_by_account(
            AccountId(query.account_id)
        )
        return [
            StakeholderDTO.from_domain(s)
            for s in stakeholders
            if s.contact_info is not None
            and s.contact_info.email_status == ValidationStatus.VALID
        ]
