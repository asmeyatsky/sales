"""Port for message persistence."""

from __future__ import annotations

from typing import Protocol

from searce_scout.shared_kernel.types import MessageId, StakeholderId

from searce_scout.messaging.domain.entities.message import Message


class MessageRepositoryPort(Protocol):
    """Driven port for persisting and retrieving Message aggregates."""

    async def save(self, message: Message) -> None:
        """Persist a message (insert or update).

        Args:
            message: The Message aggregate to persist.
        """
        ...

    async def get_by_id(self, message_id: MessageId) -> Message | None:
        """Retrieve a message by its identifier.

        Args:
            message_id: The unique message identifier.

        Returns:
            The Message if found, or None.
        """
        ...

    async def find_by_stakeholder(
        self, stakeholder_id: StakeholderId
    ) -> tuple[Message, ...]:
        """Find all messages for a given stakeholder.

        Args:
            stakeholder_id: The stakeholder to query by.

        Returns:
            All messages associated with the stakeholder.
        """
        ...
