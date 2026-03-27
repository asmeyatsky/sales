"""Port for sending emails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from searce_scout.shared_kernel.value_objects import EmailAddress


@dataclass(frozen=True)
class SendResult:
    """Outcome of an email or LinkedIn send operation."""

    success: bool
    message_id: str | None = None
    error: str | None = None


class EmailSenderPort(Protocol):
    """Driven port for sending outreach emails.

    Infrastructure adapters implement this to integrate with email
    delivery services (e.g., SendGrid, SES, SMTP).
    """

    async def send(
        self,
        to: EmailAddress,
        subject: str,
        body: str,
        from_alias: str,
    ) -> SendResult:
        """Send an email to the specified recipient.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body: Email body (HTML or plain text).
            from_alias: The sender alias / display name.

        Returns:
            SendResult indicating success or failure.
        """
        ...
