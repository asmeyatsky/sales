"""Port (driven adapter interface) for news article scraping."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from searce_scout.shared_kernel.value_objects import URL


@dataclass(frozen=True)
class NewsArticle:
    title: str
    url: URL
    published_at: datetime
    summary: str


class NewsScraperPort(Protocol):
    async def scrape_news(
        self, company_name: str, days_back: int = 90
    ) -> tuple[NewsArticle, ...]: ...
