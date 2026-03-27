"""Port for outreach sequence persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from searce_scout.shared_kernel.types import SequenceId

from searce_scout.outreach.domain.entities.outreach_sequence import OutreachSequence


class SequenceRepositoryPort(Protocol):
    """Driven port for persisting and retrieving OutreachSequence aggregates."""

    async def save(self, sequence: OutreachSequence) -> None:
        """Persist a sequence (insert or update).

        Args:
            sequence: The OutreachSequence aggregate to persist.
        """
        ...

    async def get_by_id(self, sequence_id: SequenceId) -> OutreachSequence | None:
        """Retrieve a sequence by its identifier.

        Args:
            sequence_id: The unique sequence identifier.

        Returns:
            The OutreachSequence if found, or None.
        """
        ...

    async def find_active(self) -> tuple[OutreachSequence, ...]:
        """Find all sequences in ACTIVE status.

        Returns:
            All currently active outreach sequences.
        """
        ...

    async def find_due_for_execution(
        self, now: datetime
    ) -> tuple[OutreachSequence, ...]:
        """Find active sequences whose current step is due for execution.

        Args:
            now: The current datetime used to determine due steps.

        Returns:
            Sequences with steps scheduled at or before `now`.
        """
        ...
