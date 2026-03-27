"""Port for reading incoming replies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class RawReply:
    """An unprocessed incoming reply from a stakeholder."""

    reply_id: str
    thread_id: str
    content: str
    sender: str
    received_at: datetime


class InboxReaderPort(Protocol):
    """Driven port for polling inbound replies.

    Infrastructure adapters implement this to read from email inboxes,
    LinkedIn message streams, or other channels.
    """

    async def check_replies(self, since: datetime) -> tuple[RawReply, ...]:
        """Fetch all replies received since the given timestamp.

        Args:
            since: Only return replies received after this datetime.

        Returns:
            Tuple of raw, unclassified replies.
        """
        ...
