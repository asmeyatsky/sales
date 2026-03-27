"""Port (driven adapter interface) for AI-based analysis of raw research data."""

from __future__ import annotations

from typing import Protocol

from searce_scout.account_intelligence.domain.entities.buying_signal import (
    BuyingSignal,
)
from searce_scout.account_intelligence.domain.value_objects.industry import Industry


class AIAnalyzerPort(Protocol):
    async def extract_signals(
        self, raw_data: str
    ) -> tuple[BuyingSignal, ...]: ...

    async def classify_industry(
        self, company_name: str, description: str
    ) -> Industry: ...
