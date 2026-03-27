"""Relevance scoring and persona matching value objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RelevanceScore:
    score: float  # 0.0 - 1.0
    factors: tuple[str, ...]


@dataclass(frozen=True)
class PersonaMatch:
    searce_offering: str
    target_persona: str
    pain_points: tuple[str, ...]
    confidence: float
