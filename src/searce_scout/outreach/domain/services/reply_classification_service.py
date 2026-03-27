"""Domain service for acting on reply classifications."""

from __future__ import annotations

from searce_scout.outreach.domain.value_objects.reply_classification import (
    ReplyClassification,
)


class ReplyClassificationService:
    """Determines sequence actions based on reply classification.

    Business rules:
    - OOO: pause (do not stop)
    - NOT_INTERESTED / UNSUBSCRIBE / BOUNCE: stop
    - POSITIVE: stop (escalate to sales)
    - NEUTRAL: continue sequence
    """

    _STOP_CLASSIFICATIONS: frozenset[ReplyClassification] = frozenset(
        {
            ReplyClassification.NOT_INTERESTED,
            ReplyClassification.UNSUBSCRIBE,
            ReplyClassification.BOUNCE,
            ReplyClassification.POSITIVE,
        }
    )

    _PAUSE_CLASSIFICATIONS: frozenset[ReplyClassification] = frozenset(
        {
            ReplyClassification.OOO,
        }
    )

    def should_stop_sequence(self, classification: ReplyClassification) -> bool:
        """Return True if this classification warrants stopping the sequence.

        POSITIVE replies also return True because they should be escalated
        to a human sales rep.
        """
        return classification in self._STOP_CLASSIFICATIONS

    def should_pause_sequence(self, classification: ReplyClassification) -> bool:
        """Return True if this classification warrants pausing the sequence.

        Only OOO (out-of-office) replies trigger a pause.
        """
        return classification in self._PAUSE_CLASSIFICATIONS
