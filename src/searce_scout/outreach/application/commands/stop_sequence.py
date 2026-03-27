"""Command and handler for stopping an outreach sequence."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.errors import DomainError
from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import SequenceId

from searce_scout.outreach.application.dtos.outreach_dtos import OutreachSequenceDTO
from searce_scout.outreach.domain.ports.sequence_repository_port import (
    SequenceRepositoryPort,
)


@dataclass(frozen=True)
class StopSequenceCommand:
    sequence_id: str
    reason: str


class StopSequenceHandler:
    """Stops an outreach sequence with a given reason."""

    def __init__(
        self,
        sequence_repository: SequenceRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._sequence_repository = sequence_repository
        self._event_bus = event_bus

    async def execute(self, cmd: StopSequenceCommand) -> OutreachSequenceDTO:
        """Load, stop, persist, and publish the sequence.

        Args:
            cmd: The command containing the sequence ID and stop reason.

        Returns:
            An OutreachSequenceDTO reflecting the stopped sequence.

        Raises:
            DomainError: If the sequence is not found or cannot be stopped.
        """
        sequence = await self._sequence_repository.get_by_id(
            SequenceId(cmd.sequence_id)
        )
        if sequence is None:
            raise DomainError(f"Sequence not found: {cmd.sequence_id}")

        sequence = sequence.stop(cmd.reason)

        await self._sequence_repository.save(sequence)
        if sequence.domain_events:
            await self._event_bus.publish(sequence.domain_events)

        return OutreachSequenceDTO.from_domain(sequence)
