"""Job title value object with raw and normalized forms."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class JobTitle:
    raw_title: str
    normalized_title: str
