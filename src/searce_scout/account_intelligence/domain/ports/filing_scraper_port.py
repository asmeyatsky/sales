"""Port (driven adapter interface) for SEC 10-K filing scraping."""

from __future__ import annotations

from typing import Protocol

from searce_scout.account_intelligence.domain.value_objects.filing_data import (
    FilingData,
)


class FilingScraperPort(Protocol):
    async def scrape_10k(
        self, company_name: str, ticker: str | None
    ) -> FilingData: ...
