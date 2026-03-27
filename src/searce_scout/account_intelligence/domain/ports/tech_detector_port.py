"""Port (driven adapter interface) for technology stack detection."""

from __future__ import annotations

from typing import Protocol

from searce_scout.account_intelligence.domain.value_objects.tech_stack import TechStack


class TechDetectorPort(Protocol):
    async def detect_tech_stack(self, domain: str) -> TechStack: ...
