"""Query and handler for listing all active outreach sequences."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.outreach.application.dtos.outreach_dtos import OutreachSequenceDTO
from searce_scout.outreach.domain.ports.sequence_repository_port import (
    SequenceRepositoryPort,
)


@dataclass(frozen=True)
class ListActiveSequencesQuery:
    pass


class ListActiveSequencesHandler:
    """Lists all outreach sequences currently in ACTIVE status."""

    def __init__(self, sequence_repository: SequenceRepositoryPort) -> None:
        self._sequence_repository = sequence_repository

    async def execute(
        self, query: ListActiveSequencesQuery
    ) -> list[OutreachSequenceDTO]:
        """Retrieve all active sequences.

        Args:
            query: The query (no parameters).

        Returns:
            A list of OutreachSequenceDTOs for all active sequences.
        """
        sequences = await self._sequence_repository.find_active()
        return [OutreachSequenceDTO.from_domain(seq) for seq in sequences]
