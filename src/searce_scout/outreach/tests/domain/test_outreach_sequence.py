"""Pure domain tests for the OutreachSequence aggregate root (state machine).

No mocks — this is the most critical test file. Exercises every state
transition, guard clause, and query method on the frozen aggregate.
"""

import pytest
from datetime import timedelta

from searce_scout.shared_kernel.errors import DomainError
from searce_scout.shared_kernel.types import AccountId, SequenceId, StakeholderId

from searce_scout.outreach.domain.entities.outreach_sequence import OutreachSequence
from searce_scout.outreach.domain.entities.sequence_step import SequenceStep
from searce_scout.outreach.domain.events.outreach_events import (
    SequenceCompletedEvent,
    SequenceStartedEvent,
    SequenceStoppedEvent,
    StepExecutedEvent,
)
from searce_scout.outreach.domain.value_objects.sequence_status import SequenceStatus
from searce_scout.outreach.domain.value_objects.step_type import (
    StepResult,
    StepType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_step(step_number: int, step_type: StepType) -> SequenceStep:
    return SequenceStep(
        step_number=step_number,
        step_type=step_type,
        message_id=None,
        scheduled_at=None,
        executed_at=None,
        result=None,
        delay_from_previous=timedelta(hours=48),
    )


def _make_sequence(
    status: SequenceStatus = SequenceStatus.DRAFT,
    num_steps: int = 3,
    current_step_index: int = 0,
) -> OutreachSequence:
    step_types = [StepType.LINKEDIN_REQUEST, StepType.EMAIL_1, StepType.LINKEDIN_MESSAGE,
                  StepType.EMAIL_2, StepType.PHONE_TASK]
    steps = tuple(_make_step(i + 1, step_types[i % len(step_types)]) for i in range(num_steps))
    return OutreachSequence(
        sequence_id=SequenceId("seq-001"),
        account_id=AccountId("acct-001"),
        stakeholder_id=StakeholderId("stk-001"),
        status=status,
        steps=steps,
        current_step_index=current_step_index,
        started_at=None,
        stopped_at=None,
        stop_reason=None,
        domain_events=(),
    )


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

class TestStart:
    def test_start_transitions_draft_to_active(self) -> None:
        seq = _make_sequence(SequenceStatus.DRAFT)
        started = seq.start()

        assert started.status is SequenceStatus.ACTIVE
        assert started.started_at is not None
        assert len(started.domain_events) == 1
        assert isinstance(started.domain_events[0], SequenceStartedEvent)

    def test_start_from_active_raises_domain_error(self) -> None:
        seq = _make_sequence(SequenceStatus.ACTIVE)
        with pytest.raises(DomainError, match="Cannot start"):
            seq.start()


# ---------------------------------------------------------------------------
# Advance
# ---------------------------------------------------------------------------

class TestAdvance:
    def test_advance_to_next_step_increments_index(self) -> None:
        seq = _make_sequence(SequenceStatus.ACTIVE, num_steps=3, current_step_index=0)
        advanced = seq.advance_to_next_step()

        assert advanced.current_step_index == 1
        assert advanced.status is SequenceStatus.ACTIVE

    def test_advance_past_last_step_completes_sequence(self) -> None:
        seq = _make_sequence(SequenceStatus.ACTIVE, num_steps=3, current_step_index=2)
        completed = seq.advance_to_next_step()

        assert completed.status is SequenceStatus.COMPLETED
        assert completed.current_step_index == 3
        assert any(isinstance(e, SequenceCompletedEvent) for e in completed.domain_events)


# ---------------------------------------------------------------------------
# Complete current step
# ---------------------------------------------------------------------------

class TestCompleteCurrentStep:
    def test_complete_current_step_sets_result(self) -> None:
        seq = _make_sequence(SequenceStatus.ACTIVE, num_steps=3, current_step_index=0)
        result = StepResult(success=True, channel_message_id="ext-123")
        updated = seq.complete_current_step(result)

        completed_step = updated.steps[0]
        assert completed_step.result is not None
        assert completed_step.result.success is True
        assert completed_step.result.channel_message_id == "ext-123"
        assert completed_step.executed_at is not None
        assert any(isinstance(e, StepExecutedEvent) for e in updated.domain_events)


# ---------------------------------------------------------------------------
# Stop
# ---------------------------------------------------------------------------

class TestStop:
    def test_stop_from_active_transitions_to_stopped(self) -> None:
        seq = _make_sequence(SequenceStatus.ACTIVE)
        stopped = seq.stop("Not interested reply")

        assert stopped.status is SequenceStatus.STOPPED
        assert stopped.stop_reason == "Not interested reply"
        assert stopped.stopped_at is not None
        assert any(isinstance(e, SequenceStoppedEvent) for e in stopped.domain_events)

    def test_stop_from_paused_transitions_to_stopped(self) -> None:
        seq = _make_sequence(SequenceStatus.PAUSED)
        stopped = seq.stop("Manual stop")
        assert stopped.status is SequenceStatus.STOPPED

    def test_stop_from_completed_raises_domain_error(self) -> None:
        seq = _make_sequence(SequenceStatus.COMPLETED)
        with pytest.raises(DomainError, match="Cannot stop"):
            seq.stop("Too late")


# ---------------------------------------------------------------------------
# Pause
# ---------------------------------------------------------------------------

class TestPause:
    def test_pause_from_active_transitions_to_paused(self) -> None:
        seq = _make_sequence(SequenceStatus.ACTIVE)
        paused = seq.pause()
        assert paused.status is SequenceStatus.PAUSED

    def test_pause_from_draft_raises_domain_error(self) -> None:
        seq = _make_sequence(SequenceStatus.DRAFT)
        with pytest.raises(DomainError, match="Cannot pause"):
            seq.pause()


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------

class TestResume:
    def test_resume_from_paused_transitions_to_active(self) -> None:
        seq = _make_sequence(SequenceStatus.PAUSED)
        resumed = seq.resume()
        assert resumed.status is SequenceStatus.ACTIVE


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

class TestCurrentStep:
    def test_current_step_returns_correct_step(self) -> None:
        seq = _make_sequence(SequenceStatus.ACTIVE, num_steps=3, current_step_index=1)
        step = seq.current_step()
        assert step is not None
        assert step.step_number == 2  # 0-indexed steps but step_number is 1-based

    def test_current_step_returns_none_when_completed(self) -> None:
        seq = _make_sequence(SequenceStatus.COMPLETED, num_steps=3, current_step_index=3)
        assert seq.current_step() is None
