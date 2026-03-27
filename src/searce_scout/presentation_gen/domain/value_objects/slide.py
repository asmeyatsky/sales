"""
Slide value object and SlideType enumeration.

A Slide represents one page in a presentation deck with its content
and ordering metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique


@unique
class SlideType(Enum):
    TITLE = "TITLE"
    HOOK = "HOOK"
    GAP_CURRENT_STATE = "GAP_CURRENT_STATE"
    GAP_FUTURE_STATE = "GAP_FUTURE_STATE"
    SOCIAL_PROOF = "SOCIAL_PROOF"
    SEARCE_OFFERING = "SEARCE_OFFERING"
    CALL_TO_ACTION = "CALL_TO_ACTION"


@dataclass(frozen=True)
class Slide:
    slide_type: SlideType
    title: str
    body: str
    speaker_notes: str
    order: int
