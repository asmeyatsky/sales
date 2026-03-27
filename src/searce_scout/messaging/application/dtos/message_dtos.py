"""DTOs for the Messaging application layer."""

from __future__ import annotations

from pydantic import BaseModel

from searce_scout.messaging.domain.entities.message import Message


class MessageDTO(BaseModel):
    message_id: str
    account_id: str
    stakeholder_id: str
    channel: str
    tone: str
    subject: str | None
    body: str
    call_to_action: str
    quality_score: float | None
    status: str
    company_name: str
    stakeholder_name: str
    buying_signals: list[str]
    searce_offering: str

    @classmethod
    def from_domain(cls, message: Message) -> MessageDTO:
        return cls(
            message_id=message.message_id,
            account_id=message.account_id,
            stakeholder_id=message.stakeholder_id,
            channel=message.channel.value,
            tone=message.tone.value,
            subject=message.subject,
            body=message.body,
            call_to_action=message.call_to_action,
            quality_score=message.quality_score,
            status=message.status.value,
            company_name=message.personalization_context.company_name,
            stakeholder_name=message.personalization_context.stakeholder_name,
            buying_signals=list(message.personalization_context.buying_signals),
            searce_offering=message.personalization_context.searce_offering,
        )
