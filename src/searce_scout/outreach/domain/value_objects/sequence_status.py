"""Sequence lifecycle status."""

from enum import Enum


class SequenceStatus(Enum):
    """The lifecycle state of an outreach sequence."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"
