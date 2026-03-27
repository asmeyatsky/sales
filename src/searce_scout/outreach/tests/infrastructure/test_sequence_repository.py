"""Tests for the SQLAlchemy SequenceRepository adapter using an in-memory SQLite database."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from searce_scout.outreach.domain.entities.outreach_sequence import OutreachSequence
from searce_scout.outreach.domain.entities.sequence_step import SequenceStep
from searce_scout.outreach.domain.value_objects.sequence_status import SequenceStatus
from searce_scout.outreach.domain.value_objects.step_type import StepType
from searce_scout.outreach.infrastructure.adapters.sequence_repository import (
    SequenceRepository,
    _Base,
)
from searce_scout.shared_kernel.types import AccountId, MessageId, SequenceId, StakeholderId


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _make_step(
    step_number: int = 1,
    step_type: StepType = StepType.EMAIL_1,
    scheduled_at: datetime | None = None,
    executed_at: datetime | None = None,
) -> SequenceStep:
    return SequenceStep(
        step_number=step_number,
        step_type=step_type,
        message_id=MessageId("msg-001"),
        scheduled_at=scheduled_at,
        executed_at=executed_at,
        result=None,
        delay_from_previous=timedelta(hours=48),
    )


def _make_sequence(
    sequence_id: str = "seq-001",
    account_id: str = "acc-001",
    stakeholder_id: str = "stk-001",
    status: SequenceStatus = SequenceStatus.DRAFT,
    steps: tuple[SequenceStep, ...] | None = None,
    started_at: datetime | None = None,
) -> OutreachSequence:
    if steps is None:
        steps = (_make_step(),)
    return OutreachSequence(
        sequence_id=SequenceId(sequence_id),
        account_id=AccountId(account_id),
        stakeholder_id=StakeholderId(stakeholder_id),
        status=status,
        steps=steps,
        current_step_index=0,
        started_at=started_at,
        stopped_at=None,
        stop_reason=None,
        domain_events=(),
    )


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_get_by_id(session: AsyncSession) -> None:
    """Save a sequence and retrieve it by ID; verify fields match."""
    repo = SequenceRepository(session)
    sequence = _make_sequence()

    await repo.save(sequence)
    await session.commit()

    result = await repo.get_by_id(SequenceId("seq-001"))

    assert result is not None
    assert str(result.sequence_id) == "seq-001"
    assert str(result.account_id) == "acc-001"
    assert str(result.stakeholder_id) == "stk-001"
    assert result.status == SequenceStatus.DRAFT
    assert result.current_step_index == 0
    assert len(result.steps) == 1
    assert result.steps[0].step_type == StepType.EMAIL_1
    assert result.steps[0].delay_from_previous == timedelta(hours=48)


@pytest.mark.asyncio
async def test_find_active(session: AsyncSession) -> None:
    """Save sequences with different statuses and find only ACTIVE ones."""
    repo = SequenceRepository(session)
    now = datetime(2026, 3, 27, 12, 0, 0, tzinfo=timezone.utc)

    seq_active1 = _make_sequence(
        sequence_id="seq-active-1",
        status=SequenceStatus.ACTIVE,
        started_at=now,
    )
    seq_active2 = _make_sequence(
        sequence_id="seq-active-2",
        status=SequenceStatus.ACTIVE,
        started_at=now,
    )
    seq_draft = _make_sequence(
        sequence_id="seq-draft",
        status=SequenceStatus.DRAFT,
    )
    seq_completed = _make_sequence(
        sequence_id="seq-completed",
        status=SequenceStatus.COMPLETED,
    )

    await repo.save(seq_active1)
    await repo.save(seq_active2)
    await repo.save(seq_draft)
    await repo.save(seq_completed)
    await session.commit()

    results = await repo.find_active()

    assert len(results) == 2
    result_ids = {str(s.sequence_id) for s in results}
    assert result_ids == {"seq-active-1", "seq-active-2"}
    for seq in results:
        assert seq.status == SequenceStatus.ACTIVE


@pytest.mark.asyncio
async def test_find_due_for_execution(session: AsyncSession) -> None:
    """Return sequences with due steps (scheduled_at <= now and not executed)."""
    repo = SequenceRepository(session)
    now = datetime(2026, 3, 27, 12, 0, 0, tzinfo=timezone.utc)
    past = now - timedelta(hours=1)
    future = now + timedelta(hours=1)

    # Sequence with a step scheduled in the past (due)
    step_due = _make_step(step_number=1, scheduled_at=past, executed_at=None)
    seq_due = _make_sequence(
        sequence_id="seq-due",
        status=SequenceStatus.ACTIVE,
        steps=(step_due,),
        started_at=now - timedelta(days=1),
    )

    # Sequence with a step scheduled in the future (not due)
    step_future = _make_step(step_number=1, scheduled_at=future, executed_at=None)
    seq_future = _make_sequence(
        sequence_id="seq-future",
        status=SequenceStatus.ACTIVE,
        steps=(step_future,),
        started_at=now - timedelta(days=1),
    )

    # Sequence with a step already executed (not due even if past)
    step_executed = _make_step(step_number=1, scheduled_at=past, executed_at=past)
    seq_executed = _make_sequence(
        sequence_id="seq-executed",
        status=SequenceStatus.ACTIVE,
        steps=(step_executed,),
        started_at=now - timedelta(days=1),
    )

    await repo.save(seq_due)
    await repo.save(seq_future)
    await repo.save(seq_executed)
    await session.commit()

    results = await repo.find_due_for_execution(now)

    assert len(results) == 1
    assert str(results[0].sequence_id) == "seq-due"
