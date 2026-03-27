"""Tests for the StopSequence command handler."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from searce_scout.shared_kernel.types import AccountId, SequenceId, StakeholderId

from searce_scout.outreach.application.commands.stop_sequence import (
    StopSequenceCommand,
    StopSequenceHandler,
)
from searce_scout.outreach.domain.entities.outreach_sequence import OutreachSequence
from searce_scout.outreach.domain.entities.sequence_step import SequenceStep
from searce_scout.outreach.domain.value_objects.sequence_status import SequenceStatus
from searce_scout.outreach.domain.value_objects.step_type import StepType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_active_sequence(sequence_id: str = "seq-1") -> OutreachSequence:
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
        status=SequenceStatus.ACTIVE,
        steps=(step,),
        current_step_index=0,
        started_at=None,
        stopped_at=None,
        stop_reason=None,
        domain_events=(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_sequence_sets_stopped_status():
    """After stopping, the returned DTO reflects STOPPED status."""
    sequence = _make_active_sequence()

    repo = AsyncMock()
    repo.get_by_id.return_value = sequence
    event_bus = AsyncMock()

    handler = StopSequenceHandler(
        sequence_repository=repo,
        event_bus=event_bus,
    )

    cmd = StopSequenceCommand(sequence_id="seq-1", reason="No longer needed")
    result = await handler.execute(cmd)

    assert result.status == "stopped"
    assert result.stop_reason == "No longer needed"


@pytest.mark.asyncio
async def test_stop_sequence_publishes_event():
    """The handler publishes domain events after stopping the sequence."""
    sequence = _make_active_sequence()

    repo = AsyncMock()
    repo.get_by_id.return_value = sequence
    event_bus = AsyncMock()

    handler = StopSequenceHandler(
        sequence_repository=repo,
        event_bus=event_bus,
    )

    cmd = StopSequenceCommand(sequence_id="seq-1", reason="Budget cut")
    await handler.execute(cmd)

    event_bus.publish.assert_awaited_once()
    published_events = event_bus.publish.call_args[0][0]
    assert len(published_events) > 0
