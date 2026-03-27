"""Industry and company size value objects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Industry:
    name: str
    vertical: str


class CompanySize(Enum):
    STARTUP = "STARTUP"
    SMB = "SMB"
    MID_MARKET = "MID_MARKET"
    ENTERPRISE = "ENTERPRISE"
