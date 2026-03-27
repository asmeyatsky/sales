"""
TemplateId value object.

Wraps a Google Slides template identifier to distinguish it from
arbitrary strings at the type level.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateId:
    google_slides_id: str
