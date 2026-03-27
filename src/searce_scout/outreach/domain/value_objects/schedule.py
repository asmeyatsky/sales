"""Step scheduling value objects with default timing delays."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta


@dataclass(frozen=True)
class StepSchedule:
    """Default delays between outreach sequence steps.

    Each timedelta represents the delay from the previous step's
    completion to the next step's scheduled execution.

    Index 0 = delay before step 1 (immediate),
    Index 1 = delay before step 2 (48 hours), etc.
    """

    default_delays: tuple[timedelta, ...] = field(
        default=(
            timedelta(0),
            timedelta(hours=48),
            timedelta(hours=72),
            timedelta(hours=96),
            timedelta(hours=120),
        )
    )
