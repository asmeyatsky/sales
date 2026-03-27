"""Port (driven adapter interface) for LinkedIn profile search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from searce_scout.shared_kernel.value_objects import PersonName, URL


@dataclass(frozen=True)
class LinkedInProfile:
    name: PersonName
    title: str
    linkedin_url: URL
    company: str


class LinkedInPort(Protocol):
    async def search_decision_makers(
        self, company_name: str, titles: tuple[str, ...]
    ) -> tuple[LinkedInProfile, ...]: ...
