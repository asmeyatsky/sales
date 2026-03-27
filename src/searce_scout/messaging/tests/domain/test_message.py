"""Pure domain tests for the Message aggregate root.

No mocks — exercises status transitions, domain event emission,
tone adjustment, and invariant enforcement.
"""

import pytest

from searce_scout.shared_kernel.errors import DomainError
from searce_scout.shared_kernel.types import AccountId, MessageId, StakeholderId

from searce_scout.messaging.domain.entities.message import Message
from searce_scout.messaging.domain.events.message_events import (
    MessageApprovedEvent,
    ToneAdjustedEvent,
)
from searce_scout.messaging.domain.value_objects.channel import Channel
from searce_scout.messaging.domain.value_objects.message_content import MessageStatus
from searce_scout.messaging.domain.value_objects.personalization import (
    PersonalizationContext,
)
from searce_scout.messaging.domain.value_objects.tone import Tone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_message(status: MessageStatus = MessageStatus.DRAFT) -> Message:
    return Message(
        message_id=MessageId("msg-001"),
        account_id=AccountId("acct-001"),
        stakeholder_id=StakeholderId("stk-001"),
        channel=Channel.EMAIL,
        tone=Tone.PROFESSIONAL_CONSULTANT,
        subject="Hello",
        body="Original body text.",
        call_to_action="Let's connect",
        personalization_context=PersonalizationContext(
            company_name="Acme",
            stakeholder_name="Jane Doe",
            job_title="CTO",
            buying_signals=("New CTO hire",),
            tech_stack_summary="AWS-heavy",
            pain_points=("legacy costs",),
            relevant_case_studies=(),
            searce_offering="Cloud Migration",
        ),
        quality_score=0.85,
        status=status,
        domain_events=(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestApprove:
    def test_approve_changes_status_to_approved(self) -> None:
        msg = _make_message(MessageStatus.DRAFT)
        approved = msg.approve()
        assert approved.status is MessageStatus.APPROVED

    def test_approve_appends_event(self) -> None:
        msg = _make_message(MessageStatus.DRAFT)
        approved = msg.approve()
        assert len(approved.domain_events) == 1
        assert isinstance(approved.domain_events[0], MessageApprovedEvent)

    def test_approve_from_sent_raises_domain_error(self) -> None:
        msg = _make_message(MessageStatus.SENT)
        with pytest.raises(DomainError, match="Cannot approve"):
            msg.approve()


class TestAdjustTone:
    def test_adjust_tone_updates_body_and_tone(self) -> None:
        msg = _make_message()
        updated = msg.adjust_tone(Tone.WITTY_TECH_PARTNER, "Rewritten witty body.")

        # Original unchanged
        assert msg.tone is Tone.PROFESSIONAL_CONSULTANT
        assert msg.body == "Original body text."

        # Updated instance
        assert updated.tone is Tone.WITTY_TECH_PARTNER
        assert updated.body == "Rewritten witty body."
        assert len(updated.domain_events) == 1
        event = updated.domain_events[0]
        assert isinstance(event, ToneAdjustedEvent)
        assert event.old_tone == Tone.PROFESSIONAL_CONSULTANT.value
        assert event.new_tone == Tone.WITTY_TECH_PARTNER.value


class TestMarkSent:
    def test_mark_sent_changes_status(self) -> None:
        msg = _make_message(MessageStatus.DRAFT).approve().mark_sent()
        assert msg.status is MessageStatus.SENT

    def test_mark_sent_from_draft_raises_domain_error(self) -> None:
        msg = _make_message(MessageStatus.DRAFT)
        with pytest.raises(DomainError, match="Cannot mark message as sent"):
            msg.mark_sent()
