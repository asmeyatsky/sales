"""Query and handler for retrieving a sequence's current status."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.types import SequenceId

from searce_scout.outreach.application.dtos.outreach_dtos import OutreachSequenceDTO
from searce_scout.outreach.domain.ports.sequence_repository_port import (
    SequenceRepositoryPort,
)


@dataclass(frozen=True)
class GetSequenceStatusQuery:
    sequence_id: str


class GetSequenceStatusHandler:
    """Retrieves a sequence and returns it as a DTO."""

    def __init__(self, sequence_repository: SequenceRepositoryPort) -> None:
        self._sequence_repository = sequence_repository

    async def execute(
        self, query: GetSequenceStatusQuery
    ) -> OutreachSequenceDTO | None:
        """Fetch a sequence by its identifier.

        Args:
            query: The query containing the sequence ID.

        Returns:
            An OutreachSequenceDTO if found, or None.
        """
        sequence = await self._sequence_repository.get_by_id(
            SequenceId(query.sequence_id)
        )
        if sequence is None:
            return None
        return OutreachSequenceDTO.from_domain(sequence)
