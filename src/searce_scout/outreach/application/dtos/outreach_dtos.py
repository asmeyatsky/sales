"""DTOs for the Outreach application layer."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from searce_scout.outreach.domain.entities.outreach_sequence import OutreachSequence
from searce_scout.outreach.domain.entities.sequence_step import SequenceStep


class SequenceStepDTO(BaseModel):
    step_number: int
    step_type: str
    message_id: str | None
    scheduled_at: datetime | None
    executed_at: datetime | None
    success: bool | None
    error: str | None

    @classmethod
    def from_domain(cls, step: SequenceStep) -> SequenceStepDTO:
        return cls(
            step_number=step.step_number,
            step_type=step.step_type.value,
            message_id=step.message_id if step.message_id else None,
            scheduled_at=step.scheduled_at,
            executed_at=step.executed_at,
            success=step.result.success if step.result else None,
            error=step.result.error if step.result else None,
        )


class OutreachSequenceDTO(BaseModel):
    sequence_id: str
    account_id: str
    stakeholder_id: str
    status: str
    current_step_index: int
    total_steps: int
    steps: list[SequenceStepDTO]
    started_at: datetime | None
    stopped_at: datetime | None
    stop_reason: str | None

    @classmethod
    def from_domain(cls, sequence: OutreachSequence) -> OutreachSequenceDTO:
        return cls(
            sequence_id=sequence.sequence_id,
            account_id=sequence.account_id,
            stakeholder_id=sequence.stakeholder_id,
            status=sequence.status.value,
            current_step_index=sequence.current_step_index,
            total_steps=len(sequence.steps),
            steps=[SequenceStepDTO.from_domain(s) for s in sequence.steps],
            started_at=sequence.started_at,
            stopped_at=sequence.stopped_at,
            stop_reason=sequence.stop_reason,
        )
