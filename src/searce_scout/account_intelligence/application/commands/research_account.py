"""Command and handler for researching an account."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort

from searce_scout.account_intelligence.application.dtos.account_dtos import (
    AccountProfileDTO,
)
from searce_scout.account_intelligence.application.orchestration.account_research_workflow import (
    AccountResearchWorkflow,
)
from searce_scout.account_intelligence.domain.ports.account_repository_port import (
    AccountRepositoryPort,
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


@dataclass(frozen=True)
class ResearchAccountCommand:
    company_name: str
    website: str | None = None
    ticker: str | None = None


class ResearchAccountHandler:
    """Orchestrates full account research by delegating to the workflow."""

    def __init__(
        self,
        filing_scraper: FilingScraperPort,
        news_scraper: NewsScraperPort,
        job_board_scraper: JobBoardScraperPort,
        tech_detector: TechDetectorPort,
        ai_analyzer: AIAnalyzerPort,
        account_repository: AccountRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._filing_scraper = filing_scraper
        self._news_scraper = news_scraper
        self._job_board_scraper = job_board_scraper
        self._tech_detector = tech_detector
        self._ai_analyzer = ai_analyzer
        self._account_repository = account_repository
        self._event_bus = event_bus

    async def execute(self, cmd: ResearchAccountCommand) -> AccountProfileDTO:
        workflow = AccountResearchWorkflow(
            filing_scraper=self._filing_scraper,
            news_scraper=self._news_scraper,
            job_board_scraper=self._job_board_scraper,
            tech_detector=self._tech_detector,
            ai_analyzer=self._ai_analyzer,
            signal_scoring_service=BuyingSignalScoringService(),
        )

        account = await workflow.execute(
            company_name=cmd.company_name,
            website=cmd.website,
            ticker=cmd.ticker,
        )

        await self._account_repository.save(account)

        if account.domain_events:
            await self._event_bus.publish(account.domain_events)

        return AccountProfileDTO.from_domain(account)
