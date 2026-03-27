"""Step type, step result, and default step ordering."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StepType(Enum):
    """The type of action performed in an outreach sequence step."""

    LINKEDIN_REQUEST = "linkedin_request"
    EMAIL_1 = "email_1"
    LINKEDIN_MESSAGE = "linkedin_message"
    EMAIL_2 = "email_2"
    PHONE_TASK = "phone_task"


@dataclass(frozen=True)
class StepResult:
    """Outcome of executing a sequence step."""

    success: bool
    channel_message_id: str | None = None
    error: str | None = None


# PRD-defined default order for the 5-step outreach sequence
DEFAULT_STEP_ORDER: tuple[StepType, ...] = (
    StepType.LINKEDIN_REQUEST,
    StepType.EMAIL_1,
    StepType.LINKEDIN_MESSAGE,
    StepType.EMAIL_2,
    StepType.PHONE_TASK,
)
