"""Tests for the SQLAlchemy MessageRepository adapter using an in-memory SQLite database."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from searce_scout.messaging.domain.entities.message import Message
from searce_scout.messaging.domain.value_objects.channel import Channel
from searce_scout.messaging.domain.value_objects.message_content import MessageStatus
from searce_scout.messaging.domain.value_objects.personalization import (
    CaseStudyRef,
    PersonalizationContext,
)
from searce_scout.messaging.domain.value_objects.tone import Tone
from searce_scout.messaging.infrastructure.adapters.message_repository import (
    MessageRepository,
    _Base,
)
from searce_scout.shared_kernel.types import AccountId, MessageId, StakeholderId


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _make_personalization_context() -> PersonalizationContext:
    return PersonalizationContext(
        company_name="Acme Corp",
        stakeholder_name="Jane Doe",
        job_title="CTO",
        buying_signals=("cloud migration", "digital transformation"),
        tech_stack_summary="AWS EC2, S3",
        pain_points=("legacy systems", "scaling issues"),
        relevant_case_studies=(
            CaseStudyRef(
                title="Cloud Migration Success",
                industry="Technology",
                outcome_summary="50% cost reduction",
                metric="50%",
            ),
        ),
        searce_offering="Cloud Migration",
    )


def _make_message(
    message_id: str = "msg-001",
    account_id: str = "acc-001",
    stakeholder_id: str = "stk-001",
) -> Message:
    return Message(
        message_id=MessageId(message_id),
        account_id=AccountId(account_id),
        stakeholder_id=StakeholderId(stakeholder_id),
        channel=Channel.EMAIL,
        tone=Tone.PROFESSIONAL_CONSULTANT,
        subject="Introduction to Searce",
        body="Dear Jane, I wanted to reach out about cloud migration...",
        call_to_action="Book a 15-minute call",
        personalization_context=_make_personalization_context(),
        quality_score=0.85,
        status=MessageStatus.DRAFT,
        domain_events=(),
    )


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_get_by_id(session: AsyncSession) -> None:
    """Save a message and retrieve it by ID; verify fields match."""
    repo = MessageRepository(session)
    message = _make_message()

    await repo.save(message)
    await session.commit()

    result = await repo.get_by_id(MessageId("msg-001"))

    assert result is not None
    assert str(result.message_id) == "msg-001"
    assert str(result.account_id) == "acc-001"
    assert str(result.stakeholder_id) == "stk-001"
    assert result.channel == Channel.EMAIL
    assert result.tone == Tone.PROFESSIONAL_CONSULTANT
    assert result.subject == "Introduction to Searce"
    assert "cloud migration" in result.body
    assert result.call_to_action == "Book a 15-minute call"
    assert result.quality_score == pytest.approx(0.85)
    assert result.status == MessageStatus.DRAFT
    assert result.personalization_context.company_name == "Acme Corp"
    assert result.personalization_context.stakeholder_name == "Jane Doe"
    assert len(result.personalization_context.relevant_case_studies) == 1


@pytest.mark.asyncio
async def test_find_by_stakeholder(session: AsyncSession) -> None:
    """Save messages for different stakeholders and find by stakeholder_id."""
    repo = MessageRepository(session)

    msg1 = _make_message(message_id="msg-001", stakeholder_id="stk-001")
    msg2 = _make_message(message_id="msg-002", stakeholder_id="stk-001")
    msg3 = _make_message(message_id="msg-003", stakeholder_id="stk-002")

    await repo.save(msg1)
    await repo.save(msg2)
    await repo.save(msg3)
    await session.commit()

    results = await repo.find_by_stakeholder(StakeholderId("stk-001"))
    assert len(results) == 2
    result_ids = {str(m.message_id) for m in results}
    assert result_ids == {"msg-001", "msg-002"}

    results_other = await repo.find_by_stakeholder(StakeholderId("stk-002"))
    assert len(results_other) == 1
    assert str(results_other[0].message_id) == "msg-003"

    results_none = await repo.find_by_stakeholder(StakeholderId("stk-999"))
    assert len(results_none) == 0
