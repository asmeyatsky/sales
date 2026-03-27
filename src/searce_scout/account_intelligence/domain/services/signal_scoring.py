"""Buying-signal scoring domain service."""

from __future__ import annotations

from searce_scout.account_intelligence.domain.entities.buying_signal import (
    BuyingSignal,
)
from searce_scout.account_intelligence.domain.value_objects.signal_type import (
    SignalStrength,
    SignalType,
)


_SIGNAL_WEIGHTS: dict[SignalType, float] = {
    SignalType.NEW_EXECUTIVE: 0.3,
    SignalType.HIRING_SPREE: 0.2,
    SignalType.DIGITAL_TRANSFORMATION_GOAL: 0.25,
    SignalType.CLOUD_MIGRATION_MENTION: 0.15,
    SignalType.FUNDING_ROUND: 0.1,
    SignalType.TECH_DEBT_COMPLAINT: 0.15,
    SignalType.VENDOR_CONTRACT_EXPIRY: 0.2,
}

_STRENGTH_MULTIPLIERS: dict[SignalStrength, float] = {
    SignalStrength.WEAK: 0.25,
    SignalStrength.MODERATE: 0.5,
    SignalStrength.STRONG: 0.75,
    SignalStrength.CRITICAL: 1.0,
}


class BuyingSignalScoringService:
    """Stateless domain service that scores a collection of buying signals."""

    @staticmethod
    def score_signals(signals: tuple[BuyingSignal, ...]) -> float:
        """Compute a composite score for the given signals.

        Each signal contributes: weight(signal_type) * multiplier(strength).
        The total is capped at 1.0.
        """
        total = 0.0
        for signal in signals:
            weight = _SIGNAL_WEIGHTS.get(signal.signal_type, 0.0)
            multiplier = _STRENGTH_MULTIPLIERS.get(signal.strength, 0.0)
            total += weight * multiplier
        return min(total, 1.0)
