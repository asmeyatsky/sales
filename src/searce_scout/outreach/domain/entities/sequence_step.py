"""Sequence step entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from searce_scout.shared_kernel.types import MessageId

from searce_scout.outreach.domain.value_objects.step_type import StepResult, StepType


@dataclass(frozen=True)
class SequenceStep:
    """A single step within an outreach sequence.

    Each step represents one touchpoint in the multi-channel outreach
    cadence (e.g., LinkedIn request, email, phone task).
    """

    step_number: int
    step_type: StepType
    message_id: MessageId | None
    scheduled_at: datetime | None
    executed_at: datetime | None
    result: StepResult | None
    delay_from_previous: timedelta
