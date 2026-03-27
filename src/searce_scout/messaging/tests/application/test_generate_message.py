"""Application tests for GenerateMessageHandler.

Verifies that the handler generates a personalized message, persists it,
and publishes the MessageGeneratedEvent.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort

from searce_scout.messaging.application.commands.generate_message import (
    GenerateMessageCommand,
    GenerateMessageHandler,
)
from searce_scout.messaging.domain.events.message_events import MessageGeneratedEvent
from searce_scout.messaging.domain.ports.ai_message_generator_port import (
    AIMessageGeneratorPort,
)
from searce_scout.messaging.domain.ports.case_study_port import CaseStudyPort
from searce_scout.messaging.domain.ports.message_repository_port import (
    MessageRepositoryPort,
)
from searce_scout.messaging.domain.services.personalization_service import (
    PersonalizationService,
)
from searce_scout.messaging.domain.value_objects.message_content import GeneratedMessage
from searce_scout.messaging.domain.value_objects.personalization import CaseStudyRef


def _make_generated_message() -> GeneratedMessage:
    return GeneratedMessage(
        subject="Unlock cloud savings for TestCo",
        body="Hi Alice, I noticed TestCo is exploring cloud migration...",
        call_to_action="Would a 15-minute call next week work?",
        quality_score=0.92,
    )


def _make_case_study() -> CaseStudyRef:
    return CaseStudyRef(
        title="FinanceCo Cloud Migration",
        industry="Finance",
        outcome_summary="40% cost reduction",
        metric="$2M annual savings",
    )


def _make_account_context() -> dict:
    return {
        "company_name": "TestCo",
        "industry": "Technology",
        "tech_stack_summary": "AWS EC2, S3",
        "buying_signals": ["Cloud migration announcement"],
        "pain_points": ["Legacy infrastructure costs"],
        "searce_offering": "Cloud Migration",
    }


def _make_stakeholder_context() -> dict:
    return {
        "stakeholder_name": "Alice Smith",
        "job_title": "CTO",
    }


@pytest.fixture()
def ai_message_generator() -> AsyncMock:
    gen = AsyncMock(spec=AIMessageGeneratorPort)
    gen.generate.return_value = _make_generated_message()
    return gen


@pytest.fixture()
def case_study_port() -> AsyncMock:
    port = AsyncMock(spec=CaseStudyPort)
    cs = _make_case_study()
    port.find_by_industry.return_value = (cs,)
    port.find_by_offering.return_value = ()
    return port


@pytest.fixture()
def message_repository() -> AsyncMock:
    return AsyncMock(spec=MessageRepositoryPort)


@pytest.fixture()
def event_bus() -> AsyncMock:
    bus = AsyncMock(spec=EventBusPort)
    bus.publish.return_value = None
    return bus


def _build_handler(
    ai_message_generator: AsyncMock,
    case_study_port: AsyncMock,
    message_repository: AsyncMock,
    event_bus: AsyncMock,
) -> GenerateMessageHandler:
    return GenerateMessageHandler(
        ai_message_generator=ai_message_generator,
        case_study_port=case_study_port,
        message_repository=message_repository,
        event_bus=event_bus,
        personalization_service=PersonalizationService(),
    )


async def test_generate_creates_and_saves_message(
    ai_message_generator: AsyncMock,
    case_study_port: AsyncMock,
    message_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Handler must generate a message via AI, create a Message aggregate, and save it."""
    handler = _build_handler(
        ai_message_generator, case_study_port, message_repository, event_bus
    )

    cmd = GenerateMessageCommand(
        account_id="acc-001",
        stakeholder_id="stk-001",
        channel="email",
        tone="professional_consultant",
        step_number=1,
    )

    result = await handler.execute(
        cmd,
        account_context=_make_account_context(),
        stakeholder_context=_make_stakeholder_context(),
    )

    # Verify AI generator was called
    ai_message_generator.generate.assert_awaited_once()

    # Verify message was saved
    message_repository.save.assert_awaited_once()
    saved_message = message_repository.save.call_args[0][0]
    assert saved_message.body == "Hi Alice, I noticed TestCo is exploring cloud migration..."
    assert saved_message.subject == "Unlock cloud savings for TestCo"
    assert saved_message.quality_score == 0.92

    # Verify DTO
    assert result.channel == "email"
    assert result.body == "Hi Alice, I noticed TestCo is exploring cloud migration..."
    assert result.status == "draft"


async def test_generate_uses_correct_tone(
    ai_message_generator: AsyncMock,
    case_study_port: AsyncMock,
    message_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Handler must pass the requested tone through to the AI generator."""
    handler = _build_handler(
        ai_message_generator, case_study_port, message_repository, event_bus
    )

    cmd = GenerateMessageCommand(
        account_id="acc-001",
        stakeholder_id="stk-001",
        channel="linkedin_message",
        tone="witty_tech_partner",
        step_number=2,
    )

    await handler.execute(
        cmd,
        account_context=_make_account_context(),
        stakeholder_context=_make_stakeholder_context(),
    )

    # Verify the AI generator received the correct tone
    call_kwargs = ai_message_generator.generate.call_args
    from searce_scout.messaging.domain.value_objects.tone import Tone
    from searce_scout.messaging.domain.value_objects.channel import Channel

    assert call_kwargs.kwargs["tone"] == Tone.WITTY_TECH_PARTNER
    assert call_kwargs.kwargs["channel"] == Channel.LINKEDIN_MESSAGE


async def test_generate_publishes_message_generated_event(
    ai_message_generator: AsyncMock,
    case_study_port: AsyncMock,
    message_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Handler must publish a MessageGeneratedEvent after saving the message."""
    handler = _build_handler(
        ai_message_generator, case_study_port, message_repository, event_bus
    )

    cmd = GenerateMessageCommand(
        account_id="acc-001",
        stakeholder_id="stk-001",
        channel="email",
        tone="professional_consultant",
        step_number=1,
    )

    await handler.execute(
        cmd,
        account_context=_make_account_context(),
        stakeholder_context=_make_stakeholder_context(),
    )

    event_bus.publish.assert_awaited_once()
    published_events = event_bus.publish.call_args[0][0]
    assert len(published_events) >= 1
    assert any(isinstance(e, MessageGeneratedEvent) for e in published_events)

    # Verify the event has correct fields
    msg_event = next(e for e in published_events if isinstance(e, MessageGeneratedEvent))
    assert msg_event.channel == "email"
    assert msg_event.tone == "professional_consultant"
    assert msg_event.quality_score == 0.92
