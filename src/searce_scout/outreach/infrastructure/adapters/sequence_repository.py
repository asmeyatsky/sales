"""SQLAlchemy-based persistence adapter for the OutreachSequence aggregate.

Implements SequenceRepositoryPort using async SQLAlchemy.  Internal ORM
models (SequenceModel, SequenceStepModel) are private implementation
details -- callers interact only with the domain OutreachSequence and
SequenceStep aggregates.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, relationship

from searce_scout.shared_kernel.types import (
    AccountId,
    MessageId,
    SequenceId,
    StakeholderId,
)
from searce_scout.outreach.domain.entities.outreach_sequence import OutreachSequence
from searce_scout.outreach.domain.entities.sequence_step import SequenceStep
from searce_scout.outreach.domain.ports.sequence_repository_port import (
    SequenceRepositoryPort,
)
from searce_scout.outreach.domain.value_objects.sequence_status import SequenceStatus
from searce_scout.outreach.domain.value_objects.step_type import StepResult, StepType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQLAlchemy ORM models (private to this module)
# ---------------------------------------------------------------------------

class _Base(DeclarativeBase):
    pass


class SequenceStepModel(_Base):
    """ORM model for a single step within an outreach sequence."""

    __tablename__ = "sequence_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence_id = Column(
        String(64), ForeignKey("outreach_sequences.sequence_id"), nullable=False, index=True
    )
    step_number = Column(Integer, nullable=False)
    step_type = Column(SAEnum(StepType), nullable=False)
    message_id = Column(String(64), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)

    # StepResult fields (flattened)
    result_success = Column(Boolean, nullable=True)
    result_channel_message_id = Column(String(256), nullable=True)
    result_error = Column(Text, nullable=True)

    # Delay stored as total seconds for portability
    delay_seconds = Column(Float, nullable=False, default=0.0)


class SequenceModel(_Base):
    """ORM model for the OutreachSequence aggregate root."""

    __tablename__ = "outreach_sequences"

    sequence_id = Column(String(64), primary_key=True)
    account_id = Column(String(64), nullable=False, index=True)
    stakeholder_id = Column(String(64), nullable=False, index=True)
    status = Column(SAEnum(SequenceStatus), nullable=False)
    current_step_index = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    stop_reason = Column(Text, nullable=True)

    steps = relationship(
        SequenceStepModel,
        order_by=SequenceStepModel.step_number,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


# ---------------------------------------------------------------------------
# Repository adapter
# ---------------------------------------------------------------------------

class SequenceRepository:
    """Async SQLAlchemy adapter implementing :class:`SequenceRepositoryPort`.

    Parameters
    ----------
    session:
        An async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- SequenceRepositoryPort interface -----------------------------------

    async def save(self, sequence: OutreachSequence) -> None:
        """Persist an OutreachSequence aggregate (upsert)."""
        model = self._to_model(sequence)
        await self._session.merge(model)
        await self._session.flush()

    async def get_by_id(self, sequence_id: SequenceId) -> OutreachSequence | None:
        """Retrieve a single sequence by its identifier."""
        stmt = select(SequenceModel).where(
            SequenceModel.sequence_id == str(sequence_id)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def find_active(self) -> tuple[OutreachSequence, ...]:
        """Return all sequences in ACTIVE status."""
        stmt = (
            select(SequenceModel)
            .where(SequenceModel.status == SequenceStatus.ACTIVE)
            .order_by(SequenceModel.started_at)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return tuple(self._to_domain(r) for r in rows)

    async def find_due_for_execution(
        self, now: datetime
    ) -> tuple[OutreachSequence, ...]:
        """Return active sequences whose current step is scheduled at or before *now*."""
        # We first fetch all active sequences, then filter in Python so
        # the domain invariant (current_step_index pointing into .steps)
        # is respected without duplicating that logic in SQL.
        active = await self.find_active()
        due: list[OutreachSequence] = []

        for seq in active:
            step = seq.current_step()
            if step is not None and step.scheduled_at is not None:
                if step.scheduled_at <= now and step.executed_at is None:
                    due.append(seq)

        return tuple(due)

    # -- Mapping helpers ----------------------------------------------------

    @staticmethod
    def _to_model(seq: OutreachSequence) -> SequenceModel:
        """Map a domain OutreachSequence to its ORM representation."""
        step_models = [
            SequenceStepModel(
                sequence_id=str(seq.sequence_id),
                step_number=step.step_number,
                step_type=step.step_type,
                message_id=str(step.message_id) if step.message_id else None,
                scheduled_at=step.scheduled_at,
                executed_at=step.executed_at,
                result_success=step.result.success if step.result else None,
                result_channel_message_id=(
                    step.result.channel_message_id if step.result else None
                ),
                result_error=step.result.error if step.result else None,
                delay_seconds=step.delay_from_previous.total_seconds(),
            )
            for step in seq.steps
        ]

        return SequenceModel(
            sequence_id=str(seq.sequence_id),
            account_id=str(seq.account_id),
            stakeholder_id=str(seq.stakeholder_id),
            status=seq.status,
            current_step_index=seq.current_step_index,
            started_at=seq.started_at,
            stopped_at=seq.stopped_at,
            stop_reason=seq.stop_reason,
            steps=step_models,
        )

    @staticmethod
    def _to_domain(m: SequenceModel) -> OutreachSequence:
        """Map ORM models back to a domain OutreachSequence aggregate."""
        domain_steps: list[SequenceStep] = []

        for sm in m.steps:
            result: StepResult | None = None
            if sm.result_success is not None:
                result = StepResult(
                    success=sm.result_success,
                    channel_message_id=sm.result_channel_message_id,
                    error=sm.result_error,
                )

            domain_steps.append(
                SequenceStep(
                    step_number=sm.step_number,
                    step_type=sm.step_type,
                    message_id=MessageId(sm.message_id) if sm.message_id else None,
                    scheduled_at=sm.scheduled_at,
                    executed_at=sm.executed_at,
                    result=result,
                    delay_from_previous=timedelta(seconds=sm.delay_seconds),
                )
            )

        return OutreachSequence(
            sequence_id=SequenceId(m.sequence_id),
            account_id=AccountId(m.account_id),
            stakeholder_id=StakeholderId(m.stakeholder_id),
            status=m.status,
            steps=tuple(domain_steps),
            current_step_index=m.current_step_index,
            started_at=m.started_at,
            stopped_at=m.stopped_at,
            stop_reason=m.stop_reason,
            domain_events=(),
        )


# Structural compatibility check with the port Protocol.
_check: type[SequenceRepositoryPort] = SequenceRepository  # type: ignore[assignment]
