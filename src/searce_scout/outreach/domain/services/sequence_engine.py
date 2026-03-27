"""Domain service for building and scheduling outreach sequences."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from searce_scout.shared_kernel.types import AccountId, MessageId, SequenceId, StakeholderId

from searce_scout.outreach.domain.entities.outreach_sequence import OutreachSequence
from searce_scout.outreach.domain.entities.sequence_step import SequenceStep
from searce_scout.outreach.domain.value_objects.schedule import StepSchedule
from searce_scout.outreach.domain.value_objects.sequence_status import SequenceStatus
from searce_scout.outreach.domain.value_objects.step_type import (
    DEFAULT_STEP_ORDER,
    StepType,
)


class SequenceEngineService:
    """Builds default outreach sequences and calculates execution timing.

    This is a pure domain service with no infrastructure dependencies.
    """

    def build_default_sequence(
        self,
        account_id: AccountId,
        stakeholder_id: StakeholderId,
        message_ids: dict[StepType, MessageId],
    ) -> OutreachSequence:
        """Construct the standard 5-step outreach sequence.

        Uses DEFAULT_STEP_ORDER and StepSchedule default delays to
        assemble an OutreachSequence in DRAFT status.

        Args:
            account_id: The account this sequence belongs to.
            stakeholder_id: The target stakeholder.
            message_ids: Mapping from StepType to the pre-generated
                MessageId for that step.

        Returns:
            A new OutreachSequence in DRAFT status with all 5 steps.
        """
        schedule = StepSchedule()
        steps: list[SequenceStep] = []

        for index, step_type in enumerate(DEFAULT_STEP_ORDER):
            delay = (
                schedule.default_delays[index]
                if index < len(schedule.default_delays)
                else timedelta(hours=120)
            )
            step = SequenceStep(
                step_number=index + 1,
                step_type=step_type,
                message_id=message_ids.get(step_type),
                scheduled_at=None,
                executed_at=None,
                result=None,
                delay_from_previous=delay,
            )
            steps.append(step)

        return OutreachSequence(
            sequence_id=SequenceId(str(uuid4())),
            account_id=account_id,
            stakeholder_id=stakeholder_id,
            status=SequenceStatus.DRAFT,
            steps=tuple(steps),
            current_step_index=0,
            started_at=None,
            stopped_at=None,
            stop_reason=None,
        )

    def calculate_next_execution_time(
        self,
        step: SequenceStep,
        previous_completed: datetime,
        business_hours_start: int = 9,
        business_hours_end: int = 17,
    ) -> datetime:
        """Calculate when the next step should execute.

        Applies the step's delay from the previous completion time,
        then adjusts forward to fall within business hours (Mon-Fri,
        start-end in the same timezone as previous_completed).

        Args:
            step: The step whose execution time to calculate.
            previous_completed: When the preceding step completed.
            business_hours_start: Start of business hours (hour, 0-23).
            business_hours_end: End of business hours (hour, 0-23).

        Returns:
            The adjusted datetime for execution within business hours.
        """
        candidate = previous_completed + step.delay_from_previous
        return self._adjust_to_business_hours(
            candidate, business_hours_start, business_hours_end
        )

    @staticmethod
    def _adjust_to_business_hours(
        dt: datetime,
        start_hour: int,
        end_hour: int,
    ) -> datetime:
        """Move a datetime forward until it falls within business hours.

        Skips weekends (Saturday=5, Sunday=6) and times outside the
        specified hour range.
        """
        # Move past weekends first
        while dt.weekday() >= 5:  # Saturday or Sunday
            dt = dt.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            dt += timedelta(days=1)

        # If before business hours, snap to start
        if dt.hour < start_hour:
            dt = dt.replace(hour=start_hour, minute=0, second=0, microsecond=0)

        # If after business hours, move to next business day start
        if dt.hour >= end_hour:
            dt += timedelta(days=1)
            dt = dt.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            # Skip weekend if the next day lands on one
            while dt.weekday() >= 5:
                dt += timedelta(days=1)

        return dt
