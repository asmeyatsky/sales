"""Port (driven adapter interface) for job board scraping."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from searce_scout.shared_kernel.value_objects import URL


@dataclass(frozen=True)
class JobPosting:
    title: str
    location: str
    department: str
    posted_at: datetime
    url: URL


class JobBoardScraperPort(Protocol):
    async def scrape_jobs(
        self, company_name: str
    ) -> tuple[JobPosting, ...]: ...
