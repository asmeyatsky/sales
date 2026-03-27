"""Application tests for ExecuteNextStepHandler.

Verifies that the handler dispatches to the correct channel port based on
the step type, advances the sequence, and persists the updated state.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import AccountId, MessageId, SequenceId, StakeholderId

from searce_scout.messaging.domain.ports.message_repository_port import (
    MessageRepositoryPort,
)
from searce_scout.outreach.application.commands.execute_next_step import (
    ExecuteNextStepCommand,
    ExecuteNextStepHandler,
)
from searce_scout.outreach.domain.entities.outreach_sequence import OutreachSequence
from searce_scout.outreach.domain.entities.sequence_step import SequenceStep
from searce_scout.outreach.domain.ports.email_sender_port import (
    EmailSenderPort,
    SendResult,
)
from searce_scout.outreach.domain.ports.linkedin_messenger_port import (
    LinkedInMessengerPort,
)
from searce_scout.outreach.domain.ports.sequence_repository_port import (
    SequenceRepositoryPort,
)
from searce_scout.outreach.domain.ports.task_creator_port import TaskCreatorPort
from searce_scout.outreach.domain.value_objects.sequence_status import SequenceStatus
from searce_scout.outreach.domain.value_objects.step_type import StepType


def _make_sequence(step_type: StepType) -> OutreachSequence:
    """Build an ACTIVE sequence whose current step is the given type."""
    step = SequenceStep(
        step_number=1,
        step_type=step_type,
        message_id=MessageId("msg-001"),
        scheduled_at=None,
        executed_at=None,
        result=None,
        delay_from_previous=timedelta(hours=0),
    )
    return OutreachSequence(
        sequence_id=SequenceId("seq-001"),
        account_id=AccountId("acc-001"),
        stakeholder_id=StakeholderId("stk-001"),
        status=SequenceStatus.ACTIVE,
        steps=(step,),
        current_step_index=0,
        started_at=None,
        stopped_at=None,
        stop_reason=None,
        domain_events=(),
    )


def _make_message_mock() -> MagicMock:
    """Build a mock Message with subject and body."""
    msg = MagicMock()
    msg.subject = "Test Subject"
    msg.body = "Test body content for the outreach step."
    return msg


@pytest.fixture()
def sequence_repository() -> AsyncMock:
    return AsyncMock(spec=SequenceRepositoryPort)


@pytest.fixture()
def message_repository() -> AsyncMock:
    return AsyncMock(spec=MessageRepositoryPort)


@pytest.fixture()
def email_sender() -> AsyncMock:
    sender = AsyncMock(spec=EmailSenderPort)
    sender.send.return_value = SendResult(success=True, message_id="email-ext-001")
    return sender


@pytest.fixture()
def linkedin_messenger() -> AsyncMock:
    messenger = AsyncMock(spec=LinkedInMessengerPort)
    messenger.send_connection_request.return_value = SendResult(
        success=True, message_id="li-ext-001"
    )
    messenger.send_message.return_value = SendResult(
        success=True, message_id="li-msg-ext-001"
    )
    return messenger


@pytest.fixture()
def task_creator() -> AsyncMock:
    return AsyncMock(spec=TaskCreatorPort)


@pytest.fixture()
def event_bus() -> AsyncMock:
    bus = AsyncMock(spec=EventBusPort)
    bus.publish.return_value = None
    return bus


def _build_handler(
    sequence_repository: AsyncMock,
    message_repository: AsyncMock,
    email_sender: AsyncMock,
    linkedin_messenger: AsyncMock,
    task_creator: AsyncMock,
    event_bus: AsyncMock,
) -> ExecuteNextStepHandler:
    return ExecuteNextStepHandler(
        sequence_repository=sequence_repository,
        message_repository=message_repository,
        email_sender=email_sender,
        linkedin_messenger=linkedin_messenger,
        task_creator=task_creator,
        event_bus=event_bus,
    )


async def test_execute_email_step_calls_email_sender(
    sequence_repository: AsyncMock,
    message_repository: AsyncMock,
    email_sender: AsyncMock,
    linkedin_messenger: AsyncMock,
    task_creator: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Executing an EMAIL_1 step must call the email_sender port."""
    sequence = _make_sequence(StepType.EMAIL_1)
    sequence_repository.get_by_id.return_value = sequence
    message_repository.get_by_id.return_value = _make_message_mock()

    handler = _build_handler(
        sequence_repository,
        message_repository,
        email_sender,
        linkedin_messenger,
        task_creator,
        event_bus,
    )

    cmd = ExecuteNextStepCommand(sequence_id="seq-001")
    await handler.execute(cmd)

    email_sender.send.assert_awaited_once()
    linkedin_messenger.send_connection_request.assert_not_awaited()
    linkedin_messenger.send_message.assert_not_awaited()


async def test_execute_linkedin_step_calls_linkedin_messenger(
    sequence_repository: AsyncMock,
    message_repository: AsyncMock,
    email_sender: AsyncMock,
    linkedin_messenger: AsyncMock,
    task_creator: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Executing a LINKEDIN_REQUEST step must call linkedin_messenger.send_connection_request."""
    sequence = _make_sequence(StepType.LINKEDIN_REQUEST)
    sequence_repository.get_by_id.return_value = sequence
    message_repository.get_by_id.return_value = _make_message_mock()

    handler = _build_handler(
        sequence_repository,
        message_repository,
        email_sender,
        linkedin_messenger,
        task_creator,
        event_bus,
    )

    cmd = ExecuteNextStepCommand(sequence_id="seq-001")
    await handler.execute(cmd)

    linkedin_messenger.send_connection_request.assert_awaited_once()
    email_sender.send.assert_not_awaited()


async def test_execute_advances_sequence(
    sequence_repository: AsyncMock,
    message_repository: AsyncMock,
    email_sender: AsyncMock,
    linkedin_messenger: AsyncMock,
    task_creator: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """After execution, the sequence must be persisted with an advanced step index."""
    sequence = _make_sequence(StepType.EMAIL_1)
    sequence_repository.get_by_id.return_value = sequence
    message_repository.get_by_id.return_value = _make_message_mock()

    handler = _build_handler(
        sequence_repository,
        message_repository,
        email_sender,
        linkedin_messenger,
        task_creator,
        event_bus,
    )

    cmd = ExecuteNextStepCommand(sequence_id="seq-001")
    result = await handler.execute(cmd)

    # The sequence had only 1 step, so advancing past it marks it COMPLETED
    sequence_repository.save.assert_awaited_once()
    assert result.status == SequenceStatus.COMPLETED.value

    # Events should be published (StepExecutedEvent + SequenceCompletedEvent)
    event_bus.publish.assert_awaited_once()
