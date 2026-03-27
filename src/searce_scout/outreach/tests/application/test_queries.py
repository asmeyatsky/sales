"""Tests for Outreach query handlers."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from searce_scout.shared_kernel.types import AccountId, SequenceId, StakeholderId

from searce_scout.outreach.application.queries.get_sequence_status import (
    GetSequenceStatusHandler,
    GetSequenceStatusQuery,
)
from searce_scout.outreach.application.queries.list_active_sequences import (
    ListActiveSequencesHandler,
    ListActiveSequencesQuery,
)
from searce_scout.outreach.domain.entities.outreach_sequence import OutreachSequence
from searce_scout.outreach.domain.entities.sequence_step import SequenceStep
from searce_scout.outreach.domain.value_objects.sequence_status import SequenceStatus
from searce_scout.outreach.domain.value_objects.step_type import StepType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_sequence(
    sequence_id: str = "seq-1",
    status: SequenceStatus = SequenceStatus.ACTIVE,
) -> OutreachSequence:
    step = SequenceStep(
        step_number=1,
        step_type=StepType.EMAIL_1,
        message_id=None,
        scheduled_at=None,
        executed_at=None,
        result=None,
        delay_from_previous=timedelta(days=0),
    )
    return OutreachSequence(
        sequence_id=SequenceId(sequence_id),
        account_id=AccountId("acc-1"),
        stakeholder_id=StakeholderId("stk-1"),
        status=status,
        steps=(step,),
        current_step_index=0,
        started_at=None,
        stopped_at=None,
        stop_reason=None,
        domain_events=(),
    )


# ---------------------------------------------------------------------------
# GetSequenceStatus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_sequence_status_found():
    """Returns an OutreachSequenceDTO when the sequence exists."""
    sequence = _make_sequence()
    repo = AsyncMock()
    repo.get_by_id.return_value = sequence

    handler = GetSequenceStatusHandler(sequence_repository=repo)
    result = await handler.execute(GetSequenceStatusQuery(sequence_id="seq-1"))

    assert result is not None
    assert result.sequence_id == "seq-1"
    assert result.status == "active"
    assert result.total_steps == 1
    repo.get_by_id.assert_awaited_once_with(SequenceId("seq-1"))


@pytest.mark.asyncio
async def test_get_sequence_status_not_found():
    """Returns None when the sequence does not exist."""
    repo = AsyncMock()
    repo.get_by_id.return_value = None

    handler = GetSequenceStatusHandler(sequence_repository=repo)
    result = await handler.execute(GetSequenceStatusQuery(sequence_id="nonexistent"))

    assert result is None


# ---------------------------------------------------------------------------
# ListActiveSequences
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_active_sequences():
    """Returns DTOs for all active sequences."""
    seq_a = _make_sequence(sequence_id="seq-a")
    seq_b = _make_sequence(sequence_id="seq-b")

    repo = AsyncMock()
    repo.find_active.return_value = (seq_a, seq_b)

    handler = ListActiveSequencesHandler(sequence_repository=repo)
    result = await handler.execute(ListActiveSequencesQuery())

    assert len(result) == 2
    assert result[0].sequence_id == "seq-a"
    assert result[1].sequence_id == "seq-b"
    assert all(r.status == "active" for r in result)
    repo.find_active.assert_awaited_once()
