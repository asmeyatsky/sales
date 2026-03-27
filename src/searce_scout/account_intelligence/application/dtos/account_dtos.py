"""DTOs for the Account Intelligence application layer."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from searce_scout.account_intelligence.domain.entities.account_profile import (
    AccountProfile,
)
from searce_scout.account_intelligence.domain.entities.buying_signal import (
    BuyingSignal,
)


class BuyingSignalDTO(BaseModel):
    signal_id: str
    signal_type: str
    strength: str
    description: str
    source_url: str | None
    detected_at: datetime

    @classmethod
    def from_domain(cls, signal: BuyingSignal) -> BuyingSignalDTO:
        return cls(
            signal_id=signal.signal_id,
            signal_type=signal.signal_type.value,
            strength=signal.strength.value,
            description=signal.description,
            source_url=str(signal.source_url) if signal.source_url else None,
            detected_at=signal.detected_at,
        )


class AccountProfileDTO(BaseModel):
    account_id: str
    company_name: str
    industry_name: str
    industry_vertical: str
    company_size: str
    website: str | None
    tech_stack_summary: str | None
    primary_cloud: str | None
    is_migration_target: bool
    buying_signal_count: int
    migration_opportunity_score: float
    is_high_intent: bool
    researched_at: datetime | None

    @classmethod
    def from_domain(cls, account: AccountProfile) -> AccountProfileDTO:
        tech_stack = account.tech_stack
        tech_summary: str | None = None
        primary_cloud: str | None = None
        is_migration_target = False

        if tech_stack is not None:
            component_names = [c.name for c in tech_stack.components]
            tech_summary = ", ".join(component_names) if component_names else None
            primary_cloud = tech_stack.primary_cloud.value if tech_stack.primary_cloud else None
            is_migration_target = tech_stack.is_migration_target()

        return cls(
            account_id=str(account.account_id),
            company_name=str(account.company_name),
            industry_name=account.industry.name,
            industry_vertical=account.industry.vertical,
            company_size=account.company_size.value,
            website=str(account.website) if account.website else None,
            tech_stack_summary=tech_summary,
            primary_cloud=primary_cloud,
            is_migration_target=is_migration_target,
            buying_signal_count=len(account.buying_signals),
            migration_opportunity_score=account.migration_opportunity_score(),
            is_high_intent=account.is_high_intent(),
            researched_at=account.researched_at,
        )
