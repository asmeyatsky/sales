"""Application tests for StartSequenceHandler.

Verifies that the handler builds a 5-step sequence via the domain engine,
starts it (ACTIVE), persists, and publishes events.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort

from searce_scout.outreach.application.commands.start_sequence import (
    StartSequenceCommand,
    StartSequenceHandler,
)
from searce_scout.outreach.domain.events.outreach_events import SequenceStartedEvent
from searce_scout.outreach.domain.ports.sequence_repository_port import (
    SequenceRepositoryPort,
)
from searce_scout.outreach.domain.services.sequence_engine import SequenceEngineService
from searce_scout.outreach.domain.value_objects.sequence_status import SequenceStatus


@pytest.fixture()
def sequence_repository() -> AsyncMock:
    return AsyncMock(spec=SequenceRepositoryPort)


@pytest.fixture()
def event_bus() -> AsyncMock:
    bus = AsyncMock(spec=EventBusPort)
    bus.publish.return_value = None
    return bus


def _build_handler(
    sequence_repository: AsyncMock,
    event_bus: AsyncMock,
) -> StartSequenceHandler:
    return StartSequenceHandler(
        sequence_engine=SequenceEngineService(),
        sequence_repository=sequence_repository,
        event_bus=event_bus,
    )


def _make_message_ids() -> dict[str, str]:
    """Map step type names to message IDs for all 5 steps."""
    return {
        "linkedin_request": "msg-lr",
        "email_1": "msg-e1",
        "linkedin_message": "msg-lm",
        "email_2": "msg-e2",
        "phone_task": "msg-pt",
    }


async def test_start_creates_five_step_sequence(
    sequence_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Handler must create a sequence with exactly 5 steps."""
    handler = _build_handler(sequence_repository, event_bus)

    cmd = StartSequenceCommand(
        account_id="acc-001",
        stakeholder_id="stk-001",
        message_ids=_make_message_ids(),
    )

    result = await handler.execute(cmd)

    # Verify the saved sequence has 5 steps
    sequence_repository.save.assert_awaited_once()
    assert result.total_steps == 5
    assert len(result.steps) == 5

    # Verify step order matches PRD-defined default
    step_types = [s.step_type for s in result.steps]
    assert step_types == [
        "linkedin_request",
        "email_1",
        "linkedin_message",
        "email_2",
        "phone_task",
    ]


async def test_start_sets_status_active(
    sequence_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Handler must transition the sequence from DRAFT to ACTIVE and publish SequenceStartedEvent."""
    handler = _build_handler(sequence_repository, event_bus)

    cmd = StartSequenceCommand(
        account_id="acc-001",
        stakeholder_id="stk-001",
        message_ids=_make_message_ids(),
    )

    result = await handler.execute(cmd)

    # Verify status is ACTIVE
    assert result.status == SequenceStatus.ACTIVE.value

    # Verify events were published, including SequenceStartedEvent
    event_bus.publish.assert_awaited_once()
    published_events = event_bus.publish.call_args[0][0]
    assert any(isinstance(e, SequenceStartedEvent) for e in published_events)

    # Verify started_at is set
    assert result.started_at is not None
