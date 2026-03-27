"""Job board scraper adapter — implements JobBoardScraperPort.

Uses httpx to search job boards for relevant tech roles at a target company.
Focuses on roles that signal cloud/data/ML investment: Data Engineer,
Cloud Architect, DevOps Engineer, ML Engineer, and similar titles.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from searce_scout.account_intelligence.domain.ports.job_board_scraper_port import (
    JobBoardScraperPort,
    JobPosting,
)
from searce_scout.shared_kernel.value_objects import URL

# Relevant tech roles that indicate cloud/data investment intent
_TARGET_ROLES = (
    "Data Engineer",
    "Cloud Architect",
    "DevOps Engineer",
    "ML Engineer",
    "Machine Learning Engineer",
    "Platform Engineer",
    "Site Reliability Engineer",
    "Data Scientist",
    "Cloud Engineer",
    "Infrastructure Engineer",
)

# Placeholder job search API endpoint (could be LinkedIn, Indeed, etc.)
_JOB_SEARCH_URL = "https://api.adzuna.com/v1/api/jobs/us/search/1"


class JobBoardScraper:
    """Scrapes job boards for tech-related openings at a target company.

    Implements :class:`JobBoardScraperPort`.
    """

    def __init__(
        self,
        *,
        app_id: str,
        app_key: str,
        timeout: float = 30.0,
        results_per_page: int = 50,
    ) -> None:
        self._app_id = app_id
        self._app_key = app_key
        self._timeout = timeout
        self._results_per_page = results_per_page

    # ------------------------------------------------------------------
    # JobBoardScraperPort implementation
    # ------------------------------------------------------------------

    async def scrape_jobs(
        self, company_name: str
    ) -> tuple[JobPosting, ...]:
        """Search for tech job postings at *company_name*."""
        role_query = " OR ".join(f'"{role}"' for role in _TARGET_ROLES)
        query = f'"{company_name}" AND ({role_query})'

        params = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "what": query,
            "results_per_page": self._results_per_page,
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(_JOB_SEARCH_URL, params=params)
            response.raise_for_status()

        data = response.json()
        raw_results = data.get("results", [])

        postings: list[JobPosting] = []
        for item in raw_results:
            title = item.get("title", "")
            if not self._is_relevant_role(title):
                continue

            created_str = item.get("created", "")
            try:
                posted_at = datetime.fromisoformat(
                    created_str.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                posted_at = datetime.now(tz=timezone.utc)

            redirect_url = item.get("redirect_url", "")
            if not redirect_url:
                continue

            location_data = item.get("location", {})
            location_parts: list[str] = []
            for area in location_data.get("area", []):
                if area:
                    location_parts.append(area)
            location = ", ".join(location_parts) if location_parts else "Unknown"

            department = self._infer_department(title)

            postings.append(
                JobPosting(
                    title=title,
                    location=location,
                    department=department,
                    posted_at=posted_at,
                    url=URL(value=redirect_url),
                )
            )

        return tuple(postings)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_relevant_role(title: str) -> bool:
        """Check whether a job title matches one of our target roles."""
        title_lower = title.lower()
        return any(role.lower() in title_lower for role in _TARGET_ROLES)

    @staticmethod
    def _infer_department(title: str) -> str:
        """Infer a department category from the job title."""
        title_lower = title.lower()
        if any(kw in title_lower for kw in ("data engineer", "data scientist", "analytics")):
            return "Data & Analytics"
        if any(kw in title_lower for kw in ("ml", "machine learning", "ai")):
            return "Machine Learning"
        if any(kw in title_lower for kw in ("devops", "sre", "site reliability", "platform")):
            return "DevOps / Platform"
        if any(kw in title_lower for kw in ("cloud", "infrastructure")):
            return "Cloud Infrastructure"
        return "Engineering"


# Structural compatibility assertion
def _check_port_compliance() -> None:
    _: JobBoardScraperPort = JobBoardScraper(  # type: ignore[assignment]
        app_id="test", app_key="test"
    )
