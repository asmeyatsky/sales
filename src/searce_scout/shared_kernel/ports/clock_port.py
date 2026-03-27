"""Clock port for testable time access."""

from datetime import UTC, datetime
from typing import Protocol


class ClockPort(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """Production clock using real system time."""

    def now(self) -> datetime:
        return datetime.now(UTC)
