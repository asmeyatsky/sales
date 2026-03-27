"""
Deck content value objects.

Immutable data structures representing the content building blocks
used to compose presentation slides.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HookContent:
    headline: str
    key_insight: str
    supporting_data: str


@dataclass(frozen=True)
class GapAnalysis:
    current_state: str
    future_state: str
    cost_of_inaction: str


@dataclass(frozen=True)
class CaseStudyReference:
    title: str
    industry: str
    outcome_summary: str
    metric: str
