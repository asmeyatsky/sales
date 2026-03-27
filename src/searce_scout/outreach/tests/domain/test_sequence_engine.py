"""Pure domain tests for SequenceEngineService.

No mocks — verifies default sequence construction and business-hours
scheduling logic.
"""

from datetime import datetime, timedelta

from searce_scout.shared_kernel.types import AccountId, MessageId, StakeholderId

from searce_scout.outreach.domain.entities.sequence_step import SequenceStep
from searce_scout.outreach.domain.services.sequence_engine import SequenceEngineService
from searce_scout.outreach.domain.value_objects.sequence_status import SequenceStatus
from searce_scout.outreach.domain.value_objects.step_type import (
    DEFAULT_STEP_ORDER,
    StepType,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBuildDefaultSequence:
    def test_build_default_sequence_creates_five_steps(self) -> None:
        engine = SequenceEngineService()
        message_ids = {st: MessageId(f"msg-{st.value}") for st in StepType}

        seq = engine.build_default_sequence(
            account_id=AccountId("acct-001"),
            stakeholder_id=StakeholderId("stk-001"),
            message_ids=message_ids,
        )

        assert len(seq.steps) == 5
        assert seq.status is SequenceStatus.DRAFT
        assert seq.current_step_index == 0

    def test_build_default_sequence_correct_step_types_in_order(self) -> None:
        engine = SequenceEngineService()
        message_ids = {st: MessageId(f"msg-{st.value}") for st in StepType}

        seq = engine.build_default_sequence(
            account_id=AccountId("acct-001"),
            stakeholder_id=StakeholderId("stk-001"),
            message_ids=message_ids,
        )

        actual_types = tuple(step.step_type for step in seq.steps)
        assert actual_types == DEFAULT_STEP_ORDER


class TestCalculateNextExecution:
    def test_calculate_next_execution_skips_weekends(self) -> None:
        engine = SequenceEngineService()

        # Friday 16:00 + 48h delay => Sunday 16:00 -> should be pushed to Monday 09:00
        # 2026-03-27 is a Friday
        friday = datetime(2026, 3, 27, 16, 0)
        step = SequenceStep(
            step_number=2,
            step_type=StepType.EMAIL_1,
            message_id=None,
            scheduled_at=None,
            executed_at=None,
            result=None,
            delay_from_previous=timedelta(hours=48),
        )

        result = engine.calculate_next_execution_time(step, friday)

        # Sunday 16:00 -> should be adjusted to Monday 09:00
        assert result.weekday() == 0  # Monday
        assert result.hour == 9
        assert result.minute == 0

    def test_calculate_next_execution_within_business_hours(self) -> None:
        engine = SequenceEngineService()

        # Wednesday 10:00 + 2h delay = Wednesday 12:00 (within hours)
        wednesday = datetime(2026, 3, 25, 10, 0)
        step = SequenceStep(
            step_number=2,
            step_type=StepType.EMAIL_1,
            message_id=None,
            scheduled_at=None,
            executed_at=None,
            result=None,
            delay_from_previous=timedelta(hours=2),
        )

        result = engine.calculate_next_execution_time(step, wednesday)

        assert result == datetime(2026, 3, 25, 12, 0)

    def test_calculate_next_execution_after_hours_snaps_to_next_day(self) -> None:
        engine = SequenceEngineService()

        # Wednesday 15:00 + 4h delay = Wednesday 19:00 (after 17:00)
        wednesday = datetime(2026, 3, 25, 15, 0)
        step = SequenceStep(
            step_number=2,
            step_type=StepType.EMAIL_1,
            message_id=None,
            scheduled_at=None,
            executed_at=None,
            result=None,
            delay_from_previous=timedelta(hours=4),
        )

        result = engine.calculate_next_execution_time(step, wednesday)

        # Should snap to Thursday 09:00
        assert result == datetime(2026, 3, 26, 9, 0, 0)
