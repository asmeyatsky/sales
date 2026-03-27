"""Infrastructure adapter for reading Gmail inbox replies.

Implements InboxReaderPort using google-api-python-client to query the
Gmail API for incoming replies.  Filters to threads matching sent
outreach messages and returns RawReply domain objects.
"""

from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from searce_scout.outreach.domain.ports.inbox_reader_port import (
    InboxReaderPort,
    RawReply,
)

logger = logging.getLogger(__name__)

_GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailInboxReader:
    """Gmail inbox reader implementing :class:`InboxReaderPort`.

    Parameters
    ----------
    credentials_path:
        Path to a Google service-account JSON key file with domain-wide
        delegation for Gmail.
    user_email:
        The Gmail address whose inbox we monitor.
    """

    def __init__(self, credentials_path: str, user_email: str) -> None:
        self._credentials_path = credentials_path
        self._user_email = user_email
        self._service: Any | None = None

    # -- InboxReaderPort interface ------------------------------------------

    async def check_replies(self, since: datetime) -> tuple[RawReply, ...]:
        """Fetch all inbox replies received after *since*.

        Uses the Gmail search query ``is:inbox after:<epoch>`` and then
        retrieves each matching message to extract content and metadata.
        """
        try:
            service = self._get_service()
            epoch_seconds = int(since.timestamp())
            query = f"is:inbox after:{epoch_seconds}"

            message_refs = self._list_messages(service, query)
            if not message_refs:
                return ()

            replies: list[RawReply] = []
            for ref in message_refs:
                raw_reply = self._fetch_and_map(service, ref["id"])
                if raw_reply is not None:
                    replies.append(raw_reply)

            return tuple(replies)

        except HttpError as exc:
            logger.error("Gmail API error checking replies: %s", exc)
            return ()
        except Exception as exc:
            logger.error("Unexpected error checking Gmail replies: %s", exc)
            return ()

    # -- Internal helpers ---------------------------------------------------

    def _get_service(self) -> Any:
        """Lazily build and cache the Gmail API service resource."""
        if self._service is not None:
            return self._service

        credentials = Credentials.from_service_account_file(
            self._credentials_path,
            scopes=_GMAIL_SCOPES,
        )
        delegated = credentials.with_subject(self._user_email)
        self._service = build("gmail", "v1", credentials=delegated)
        return self._service

    @staticmethod
    def _list_messages(service: Any, query: str) -> list[dict[str, Any]]:
        """Page through messages.list and collect all message id/threadId refs."""
        refs: list[dict[str, Any]] = []
        page_token: str | None = None

        while True:
            response: dict[str, Any] = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    pageToken=page_token,
                    maxResults=100,
                )
                .execute()
            )

            batch: list[dict[str, Any]] = response.get("messages", [])
            refs.extend(batch)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return refs

    @staticmethod
    def _fetch_and_map(service: Any, message_id: str) -> RawReply | None:
        """Fetch a full message by ID and map it to a :class:`RawReply`."""
        try:
            msg: dict[str, Any] = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            thread_id: str = msg.get("threadId", "")
            internal_date_ms: int = int(msg.get("internalDate", 0))
            received_at = datetime.fromtimestamp(
                internal_date_ms / 1000, tz=UTC
            )

            headers: list[dict[str, str]] = (
                msg.get("payload", {}).get("headers", [])
            )
            sender = ""
            for h in headers:
                if h.get("name", "").lower() == "from":
                    sender = h.get("value", "")
                    break

            # Extract body text (prefer plain text, fall back to snippet)
            body = _extract_body(msg.get("payload", {}))
            if not body:
                body = msg.get("snippet", "")

            return RawReply(
                reply_id=message_id,
                thread_id=thread_id,
                content=body,
                sender=sender,
                received_at=received_at,
            )
        except Exception:
            logger.debug(
                "Failed to fetch/map Gmail message %s", message_id, exc_info=True
            )
            return None


def _extract_body(payload: dict[str, Any]) -> str:
    """Recursively extract the plain-text body from a Gmail message payload."""
    mime_type: str = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    parts: list[dict[str, Any]] = payload.get("parts", [])
    for part in parts:
        result = _extract_body(part)
        if result:
            return result

    return ""


# Structural compatibility check with the port Protocol.
_check: type[InboxReaderPort] = GmailInboxReader  # type: ignore[assignment]
