"""Pure domain tests for ReplyClassificationService.

No mocks — verifies the should_stop / should_pause logic for each
ReplyClassification variant.
"""

from searce_scout.outreach.domain.services.reply_classification_service import (
    ReplyClassificationService,
)
from searce_scout.outreach.domain.value_objects.reply_classification import (
    ReplyClassification,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestShouldStopSequence:
    def test_not_interested_should_stop(self) -> None:
        svc = ReplyClassificationService()
        assert svc.should_stop_sequence(ReplyClassification.NOT_INTERESTED) is True

    def test_positive_should_stop(self) -> None:
        """Positive replies stop the automated sequence to escalate to a human."""
        svc = ReplyClassificationService()
        assert svc.should_stop_sequence(ReplyClassification.POSITIVE) is True

    def test_bounce_should_stop(self) -> None:
        svc = ReplyClassificationService()
        assert svc.should_stop_sequence(ReplyClassification.BOUNCE) is True

    def test_unsubscribe_should_stop(self) -> None:
        svc = ReplyClassificationService()
        assert svc.should_stop_sequence(ReplyClassification.UNSUBSCRIBE) is True

    def test_neutral_should_not_stop_or_pause(self) -> None:
        svc = ReplyClassificationService()
        assert svc.should_stop_sequence(ReplyClassification.NEUTRAL) is False
        assert svc.should_pause_sequence(ReplyClassification.NEUTRAL) is False


class TestShouldPauseSequence:
    def test_ooo_should_pause_not_stop(self) -> None:
        svc = ReplyClassificationService()
        assert svc.should_pause_sequence(ReplyClassification.OOO) is True
        assert svc.should_stop_sequence(ReplyClassification.OOO) is False
