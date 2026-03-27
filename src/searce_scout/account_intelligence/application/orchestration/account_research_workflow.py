"""DAG-orchestrated workflow for full account research."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from searce_scout.shared_kernel.orchestration.dag_orchestrator import (
    DAGOrchestrator,
    WorkflowStep,
)
from searce_scout.shared_kernel.types import AccountId
from searce_scout.shared_kernel.value_objects import CompanyName, URL

from searce_scout.account_intelligence.domain.entities.account_profile import (
    AccountProfile,
)
from searce_scout.account_intelligence.domain.events.account_events import (
    AccountResearchedEvent,
)
from searce_scout.account_intelligence.domain.ports.ai_analyzer_port import (
    AIAnalyzerPort,
)
from searce_scout.account_intelligence.domain.ports.filing_scraper_port import (
    FilingScraperPort,
)
from searce_scout.account_intelligence.domain.ports.job_board_scraper_port import (
    JobBoardScraperPort,
)
from searce_scout.account_intelligence.domain.ports.news_scraper_port import (
    NewsScraperPort,
)
from searce_scout.account_intelligence.domain.ports.tech_detector_port import (
    TechDetectorPort,
)
from searce_scout.account_intelligence.domain.services.signal_scoring import (
    BuyingSignalScoringService,
)
from searce_scout.account_intelligence.domain.value_objects.industry import (
    CompanySize,
    Industry,
)


class AccountResearchWorkflow:
    """Orchestrates parallel data collection and AI analysis for account research.

    DAG structure:
        scrape_filings ──┐
        scrape_news    ──┤── extract_signals ──┐
        scrape_jobs    ──┘                     ├── compose_profile
        detect_tech_stack ─────────────────────┘
    """

    def __init__(
        self,
        filing_scraper: FilingScraperPort,
        news_scraper: NewsScraperPort,
        job_board_scraper: JobBoardScraperPort,
        tech_detector: TechDetectorPort,
        ai_analyzer: AIAnalyzerPort,
        signal_scoring_service: BuyingSignalScoringService,
    ) -> None:
        self._filing_scraper = filing_scraper
        self._news_scraper = news_scraper
        self._job_board_scraper = job_board_scraper
        self._tech_detector = tech_detector
        self._ai_analyzer = ai_analyzer
        self._signal_scoring_service = signal_scoring_service

    async def execute(
        self,
        company_name: str,
        website: str | None = None,
        ticker: str | None = None,
    ) -> AccountProfile:
        context: dict[str, Any] = {
            "company_name": company_name,
            "website": website,
            "ticker": ticker,
        }

        # ------------------------------------------------------------------
        # Step functions -- each receives (context, completed) per DAGOrchestrator API
        # ------------------------------------------------------------------

        async def scrape_filings(ctx: dict[str, Any], _completed: dict[str, Any]) -> Any:
            return await self._filing_scraper.scrape_10k(
                company_name=ctx["company_name"],
                ticker=ctx["ticker"],
            )

        async def scrape_news(ctx: dict[str, Any], _completed: dict[str, Any]) -> Any:
            return await self._news_scraper.scrape_news(
                company_name=ctx["company_name"],
            )

        async def scrape_jobs(ctx: dict[str, Any], _completed: dict[str, Any]) -> Any:
            return await self._job_board_scraper.scrape_jobs(
                company_name=ctx["company_name"],
            )

        async def detect_tech_stack(ctx: dict[str, Any], _completed: dict[str, Any]) -> Any:
            domain = ctx["website"] or ctx["company_name"]
            return await self._tech_detector.detect_tech_stack(domain)

        async def extract_signals(_ctx: dict[str, Any], completed: dict[str, Any]) -> Any:
            filings = completed.get("scrape_filings")
            news = completed.get("scrape_news") or ()
            jobs = completed.get("scrape_jobs") or ()

            # Combine raw data into a textual summary for AI analysis
            parts: list[str] = []
            if filings:
                parts.append(
                    f"Filing data: revenue={filings.revenue}, "
                    f"IT spend mentions={filings.it_spend_mentions}, "
                    f"cloud mentions={filings.cloud_mentions}, "
                    f"digital transformation={filings.digital_transformation_mentions}"
                )
            for article in news:
                parts.append(f"News: {article.title} - {article.summary}")
            for job in jobs:
                parts.append(f"Job posting: {job.title} in {job.department}")

            raw_data = "\n".join(parts) if parts else "No data collected"
            return await self._ai_analyzer.extract_signals(raw_data)

        async def compose_profile(ctx: dict[str, Any], completed: dict[str, Any]) -> Any:
            signals = completed.get("extract_signals") or ()
            tech_stack = completed.get("detect_tech_stack")
            filings = completed.get("scrape_filings")

            account_id = AccountId(str(uuid4()))
            company = CompanyName(canonical=ctx["company_name"])
            website_url = URL(value=ctx["website"]) if ctx["website"] else None

            # Classify industry via AI
            industry = await self._ai_analyzer.classify_industry(
                company_name=ctx["company_name"],
                description="\n".join(
                    s.description for s in signals
                ) if signals else ctx["company_name"],
            )

            # Build the aggregate
            account = AccountProfile(
                account_id=account_id,
                company_name=company,
                industry=industry,
                company_size=CompanySize.ENTERPRISE,  # default; refined later
                tech_stack=tech_stack,
                buying_signals=signals,
                filing_data=filings,
                website=website_url,
                researched_at=datetime.now(UTC),
                domain_events=(
                    AccountResearchedEvent(
                        aggregate_id=str(account_id),
                        company_name=ctx["company_name"],
                    ),
                ),
            )

            return account

        # ------------------------------------------------------------------
        # Build and run the DAG
        # ------------------------------------------------------------------
        dag = DAGOrchestrator(
            steps=[
                WorkflowStep(
                    name="scrape_filings",
                    execute=scrape_filings,
                    timeout_seconds=30.0,
                    is_critical=False,
                ),
                WorkflowStep(
                    name="scrape_news",
                    execute=scrape_news,
                    timeout_seconds=30.0,
                    is_critical=False,
                ),
                WorkflowStep(
                    name="scrape_jobs",
                    execute=scrape_jobs,
                    timeout_seconds=30.0,
                    is_critical=False,
                ),
                WorkflowStep(
                    name="detect_tech_stack",
                    execute=detect_tech_stack,
                    timeout_seconds=30.0,
                    is_critical=False,
                ),
                WorkflowStep(
                    name="extract_signals",
                    execute=extract_signals,
                    depends_on=("scrape_filings", "scrape_news", "scrape_jobs"),
                    timeout_seconds=60.0,
                ),
                WorkflowStep(
                    name="compose_profile",
                    execute=compose_profile,
                    depends_on=("extract_signals", "detect_tech_stack"),
                    timeout_seconds=30.0,
                ),
            ]
        )

        results = await dag.execute(context)
        return results["compose_profile"]
