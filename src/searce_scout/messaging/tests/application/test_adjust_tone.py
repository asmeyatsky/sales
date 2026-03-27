"""Tests for the AdjustTone command handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from searce_scout.shared_kernel.types import AccountId, MessageId, StakeholderId

from searce_scout.messaging.application.commands.adjust_tone import (
    AdjustToneCommand,
    AdjustToneHandler,
)
from searce_scout.messaging.domain.entities.message import Message
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


def _make_message(
    message_id: str = "msg-1",
    tone: Tone = Tone.PROFESSIONAL_CONSULTANT,
) -> Message:
    return Message(
        message_id=MessageId(message_id),
        account_id=AccountId("acc-1"),
        stakeholder_id=StakeholderId("stk-1"),
        channel=Channel.EMAIL,
        tone=tone,
        subject="Hello",
        body="Original body",
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


def _make_generated() -> GeneratedMessage:
    return GeneratedMessage(
        subject="New Subject",
        body="Regenerated body with new tone",
        call_to_action="Schedule a call",
        quality_score=0.95,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adjust_tone_regenerates_message():
    """The handler calls AI generator with the new tone."""
    message = _make_message()
    generated = _make_generated()

    ai_gen = AsyncMock()
    ai_gen.generate.return_value = generated
    repo = AsyncMock()
    repo.get_by_id.return_value = message
    event_bus = AsyncMock()

    handler = AdjustToneHandler(
        ai_message_generator=ai_gen,
        message_repository=repo,
        event_bus=event_bus,
    )

    cmd = AdjustToneCommand(message_id="msg-1", new_tone="witty_tech_partner")
    result = await handler.execute(cmd)

    # AI generator must be called with the new tone
    ai_gen.generate.assert_awaited_once()
    call_kwargs = ai_gen.generate.call_args
    assert call_kwargs.kwargs.get("tone") == Tone.WITTY_TECH_PARTNER or (
        len(call_kwargs.args) >= 3 and call_kwargs.args[2] == Tone.WITTY_TECH_PARTNER
    )

    assert result.tone == "witty_tech_partner"
    assert result.body == "Regenerated body with new tone"


@pytest.mark.asyncio
async def test_adjust_tone_saves_updated_message():
    """The handler persists the updated message via the repository."""
    message = _make_message()
    generated = _make_generated()

    ai_gen = AsyncMock()
    ai_gen.generate.return_value = generated
    repo = AsyncMock()
    repo.get_by_id.return_value = message
    event_bus = AsyncMock()

    handler = AdjustToneHandler(
        ai_message_generator=ai_gen,
        message_repository=repo,
        event_bus=event_bus,
    )

    cmd = AdjustToneCommand(message_id="msg-1", new_tone="witty_tech_partner")
    await handler.execute(cmd)

    repo.save.assert_awaited_once()
    saved_msg = repo.save.call_args[0][0]
    assert saved_msg.tone == Tone.WITTY_TECH_PARTNER
    assert saved_msg.body == "Regenerated body with new tone"
