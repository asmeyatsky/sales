"""Tests for Messaging query handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from searce_scout.shared_kernel.types import AccountId, MessageId, StakeholderId

from searce_scout.messaging.application.queries.get_message import (
    GetMessageHandler,
    GetMessageQuery,
)
from searce_scout.messaging.application.queries.preview_message import (
    PreviewMessageHandler,
    PreviewMessageQuery,
)
from searce_scout.messaging.domain.entities.message import Message
from searce_scout.messaging.domain.services.personalization_service import (
    PersonalizationService,
)
from searce_scout.messaging.domain.value_objects.channel import Channel
from searce_scout.messaging.domain.value_objects.message_content import (
    GeneratedMessage,
    MessageStatus,
)
from searce_scout.messaging.domain.value_objects.personalization import (
    PersonalizationContext,
)
from searce_scout.messaging.domain.value_objects.tone import Tone


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_message(message_id: str = "msg-1") -> Message:
    return Message(
        message_id=MessageId(message_id),
        account_id=AccountId("acc-1"),
        stakeholder_id=StakeholderId("stk-1"),
        channel=Channel.EMAIL,
        tone=Tone.PROFESSIONAL_CONSULTANT,
        subject="Hello",
        body="Test body",
        call_to_action="Let us chat",
        personalization_context=PersonalizationContext(
            company_name="Acme",
            stakeholder_name="Jane Doe",
            job_title="CTO",
            buying_signals=("cloud migration",),
            tech_stack_summary="AWS, PostgreSQL",
            pain_points=("legacy infra",),
            relevant_case_studies=(),
            searce_offering="GCP Migration",
        ),
        quality_score=0.9,
        status=MessageStatus.DRAFT,
    )


# ---------------------------------------------------------------------------
# GetMessage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_message_found():
    """Returns a MessageDTO when the message exists."""
    message = _make_message()
    repo = AsyncMock()
    repo.get_by_id.return_value = message

    handler = GetMessageHandler(message_repository=repo)
    result = await handler.execute(GetMessageQuery(message_id="msg-1"))

    assert result is not None
    assert result.message_id == "msg-1"
    assert result.channel == "email"
    assert result.body == "Test body"
    repo.get_by_id.assert_awaited_once_with(MessageId("msg-1"))


@pytest.mark.asyncio
async def test_get_message_not_found():
    """Returns None when the message does not exist."""
    repo = AsyncMock()
    repo.get_by_id.return_value = None

    handler = GetMessageHandler(message_repository=repo)
    result = await handler.execute(GetMessageQuery(message_id="nonexistent"))

    assert result is None


# ---------------------------------------------------------------------------
# PreviewMessage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_preview_message():
    """Generates a preview but does NOT persist it (no repository call)."""
    generated = GeneratedMessage(
        subject="Preview Subject",
        body="Preview body",
        call_to_action="Let us talk",
        quality_score=0.88,
    )

    ai_gen = AsyncMock()
    ai_gen.generate.return_value = generated

    case_study_port = AsyncMock()
    case_study_port.find_by_industry.return_value = ()
    case_study_port.find_by_offering.return_value = ()

    personalization_service = PersonalizationService()

    handler = PreviewMessageHandler(
        ai_message_generator=ai_gen,
        case_study_port=case_study_port,
        personalization_service=personalization_service,
    )

    query = PreviewMessageQuery(
        account_id="acc-1",
        stakeholder_id="stk-1",
        channel="email",
        tone="professional_consultant",
    )

    account_context = {
        "company_name": "Acme Corp",
        "industry": "Technology",
        "tech_stack_summary": "AWS, PostgreSQL",
        "buying_signals": ["cloud migration"],
        "pain_points": ["legacy infra"],
        "searce_offering": "GCP Migration",
    }
    stakeholder_context = {
        "stakeholder_name": "Jane Doe",
        "job_title": "CTO",
    }

    result = await handler.execute(query, account_context, stakeholder_context)

    # The handler should have called the AI generator
    ai_gen.generate.assert_awaited_once()

    # Result should be a MessageDTO with preview content
    assert result.body == "Preview body"
    assert result.subject == "Preview Subject"
    assert result.status == "draft"
    assert result.company_name == "Acme Corp"
