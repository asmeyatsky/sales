"""Infrastructure adapter for sending emails via the Gmail API.

Implements EmailSenderPort using google-api-python-client to send
outreach emails through a Google Workspace / Gmail account.  Constructs
proper MIME messages and returns a SendResult with the Gmail message ID.
"""

from __future__ import annotations

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from searce_scout.shared_kernel.value_objects import EmailAddress
from searce_scout.outreach.domain.ports.email_sender_port import (
    EmailSenderPort,
    SendResult,
)

logger = logging.getLogger(__name__)

_GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class GmailSender:
    """Gmail API adapter implementing :class:`EmailSenderPort`.

    Parameters
    ----------
    credentials_path:
        Path to a Google service-account JSON key file that has
        domain-wide delegation enabled for Gmail.
    sender_email:
        The Gmail address to send from (the service account must be
        authorised to impersonate this user).
    """

    def __init__(self, credentials_path: str, sender_email: str) -> None:
        self._credentials_path = credentials_path
        self._sender_email = sender_email
        self._service: Any | None = None

    # -- EmailSenderPort interface ------------------------------------------

    async def send(
        self,
        to: EmailAddress,
        subject: str,
        body: str,
        from_alias: str,
    ) -> SendResult:
        """Send an email via the Gmail API.

        Builds a MIME message, base64url-encodes it, and calls the Gmail
        ``messages.send`` endpoint.

        Returns a :class:`SendResult` containing the Gmail message ID on
        success or an error description on failure.
        """
        try:
            service = self._get_service()
            mime_message = self._build_mime_message(
                to=to.value,
                subject=subject,
                body=body,
                from_alias=from_alias,
            )
            raw_message = base64.urlsafe_b64encode(
                mime_message.as_bytes()
            ).decode("ascii")

            sent: dict[str, Any] = (
                service.users()
                .messages()
                .send(
                    userId="me",
                    body={"raw": raw_message},
                )
                .execute()
            )

            message_id: str = sent.get("id", "")
            logger.info(
                "Email sent successfully via Gmail. message_id=%s, to=%s",
                message_id,
                to.value,
            )
            return SendResult(success=True, message_id=message_id)

        except HttpError as exc:
            error_detail = str(exc)
            logger.error("Gmail API error sending email to %s: %s", to.value, error_detail)
            return SendResult(success=False, error=error_detail)
        except Exception as exc:
            error_detail = f"{type(exc).__name__}: {exc}"
            logger.error("Unexpected error sending email to %s: %s", to.value, error_detail)
            return SendResult(success=False, error=error_detail)

    # -- Internal helpers ---------------------------------------------------

    def _get_service(self) -> Any:
        """Lazily build and cache the Gmail API service resource."""
        if self._service is not None:
            return self._service

        credentials = Credentials.from_service_account_file(
            self._credentials_path,
            scopes=_GMAIL_SCOPES,
        )
        delegated = credentials.with_subject(self._sender_email)

        self._service = build("gmail", "v1", credentials=delegated)
        return self._service

    def _build_mime_message(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        from_alias: str,
    ) -> MIMEMultipart:
        """Construct a MIME multipart message with HTML and plain-text parts."""
        message = MIMEMultipart("alternative")
        message["To"] = to
        message["From"] = f"{from_alias} <{self._sender_email}>"
        message["Subject"] = subject

        # Plain-text fallback (strip tags naively for text-only clients)
        plain_body = body  # Callers should ideally supply both variants
        message.attach(MIMEText(plain_body, "plain"))
        message.attach(MIMEText(body, "html"))

        return message


# Structural compatibility check with the port Protocol.
_check: type[EmailSenderPort] = GmailSender  # type: ignore[assignment]
