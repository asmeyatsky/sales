"""Port for LinkedIn messaging operations."""

from __future__ import annotations

from typing import Protocol

from searce_scout.shared_kernel.value_objects import URL

from searce_scout.outreach.domain.ports.email_sender_port import SendResult


class LinkedInMessengerPort(Protocol):
    """Driven port for LinkedIn outreach actions.

    Infrastructure adapters implement this to integrate with LinkedIn
    automation tools or APIs.
    """

    async def send_connection_request(
        self,
        profile_url: URL,
        note: str,
    ) -> SendResult:
        """Send a LinkedIn connection request with a personalized note.

        Args:
            profile_url: The target LinkedIn profile URL.
            note: The connection request note (max ~300 chars).

        Returns:
            SendResult indicating success or failure.
        """
        ...

    async def send_message(
        self,
        profile_url: URL,
        body: str,
    ) -> SendResult:
        """Send a LinkedIn direct message to a connected profile.

        Args:
            profile_url: The target LinkedIn profile URL.
            body: The message body.

        Returns:
            SendResult indicating success or failure.
        """
        ...
