"""Inbox event entity for classified replies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from searce_scout.shared_kernel.types import SequenceId

from searce_scout.outreach.domain.value_objects.reply_classification import (
    ReplyClassification,
)


@dataclass(frozen=True)
class InboxEvent:
    """A classified reply received from a stakeholder.

    Represents the result of classifying an incoming message that
    is associated with an active outreach sequence.
    """

    event_id: str
    sequence_id: SequenceId
    raw_content: str
    classification: ReplyClassification
    classified_at: datetime
    confidence: float
