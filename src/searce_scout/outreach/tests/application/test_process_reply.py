"""Application tests for ProcessReplyHandler.

Verifies that the handler classifies replies via AI and applies the
correct action to the sequence based on the classification.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import AccountId, MessageId, SequenceId, StakeholderId

from searce_scout.outreach.application.commands.process_reply import (
    ProcessReplyCommand,
    ProcessReplyHandler,
)
from searce_scout.outreach.domain.entities.outreach_sequence import OutreachSequence
from searce_scout.outreach.domain.entities.sequence_step import SequenceStep
from searce_scout.outreach.domain.ports.ai_classifier_port import AIClassifierPort
from searce_scout.outreach.domain.ports.sequence_repository_port import (
    SequenceRepositoryPort,
)
from searce_scout.outreach.domain.services.reply_classification_service import (
    ReplyClassificationService,
)
from searce_scout.outreach.domain.value_objects.reply_classification import (
    ReplyClassification,
)
from searce_scout.outreach.domain.value_objects.sequence_status import SequenceStatus
from searce_scout.outreach.domain.value_objects.step_type import StepType


def _make_active_sequence() -> OutreachSequence:
    """Build an ACTIVE sequence with 5 steps."""
    step_types = [
        StepType.LINKEDIN_REQUEST,
        StepType.EMAIL_1,
        StepType.LINKEDIN_MESSAGE,
        StepType.EMAIL_2,
        StepType.PHONE_TASK,
    ]
    steps = tuple(
        SequenceStep(
            step_number=i + 1,
            step_type=st,
            message_id=MessageId(f"msg-{i+1}"),
            scheduled_at=None,
            executed_at=None,
            result=None,
            delay_from_previous=timedelta(hours=24),
        )
        for i, st in enumerate(step_types)
    )
    return OutreachSequence(
        sequence_id=SequenceId("seq-reply"),
        account_id=AccountId("acc-001"),
        stakeholder_id=StakeholderId("stk-001"),
        status=SequenceStatus.ACTIVE,
        steps=steps,
        current_step_index=1,
        started_at=None,
        stopped_at=None,
        stop_reason=None,
        domain_events=(),
    )


@pytest.fixture()
def ai_classifier() -> AsyncMock:
    return AsyncMock(spec=AIClassifierPort)


@pytest.fixture()
def sequence_repository() -> AsyncMock:
    return AsyncMock(spec=SequenceRepositoryPort)


@pytest.fixture()
def event_bus() -> AsyncMock:
    bus = AsyncMock(spec=EventBusPort)
    bus.publish.return_value = None
    return bus


def _build_handler(
    ai_classifier: AsyncMock,
    sequence_repository: AsyncMock,
    event_bus: AsyncMock,
) -> ProcessReplyHandler:
    return ProcessReplyHandler(
        ai_classifier=ai_classifier,
        reply_classification_service=ReplyClassificationService(),
        sequence_repository=sequence_repository,
        event_bus=event_bus,
    )


async def test_not_interested_stops_sequence(
    ai_classifier: AsyncMock,
    sequence_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """A NOT_INTERESTED reply must stop the sequence."""
    ai_classifier.classify_reply.return_value = (
        ReplyClassification.NOT_INTERESTED,
        0.95,
    )
    sequence_repository.get_by_id.return_value = _make_active_sequence()

    handler = _build_handler(ai_classifier, sequence_repository, event_bus)
    cmd = ProcessReplyCommand(sequence_id="seq-reply", raw_content="No thanks, not interested.")

    result = await handler.execute(cmd)

    assert result.status == SequenceStatus.STOPPED.value
    assert result.stop_reason is not None
    assert "not_interested" in result.stop_reason.lower()

    sequence_repository.save.assert_awaited_once()
    event_bus.publish.assert_awaited_once()


async def test_ooo_pauses_sequence(
    ai_classifier: AsyncMock,
    sequence_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """An OOO reply must pause the sequence."""
    ai_classifier.classify_reply.return_value = (
        ReplyClassification.OOO,
        0.88,
    )
    sequence_repository.get_by_id.return_value = _make_active_sequence()

    handler = _build_handler(ai_classifier, sequence_repository, event_bus)
    cmd = ProcessReplyCommand(
        sequence_id="seq-reply",
        raw_content="I am out of office until next week.",
    )

    result = await handler.execute(cmd)

    assert result.status == SequenceStatus.PAUSED.value

    sequence_repository.save.assert_awaited_once()
    event_bus.publish.assert_awaited_once()


async def test_positive_stops_sequence(
    ai_classifier: AsyncMock,
    sequence_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """A POSITIVE reply must stop the sequence (escalate to sales)."""
    ai_classifier.classify_reply.return_value = (
        ReplyClassification.POSITIVE,
        0.91,
    )
    sequence_repository.get_by_id.return_value = _make_active_sequence()

    handler = _build_handler(ai_classifier, sequence_repository, event_bus)
    cmd = ProcessReplyCommand(
        sequence_id="seq-reply",
        raw_content="Yes, I would love to learn more about your offering!",
    )

    result = await handler.execute(cmd)

    assert result.status == SequenceStatus.STOPPED.value
    assert result.stop_reason is not None
    assert "positive" in result.stop_reason.lower()

    sequence_repository.save.assert_awaited_once()
    event_bus.publish.assert_awaited_once()
