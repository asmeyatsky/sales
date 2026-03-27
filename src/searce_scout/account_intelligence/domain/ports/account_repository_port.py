"""Port (driven adapter interface) for account profile persistence."""

from __future__ import annotations

from typing import Protocol

from searce_scout.shared_kernel.types import AccountId
from searce_scout.shared_kernel.value_objects import CompanyName

from searce_scout.account_intelligence.domain.entities.account_profile import (
    AccountProfile,
)


class AccountRepositoryPort(Protocol):
    async def save(self, account: AccountProfile) -> None: ...

    async def get_by_id(self, account_id: AccountId) -> AccountProfile | None: ...

    async def find_by_company(
        self, company_name: CompanyName
    ) -> AccountProfile | None: ...

    async def list_high_intent(
        self, min_score: float
    ) -> tuple[AccountProfile, ...]: ...
