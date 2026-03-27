"""
AIContentGeneratorPort — output port for AI-driven content generation.
"""

from __future__ import annotations

from typing import Protocol

from searce_scout.presentation_gen.domain.value_objects.deck_content import (
    GapAnalysis,
    HookContent,
)


class AIContentGeneratorPort(Protocol):
    async def generate_hook(
        self, account_data: str, signals: str
    ) -> HookContent: ...

    async def generate_gap_analysis(
        self, tech_stack: str, offering: str
    ) -> GapAnalysis: ...
