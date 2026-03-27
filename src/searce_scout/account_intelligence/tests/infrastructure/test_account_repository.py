"""Tests for the SQLAlchemy AccountRepository adapter using an in-memory SQLite database."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from searce_scout.account_intelligence.domain.entities.account_profile import (
    AccountProfile,
)
from searce_scout.account_intelligence.domain.entities.buying_signal import BuyingSignal
from searce_scout.account_intelligence.domain.value_objects.filing_data import FilingData
from searce_scout.account_intelligence.domain.value_objects.industry import (
    CompanySize,
    Industry,
)
from searce_scout.account_intelligence.domain.value_objects.signal_type import (
    SignalStrength,
    SignalType,
)
from searce_scout.account_intelligence.domain.value_objects.tech_stack import (
    CloudProvider,
    TechComponent,
    TechStack,
)
from searce_scout.account_intelligence.infrastructure.adapters.account_repository import (
    AccountRepository,
    _Base,
)
from searce_scout.shared_kernel.types import AccountId
from searce_scout.shared_kernel.value_objects import URL, CompanyName


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _make_account(
    account_id: str = "acc-001",
    company_name: str = "Acme Corp",
    intent_score_hint: float | None = None,
    signals: tuple[BuyingSignal, ...] = (),
    tech_stack: TechStack | None = None,
) -> AccountProfile:
    """Helper to build an AccountProfile with sensible defaults."""
    return AccountProfile(
        account_id=AccountId(account_id),
        company_name=CompanyName(canonical=company_name),
        industry=Industry(name="Technology", vertical="SaaS"),
        company_size=CompanySize.ENTERPRISE,
        tech_stack=tech_stack,
        buying_signals=signals,
        filing_data=None,
        website=URL(value="https://acme.example.com"),
        researched_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        domain_events=(),
    )


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_get_by_id(session: AsyncSession) -> None:
    """Save an account and retrieve it by ID; verify all fields match."""
    repo = AccountRepository(session)
    account = _make_account()

    await repo.save(account)
    await session.commit()

    result = await repo.get_by_id(AccountId("acc-001"))

    assert result is not None
    assert str(result.account_id) == "acc-001"
    assert result.company_name.canonical == "Acme Corp"
    assert result.industry.name == "Technology"
    assert result.industry.vertical == "SaaS"
    assert result.company_size == CompanySize.ENTERPRISE
    assert result.website is not None
    assert result.website.value == "https://acme.example.com"
    assert result.researched_at is not None


@pytest.mark.asyncio
async def test_find_by_company(session: AsyncSession) -> None:
    """Save an account and find it by company name."""
    repo = AccountRepository(session)
    account = _make_account(company_name="Globex Inc")

    await repo.save(account)
    await session.commit()

    result = await repo.find_by_company(CompanyName(canonical="Globex Inc"))

    assert result is not None
    assert result.company_name.canonical == "Globex Inc"


@pytest.mark.asyncio
async def test_find_by_company_not_found(session: AsyncSession) -> None:
    """Searching for a company that doesn't exist returns None."""
    repo = AccountRepository(session)

    result = await repo.find_by_company(CompanyName(canonical="Nonexistent Corp"))

    assert result is None


@pytest.mark.asyncio
async def test_list_high_intent(session: AsyncSession) -> None:
    """Save 3 accounts with different scores and verify high-intent filtering."""
    repo = AccountRepository(session)

    # Account with high score: has competitor cloud + critical buying signal
    high_score_account = _make_account(
        account_id="acc-high",
        company_name="HighScore Inc",
        tech_stack=TechStack(
            components=(
                TechComponent(name="EC2", category="compute", provider=CloudProvider.AWS),
            ),
            primary_cloud=CloudProvider.AWS,
        ),
        signals=(
            BuyingSignal(
                signal_id="sig-1",
                signal_type=SignalType.CLOUD_MIGRATION_MENTION,
                strength=SignalStrength.CRITICAL,
                description="Major migration initiative",
                source_url=None,
                detected_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
            ),
            BuyingSignal(
                signal_id="sig-2",
                signal_type=SignalType.DIGITAL_TRANSFORMATION_GOAL,
                strength=SignalStrength.CRITICAL,
                description="DT goal",
                source_url=None,
                detected_at=datetime(2026, 1, 11, tzinfo=timezone.utc),
            ),
            BuyingSignal(
                signal_id="sig-3",
                signal_type=SignalType.NEW_EXECUTIVE,
                strength=SignalStrength.CRITICAL,
                description="New CTO",
                source_url=None,
                detected_at=datetime(2026, 1, 12, tzinfo=timezone.utc),
            ),
        ),
    )

    # Account with medium score: competitor cloud, moderate signal
    medium_score_account = _make_account(
        account_id="acc-medium",
        company_name="MediumScore Ltd",
        tech_stack=TechStack(
            components=(
                TechComponent(name="Azure VM", category="compute", provider=CloudProvider.AZURE),
            ),
            primary_cloud=CloudProvider.AZURE,
        ),
        signals=(
            BuyingSignal(
                signal_id="sig-4",
                signal_type=SignalType.HIRING_SPREE,
                strength=SignalStrength.MODERATE,
                description="Hiring cloud engineers",
                source_url=None,
                detected_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
            ),
        ),
    )

    # Account with zero score: no tech stack, no signals
    low_score_account = _make_account(
        account_id="acc-low",
        company_name="LowScore Co",
    )

    await repo.save(high_score_account)
    await repo.save(medium_score_account)
    await repo.save(low_score_account)
    await session.commit()

    # The high and medium accounts should have non-zero scores.
    # Use a threshold that only the highest-scored account passes.
    high_results = await repo.list_high_intent(min_score=0.5)
    assert len(high_results) >= 1
    # All returned must have score >= 0.5
    for acct in high_results:
        assert acct.migration_opportunity_score() >= 0.5

    # With a threshold of 0.0 we should get all accounts
    all_results = await repo.list_high_intent(min_score=0.0)
    assert len(all_results) == 3

    # With a very high threshold we might get 0 or 1
    very_high = await repo.list_high_intent(min_score=0.99)
    for acct in very_high:
        assert acct.migration_opportunity_score() >= 0.99
