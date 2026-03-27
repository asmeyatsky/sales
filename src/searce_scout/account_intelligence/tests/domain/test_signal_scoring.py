"""Pure domain tests for BuyingSignalScoringService.

No mocks — exercises the weight * multiplier formula, empty-signal
edge case, and the 1.0 cap.
"""

from datetime import datetime, UTC

from searce_scout.account_intelligence.domain.entities.buying_signal import (
    BuyingSignal,
)
from searce_scout.account_intelligence.domain.services.signal_scoring import (
    BuyingSignalScoringService,
)
from searce_scout.account_intelligence.domain.value_objects.signal_type import (
    SignalStrength,
    SignalType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _signal(
    signal_type: SignalType,
    strength: SignalStrength,
) -> BuyingSignal:
    return BuyingSignal(
        signal_id="sig-test",
        signal_type=signal_type,
        strength=strength,
        description="test",
        source_url=None,
        detected_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestScoreSignals:
    def test_score_signals_empty_returns_zero(self) -> None:
        assert BuyingSignalScoringService.score_signals(()) == 0.0

    def test_score_signals_single_critical_new_executive(self) -> None:
        """NEW_EXECUTIVE weight=0.3, CRITICAL multiplier=1.0 => 0.3."""
        signals = (_signal(SignalType.NEW_EXECUTIVE, SignalStrength.CRITICAL),)
        score = BuyingSignalScoringService.score_signals(signals)
        assert score == 0.3

    def test_score_signals_multiple_weighted_correctly(self) -> None:
        """NEW_EXECUTIVE STRONG (0.3*0.75=0.225) +
        HIRING_SPREE MODERATE (0.2*0.5=0.1) = 0.325."""
        signals = (
            _signal(SignalType.NEW_EXECUTIVE, SignalStrength.STRONG),
            _signal(SignalType.HIRING_SPREE, SignalStrength.MODERATE),
        )
        score = BuyingSignalScoringService.score_signals(signals)
        assert abs(score - 0.325) < 1e-9

    def test_score_signals_capped_at_one(self) -> None:
        """Stacking many CRITICAL signals must cap the result at 1.0."""
        signals = tuple(
            _signal(st, SignalStrength.CRITICAL) for st in SignalType
        )
        score = BuyingSignalScoringService.score_signals(signals)
        assert score == 1.0
