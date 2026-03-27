"""Query and handler for retrieving a single message by ID."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.types import MessageId

from searce_scout.messaging.application.dtos.message_dtos import MessageDTO
from searce_scout.messaging.domain.ports.message_repository_port import (
    MessageRepositoryPort,
)


@dataclass(frozen=True)
class GetMessageQuery:
    message_id: str


class GetMessageHandler:
    """Retrieves a message and returns it as a DTO."""

    def __init__(self, message_repository: MessageRepositoryPort) -> None:
        self._message_repository = message_repository

    async def execute(self, query: GetMessageQuery) -> MessageDTO | None:
        """Fetch a message by its identifier.

        Args:
            query: The query containing the message ID.

        Returns:
            A MessageDTO if found, or None.
        """
        message = await self._message_repository.get_by_id(
            MessageId(query.message_id)
        )
        if message is None:
            return None
        return MessageDTO.from_domain(message)
