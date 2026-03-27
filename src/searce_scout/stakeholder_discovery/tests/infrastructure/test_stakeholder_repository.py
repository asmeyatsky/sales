"""Tests for the SQLAlchemy StakeholderRepository adapter using an in-memory SQLite database."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from searce_scout.shared_kernel.types import AccountId, StakeholderId
from searce_scout.shared_kernel.value_objects import PersonName, URL
from searce_scout.stakeholder_discovery.domain.entities.stakeholder import Stakeholder
from searce_scout.stakeholder_discovery.domain.value_objects.job_title import JobTitle
from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    Department,
    Seniority,
)
from searce_scout.stakeholder_discovery.infrastructure.adapters.stakeholder_repository import (
    StakeholderRepository,
    _Base,
)


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _make_stakeholder(
    stakeholder_id: str = "stk-001",
    account_id: str = "acc-001",
    first_name: str = "Jane",
    last_name: str = "Doe",
) -> Stakeholder:
    return Stakeholder(
        stakeholder_id=StakeholderId(stakeholder_id),
        account_id=AccountId(account_id),
        person_name=PersonName(first_name=first_name, last_name=last_name),
        job_title=JobTitle(raw_title="CTO", normalized_title="CTO"),
        seniority=Seniority.C_SUITE,
        department=Department.ENGINEERING,
        contact_info=None,
        relevance_score=None,
        persona_match=None,
        linkedin_url=URL(value="https://linkedin.com/in/janedoe"),
        domain_events=(),
    )


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_get_by_id(session: AsyncSession) -> None:
    """Save a stakeholder and retrieve it by ID; verify fields match."""
    repo = StakeholderRepository(session)
    stakeholder = _make_stakeholder()

    await repo.save(stakeholder)
    await session.commit()

    result = await repo.get_by_id(StakeholderId("stk-001"))

    assert result is not None
    assert str(result.stakeholder_id) == "stk-001"
    assert str(result.account_id) == "acc-001"
    assert result.person_name.first_name == "Jane"
    assert result.person_name.last_name == "Doe"
    assert result.job_title.raw_title == "CTO"
    assert result.seniority == Seniority.C_SUITE
    assert result.department == Department.ENGINEERING
    assert result.linkedin_url is not None
    assert result.linkedin_url.value == "https://linkedin.com/in/janedoe"


@pytest.mark.asyncio
async def test_find_by_account(session: AsyncSession) -> None:
    """Save stakeholders for different accounts and find by account_id."""
    repo = StakeholderRepository(session)

    stk1 = _make_stakeholder(stakeholder_id="stk-001", account_id="acc-001", first_name="Alice", last_name="Smith")
    stk2 = _make_stakeholder(stakeholder_id="stk-002", account_id="acc-001", first_name="Bob", last_name="Jones")
    stk3 = _make_stakeholder(stakeholder_id="stk-003", account_id="acc-002", first_name="Carol", last_name="White")

    await repo.save(stk1)
    await repo.save(stk2)
    await repo.save(stk3)
    await session.commit()

    results = await repo.find_by_account(AccountId("acc-001"))

    assert len(results) == 2
    result_ids = {str(s.stakeholder_id) for s in results}
    assert result_ids == {"stk-001", "stk-002"}

    # The other account should only return one
    results_other = await repo.find_by_account(AccountId("acc-002"))
    assert len(results_other) == 1
    assert str(results_other[0].stakeholder_id) == "stk-003"

    # Non-existent account returns empty
    results_none = await repo.find_by_account(AccountId("acc-999"))
    assert len(results_none) == 0
