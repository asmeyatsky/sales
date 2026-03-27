"""OutreachSequence aggregate root."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from searce_scout.shared_kernel.domain_event import DomainEvent
from searce_scout.shared_kernel.errors import DomainError
from searce_scout.shared_kernel.types import AccountId, SequenceId, StakeholderId

from searce_scout.outreach.domain.entities.sequence_step import SequenceStep
from searce_scout.outreach.domain.events.outreach_events import (
    SequenceCompletedEvent,
    SequenceStartedEvent,
    SequenceStoppedEvent,
    StepExecutedEvent,
)
from searce_scout.outreach.domain.value_objects.sequence_status import SequenceStatus
from searce_scout.outreach.domain.value_objects.step_type import StepResult


@dataclass(frozen=True)
class OutreachSequence:
    """Aggregate root representing a multi-step outreach sequence.

    Enforces state machine invariants on all transitions. Every
    mutation returns a new instance via dataclasses.replace().
    Domain events are accumulated for dispatch by the application layer.
    """

    sequence_id: SequenceId
    account_id: AccountId
    stakeholder_id: StakeholderId
    status: SequenceStatus
    steps: tuple[SequenceStep, ...]
    current_step_index: int
    started_at: datetime | None
    stopped_at: datetime | None
    stop_reason: str | None
    domain_events: tuple[DomainEvent, ...] = ()

    # ------------------------------------------------------------------
    # State-machine transitions
    # ------------------------------------------------------------------

    def start(self) -> OutreachSequence:
        """Transition from DRAFT to ACTIVE.

        Raises:
            DomainError: If the sequence is not in DRAFT status.
        """
        self._assert_status(SequenceStatus.DRAFT, "start")

        event = SequenceStartedEvent(
            aggregate_id=self.sequence_id,
            stakeholder_id=self.stakeholder_id,
        )
        return replace(
            self,
            status=SequenceStatus.ACTIVE,
            started_at=datetime.now(),
            domain_events=self.domain_events + (event,),
        )

    def advance_to_next_step(self) -> OutreachSequence:
        """Move to the next step in the sequence.

        If all steps have been visited, transitions to COMPLETED.

        Raises:
            DomainError: If the sequence is not ACTIVE.
        """
        self._assert_status(SequenceStatus.ACTIVE, "advance")

        next_index = self.current_step_index + 1

        if next_index >= len(self.steps):
            event = SequenceCompletedEvent(aggregate_id=self.sequence_id)
            return replace(
                self,
                status=SequenceStatus.COMPLETED,
                current_step_index=next_index,
                domain_events=self.domain_events + (event,),
            )

        return replace(self, current_step_index=next_index)

    def complete_current_step(self, result: StepResult) -> OutreachSequence:
        """Record the result of executing the current step.

        Args:
            result: The outcome of the step execution.

        Raises:
            DomainError: If the sequence is not ACTIVE or there is no
                current step.
        """
        self._assert_status(SequenceStatus.ACTIVE, "complete step")

        step = self.current_step()
        if step is None:
            raise DomainError("No current step to complete")

        updated_step = replace(
            step,
            executed_at=datetime.now(),
            result=result,
        )

        steps_list = list(self.steps)
        steps_list[self.current_step_index] = updated_step
        updated_steps = tuple(steps_list)

        event = StepExecutedEvent(
            aggregate_id=self.sequence_id,
            step_number=step.step_number,
            step_type=step.step_type.value,
            success=result.success,
        )

        return replace(
            self,
            steps=updated_steps,
            domain_events=self.domain_events + (event,),
        )

    def stop(self, reason: str) -> OutreachSequence:
        """Stop the sequence.

        Valid from ACTIVE or PAUSED status.

        Args:
            reason: Human-readable reason for stopping.

        Raises:
            DomainError: If the sequence is not stoppable.
        """
        if not self.is_stoppable():
            raise DomainError(
                f"Cannot stop sequence in status {self.status.value}; "
                f"must be ACTIVE or PAUSED"
            )

        event = SequenceStoppedEvent(
            aggregate_id=self.sequence_id,
            reason=reason,
        )
        return replace(
            self,
            status=SequenceStatus.STOPPED,
            stopped_at=datetime.now(),
            stop_reason=reason,
            domain_events=self.domain_events + (event,),
        )

    def pause(self) -> OutreachSequence:
        """Pause an active sequence.

        Raises:
            DomainError: If the sequence is not ACTIVE.
        """
        self._assert_status(SequenceStatus.ACTIVE, "pause")
        return replace(self, status=SequenceStatus.PAUSED)

    def resume(self) -> OutreachSequence:
        """Resume a paused sequence.

        Raises:
            DomainError: If the sequence is not PAUSED.
        """
        self._assert_status(SequenceStatus.PAUSED, "resume")
        return replace(self, status=SequenceStatus.ACTIVE)

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def current_step(self) -> SequenceStep | None:
        """Return the current step, or None if the index is out of range."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def is_stoppable(self) -> bool:
        """Return True if the sequence can be stopped."""
        return self.status in (SequenceStatus.ACTIVE, SequenceStatus.PAUSED)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assert_status(self, expected: SequenceStatus, action: str) -> None:
        """Raise DomainError if the current status does not match expected."""
        if self.status is not expected:
            raise DomainError(
                f"Cannot {action} sequence in status {self.status.value}; "
                f"must be {expected.value}"
            )
