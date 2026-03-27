"""Message aggregate root."""

from __future__ import annotations

from dataclasses import dataclass, replace

from searce_scout.shared_kernel.domain_event import DomainEvent
from searce_scout.shared_kernel.errors import DomainError
from searce_scout.shared_kernel.types import AccountId, MessageId, StakeholderId

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


@dataclass(frozen=True)
class Message:
    """Aggregate root representing a generated outreach message.

    All state transitions produce new instances via dataclasses.replace().
    Domain events are collected in the domain_events tuple and dispatched
    by the application layer after persistence.
    """

    message_id: MessageId
    account_id: AccountId
    stakeholder_id: StakeholderId
    channel: Channel
    tone: Tone
    subject: str | None
    body: str
    call_to_action: str
    personalization_context: PersonalizationContext
    quality_score: float | None
    status: MessageStatus
    domain_events: tuple[DomainEvent, ...] = ()

    def approve(self) -> Message:
        """Approve this message for sending.

        Transitions status from DRAFT to APPROVED and records a
        MessageApprovedEvent.

        Raises:
            DomainError: If message is not in DRAFT status.
        """
        if self.status is not MessageStatus.DRAFT:
            raise DomainError(
                f"Cannot approve message in status {self.status.value}; "
                f"must be {MessageStatus.DRAFT.value}"
            )

        event = MessageApprovedEvent(aggregate_id=self.message_id)
        return replace(
            self,
            status=MessageStatus.APPROVED,
            domain_events=self.domain_events + (event,),
        )

    def adjust_tone(self, new_tone: Tone, new_body: str) -> Message:
        """Adjust the tone of this message, replacing its body.

        Records a ToneAdjustedEvent capturing the old and new tones.

        Args:
            new_tone: The target tone.
            new_body: The rewritten body text matching the new tone.

        Returns:
            A new Message instance with updated tone and body.
        """
        event = ToneAdjustedEvent(
            aggregate_id=self.message_id,
            old_tone=self.tone.value,
            new_tone=new_tone.value,
        )
        return replace(
            self,
            tone=new_tone,
            body=new_body,
            domain_events=self.domain_events + (event,),
        )

    def mark_sent(self) -> Message:
        """Mark this message as successfully sent.

        Transitions status from APPROVED to SENT.

        Raises:
            DomainError: If message is not in APPROVED status.
        """
        if self.status is not MessageStatus.APPROVED:
            raise DomainError(
                f"Cannot mark message as sent in status {self.status.value}; "
                f"must be {MessageStatus.APPROVED.value}"
            )

        return replace(self, status=MessageStatus.SENT)
