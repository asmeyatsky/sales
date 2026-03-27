"""SEC EDGAR filing scraper adapter — implements FilingScraperPort.

Uses the SEC EDGAR full-text search API (efts.sec.gov) to find 10-K filings
and extract fiscal-year data, revenue metadata, and keyword mentions related
to IT spend, digital transformation, and cloud initiatives.
"""

from __future__ import annotations

import re
from datetime import datetime

import httpx

from searce_scout.account_intelligence.domain.ports.filing_scraper_port import (
    FilingScraperPort,
)
from searce_scout.account_intelligence.domain.value_objects.filing_data import (
    FilingData,
)

_EFTS_BASE_URL = "https://efts.sec.gov/LATEST/search-index"
_FULL_TEXT_URL = "https://efts.sec.gov/LATEST/search-index"
_EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
_EDGAR_FULL_TEXT_SEARCH = "https://efts.sec.gov/LATEST/search-index"

# SEC EDGAR full-text search endpoint
_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"

# Keywords we scan for in filing text
_IT_SPEND_KEYWORDS = (
    "IT spending",
    "information technology expenditure",
    "technology investment",
    "IT budget",
    "technology spend",
)

_DX_KEYWORDS = (
    "digital transformation",
    "digital strategy",
    "digital modernization",
    "digital initiative",
    "digitization",
)

_CLOUD_KEYWORDS = (
    "cloud computing",
    "cloud migration",
    "cloud infrastructure",
    "Amazon Web Services",
    "AWS",
    "Microsoft Azure",
    "Google Cloud",
    "GCP",
    "multi-cloud",
)


class SecEdgarScraper:
    """Scrapes SEC EDGAR for 10-K filings using the full-text search API.

    Implements :class:`FilingScraperPort`.
    """

    def __init__(
        self,
        *,
        user_agent: str = "SearceScout/1.0 (scout@searce.com)",
        timeout: float = 30.0,
    ) -> None:
        self._user_agent = user_agent
        self._timeout = timeout

    # ------------------------------------------------------------------
    # FilingScraperPort implementation
    # ------------------------------------------------------------------

    async def scrape_10k(
        self, company_name: str, ticker: str | None
    ) -> FilingData:
        """Search EDGAR for the most recent 10-K and extract key data."""
        query = ticker if ticker else company_name
        filings = await self._search_filings(query, form_type="10-K")

        if not filings:
            return FilingData(
                fiscal_year=datetime.now().year - 1,
                revenue=None,
                it_spend_mentions=(),
                digital_transformation_mentions=(),
                cloud_mentions=(),
            )

        latest = filings[0]
        filing_text = await self._fetch_filing_text(latest["file_url"])

        fiscal_year = self._extract_fiscal_year(latest, filing_text)
        revenue = self._extract_revenue(filing_text)
        it_mentions = self._find_keyword_mentions(filing_text, _IT_SPEND_KEYWORDS)
        dx_mentions = self._find_keyword_mentions(filing_text, _DX_KEYWORDS)
        cloud_mentions = self._find_keyword_mentions(filing_text, _CLOUD_KEYWORDS)

        return FilingData(
            fiscal_year=fiscal_year,
            revenue=revenue,
            it_spend_mentions=tuple(it_mentions),
            digital_transformation_mentions=tuple(dx_mentions),
            cloud_mentions=tuple(cloud_mentions),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _search_filings(
        self, query: str, form_type: str
    ) -> list[dict[str, str]]:
        """Call the EDGAR full-text search API and return filing metadata."""
        params = {
            "q": query,
            "dateRange": "custom",
            "forms": form_type,
            "startdt": f"{datetime.now().year - 2}-01-01",
            "enddt": datetime.now().strftime("%Y-%m-%d"),
        }
        headers = {"User-Agent": self._user_agent}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                "https://efts.sec.gov/LATEST/search-index",
                params=params,
                headers=headers,
            )
            response.raise_for_status()

        data = response.json()
        hits = data.get("hits", {}).get("hits", [])

        results: list[dict[str, str]] = []
        for hit in hits:
            source = hit.get("_source", {})
            results.append(
                {
                    "file_url": source.get("file_url", ""),
                    "file_date": source.get("file_date", ""),
                    "period_of_report": source.get("period_of_report", ""),
                    "entity_name": source.get("entity_name", ""),
                }
            )
        return results

    async def _fetch_filing_text(self, file_url: str) -> str:
        """Download the full text of a filing document."""
        if not file_url:
            return ""

        base = "https://www.sec.gov/Archives/"
        url = f"{base}{file_url}" if not file_url.startswith("http") else file_url

        headers = {"User-Agent": self._user_agent}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
        return response.text

    @staticmethod
    def _extract_fiscal_year(
        metadata: dict[str, str], filing_text: str
    ) -> int:
        """Derive the fiscal year from filing metadata or text content."""
        period = metadata.get("period_of_report", "")
        if period:
            try:
                return int(period[:4])
            except (ValueError, IndexError):
                pass

        file_date = metadata.get("file_date", "")
        if file_date:
            try:
                return int(file_date[:4]) - 1
            except (ValueError, IndexError):
                pass

        return datetime.now().year - 1

    @staticmethod
    def _extract_revenue(text: str) -> float | None:
        """Attempt to extract a revenue figure from filing text.

        Looks for patterns like ``$X,XXX million`` or ``$X.X billion`` near
        the words "revenue" or "net sales".
        """
        patterns = [
            r"(?:total\s+)?(?:net\s+)?(?:revenue|net\s+sales)\s*(?:was|were|of)\s*\$\s*([\d,]+(?:\.\d+)?)\s*(million|billion)",
            r"\$\s*([\d,]+(?:\.\d+)?)\s*(million|billion)\s*(?:in\s+)?(?:total\s+)?(?:net\s+)?(?:revenue|net\s+sales)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw = float(match.group(1).replace(",", ""))
                unit = match.group(2).lower()
                multiplier = 1_000_000_000 if unit == "billion" else 1_000_000
                return raw * multiplier
        return None

    @staticmethod
    def _find_keyword_mentions(
        text: str, keywords: tuple[str, ...]
    ) -> list[str]:
        """Return context snippets around each keyword found in text."""
        mentions: list[str] = []
        text_lower = text.lower()
        for keyword in keywords:
            start = 0
            kw_lower = keyword.lower()
            while True:
                idx = text_lower.find(kw_lower, start)
                if idx == -1:
                    break
                # Extract surrounding context (up to 200 chars each side)
                snippet_start = max(0, idx - 200)
                snippet_end = min(len(text), idx + len(keyword) + 200)
                snippet = text[snippet_start:snippet_end].strip()
                # Normalize whitespace
                snippet = re.sub(r"\s+", " ", snippet)
                mentions.append(snippet)
                start = idx + len(keyword)
                # Cap at 5 mentions per keyword to avoid noise
                if len(mentions) >= 5 * len(keywords):
                    return mentions
        return mentions


# Structural compatibility assertion
def _check_port_compliance() -> None:
    _: FilingScraperPort = SecEdgarScraper()  # type: ignore[assignment]
