"""SQLAlchemy message repository adapter — implements MessageRepositoryPort.

Persists Message aggregates using an async SQLAlchemy session.
Provides an ORM model (MessageModel) that maps between the relational
representation and the frozen domain Message dataclass.
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from searce_scout.messaging.domain.entities.message import Message
from searce_scout.messaging.domain.ports.message_repository_port import (
    MessageRepositoryPort,
)
from searce_scout.messaging.domain.value_objects.channel import Channel
from searce_scout.messaging.domain.value_objects.message_content import MessageStatus
from searce_scout.messaging.domain.value_objects.personalization import (
    CaseStudyRef,
    PersonalizationContext,
)
from searce_scout.messaging.domain.value_objects.tone import Tone
from searce_scout.shared_kernel.types import AccountId, MessageId, StakeholderId


# ---------------------------------------------------------------------------
# ORM base and table model
# ---------------------------------------------------------------------------


class _Base(DeclarativeBase):
    pass


class MessageModel(_Base):
    """Relational mapping for the Message aggregate."""

    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(sa.String(64), nullable=False, index=True)
    stakeholder_id: Mapped[str] = mapped_column(
        sa.String(64), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    tone: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    subject: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    body: Mapped[str] = mapped_column(sa.Text, nullable=False)
    call_to_action: Mapped[str] = mapped_column(sa.Text, nullable=False)
    personalization_json: Mapped[str] = mapped_column(sa.Text, nullable=False)
    quality_score: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False)


# ---------------------------------------------------------------------------
# Repository implementation
# ---------------------------------------------------------------------------


class MessageRepository:
    """Persists and retrieves Message aggregates via SQLAlchemy async.

    Implements :class:`MessageRepositoryPort`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # MessageRepositoryPort implementation
    # ------------------------------------------------------------------

    async def save(self, message: Message) -> None:
        """Upsert a Message into the database."""
        model = self._to_model(message)
        await self._session.merge(model)
        await self._session.flush()

    async def get_by_id(self, message_id: MessageId) -> Message | None:
        """Retrieve a Message by its unique identifier."""
        stmt = sa.select(MessageModel).where(
            MessageModel.message_id == str(message_id)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def find_by_stakeholder(
        self, stakeholder_id: StakeholderId
    ) -> tuple[Message, ...]:
        """Find all Messages for a given stakeholder."""
        stmt = (
            sa.select(MessageModel)
            .where(MessageModel.stakeholder_id == str(stakeholder_id))
            .order_by(MessageModel.message_id)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return tuple(self._to_domain(row) for row in rows)

    # ------------------------------------------------------------------
    # Domain <-> ORM mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _to_model(message: Message) -> MessageModel:
        """Convert a domain Message to an ORM model."""
        ctx = message.personalization_context
        personalization_data = {
            "company_name": ctx.company_name,
            "stakeholder_name": ctx.stakeholder_name,
            "job_title": ctx.job_title,
            "buying_signals": list(ctx.buying_signals),
            "tech_stack_summary": ctx.tech_stack_summary,
            "pain_points": list(ctx.pain_points),
            "relevant_case_studies": [
                {
                    "title": cs.title,
                    "industry": cs.industry,
                    "outcome_summary": cs.outcome_summary,
                    "metric": cs.metric,
                }
                for cs in ctx.relevant_case_studies
            ],
            "searce_offering": ctx.searce_offering,
        }

        return MessageModel(
            message_id=str(message.message_id),
            account_id=str(message.account_id),
            stakeholder_id=str(message.stakeholder_id),
            channel=message.channel.value,
            tone=message.tone.value,
            subject=message.subject,
            body=message.body,
            call_to_action=message.call_to_action,
            personalization_json=json.dumps(personalization_data),
            quality_score=message.quality_score,
            status=message.status.value,
        )

    @staticmethod
    def _to_domain(model: MessageModel) -> Message:
        """Convert an ORM model back to a domain Message."""
        ctx_data = json.loads(model.personalization_json)

        case_studies = tuple(
            CaseStudyRef(
                title=cs["title"],
                industry=cs["industry"],
                outcome_summary=cs["outcome_summary"],
                metric=cs["metric"],
            )
            for cs in ctx_data.get("relevant_case_studies", [])
        )

        context = PersonalizationContext(
            company_name=ctx_data["company_name"],
            stakeholder_name=ctx_data["stakeholder_name"],
            job_title=ctx_data["job_title"],
            buying_signals=tuple(ctx_data.get("buying_signals", [])),
            tech_stack_summary=ctx_data.get("tech_stack_summary", ""),
            pain_points=tuple(ctx_data.get("pain_points", [])),
            relevant_case_studies=case_studies,
            searce_offering=ctx_data.get("searce_offering", ""),
        )

        return Message(
            message_id=MessageId(model.message_id),
            account_id=AccountId(model.account_id),
            stakeholder_id=StakeholderId(model.stakeholder_id),
            channel=Channel(model.channel),
            tone=Tone(model.tone),
            subject=model.subject,
            body=model.body,
            call_to_action=model.call_to_action,
            personalization_context=context,
            quality_score=model.quality_score,
            status=MessageStatus(model.status),
            domain_events=(),
        )


# Structural compatibility assertion
def _check_port_compliance(session: AsyncSession) -> None:
    _: MessageRepositoryPort = MessageRepository(session=session)  # type: ignore[assignment]
