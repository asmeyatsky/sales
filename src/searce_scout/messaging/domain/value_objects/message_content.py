"""Message content value objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MessageStatus(Enum):
    """Lifecycle status of a generated message."""

    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    FAILED = "failed"


@dataclass(frozen=True)
class GeneratedMessage:
    """Output from the AI message generator."""

    subject: str | None
    body: str
    call_to_action: str
    quality_score: float
