"""Filing data value object representing SEC 10-K filing extracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FilingData:
    fiscal_year: int
    revenue: float | None
    it_spend_mentions: tuple[str, ...]
    digital_transformation_mentions: tuple[str, ...]
    cloud_mentions: tuple[str, ...]
