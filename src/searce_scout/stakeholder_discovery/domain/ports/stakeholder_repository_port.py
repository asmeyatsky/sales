"""Port (driven adapter interface) for stakeholder persistence."""

from __future__ import annotations

from typing import Protocol

from searce_scout.shared_kernel.types import AccountId, StakeholderId

from searce_scout.stakeholder_discovery.domain.entities.stakeholder import Stakeholder


class StakeholderRepositoryPort(Protocol):
    async def save(self, stakeholder: Stakeholder) -> None: ...

    async def get_by_id(
        self, stakeholder_id: StakeholderId
    ) -> Stakeholder | None: ...

    async def find_by_account(
        self, account_id: AccountId
    ) -> tuple[Stakeholder, ...]: ...
