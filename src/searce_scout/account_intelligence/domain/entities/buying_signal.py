"""BuyingSignal entity representing a detected market signal for an account."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from searce_scout.shared_kernel.value_objects import URL

from searce_scout.account_intelligence.domain.value_objects.signal_type import (
    SignalStrength,
    SignalType,
)


@dataclass(frozen=True)
class BuyingSignal:
    signal_id: str
    signal_type: SignalType
    strength: SignalStrength
    description: str
    source_url: URL | None
    detected_at: datetime
