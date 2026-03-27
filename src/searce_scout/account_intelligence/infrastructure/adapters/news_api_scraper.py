"""News API scraper adapter — implements NewsScraperPort.

Uses NewsAPI.org to search for recent news articles about a company and
converts the results into domain NewsArticle value objects.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from searce_scout.account_intelligence.domain.ports.news_scraper_port import (
    NewsArticle,
    NewsScraperPort,
)
from searce_scout.shared_kernel.value_objects import URL

_NEWSAPI_EVERYTHING_URL = "https://newsapi.org/v2/everything"


class NewsApiScraper:
    """Fetches company news from NewsAPI.org.

    Implements :class:`NewsScraperPort`.
    """

    def __init__(
        self,
        *,
        api_key: str,
        timeout: float = 30.0,
        page_size: int = 20,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._page_size = page_size

    # ------------------------------------------------------------------
    # NewsScraperPort implementation
    # ------------------------------------------------------------------

    async def scrape_news(
        self, company_name: str, days_back: int = 90
    ) -> tuple[NewsArticle, ...]:
        """Search NewsAPI for recent articles mentioning *company_name*."""
        from_date = datetime.now(tz=timezone.utc) - timedelta(days=days_back)

        params = {
            "q": f'"{company_name}"',
            "from": from_date.strftime("%Y-%m-%d"),
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": self._page_size,
            "apiKey": self._api_key,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(_NEWSAPI_EVERYTHING_URL, params=params)
            response.raise_for_status()

        data = response.json()
        articles = data.get("articles", [])

        results: list[NewsArticle] = []
        for article in articles:
            published_str = article.get("publishedAt", "")
            try:
                published_at = datetime.fromisoformat(
                    published_str.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                published_at = datetime.now(tz=timezone.utc)

            article_url = article.get("url", "")
            if not article_url:
                continue

            results.append(
                NewsArticle(
                    title=article.get("title", "") or "",
                    url=URL(value=article_url),
                    published_at=published_at,
                    summary=article.get("description", "") or "",
                )
            )

        return tuple(results)


# Structural compatibility assertion
def _check_port_compliance() -> None:
    _: NewsScraperPort = NewsApiScraper(api_key="test")  # type: ignore[assignment]
