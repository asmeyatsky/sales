"""Reply classification value object."""

from enum import Enum


class ReplyClassification(Enum):
    """Classification of a stakeholder's reply to an outreach message."""

    OOO = "ooo"
    NOT_INTERESTED = "not_interested"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    UNSUBSCRIBE = "unsubscribe"
    BOUNCE = "bounce"
