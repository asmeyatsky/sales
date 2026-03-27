"""Application / orchestration tests for AccountResearchWorkflow.

Verifies that the DAG-orchestrated workflow calls all scraper ports
and composes an AccountProfile from the collected results.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from searce_scout.shared_kernel.value_objects import URL

from searce_scout.account_intelligence.application.orchestration.account_research_workflow import (
    AccountResearchWorkflow,
)
from searce_scout.account_intelligence.domain.entities.buying_signal import BuyingSignal
from searce_scout.account_intelligence.domain.ports.ai_analyzer_port import AIAnalyzerPort
from searce_scout.account_intelligence.domain.ports.filing_scraper_port import FilingScraperPort
from searce_scout.account_intelligence.domain.ports.job_board_scraper_port import (
    JobBoardScraperPort,
    JobPosting,
)
from searce_scout.account_intelligence.domain.ports.news_scraper_port import (
    NewsArticle,
    NewsScraperPort,
)
from searce_scout.account_intelligence.domain.ports.tech_detector_port import TechDetectorPort
from searce_scout.account_intelligence.domain.services.signal_scoring import (
    BuyingSignalScoringService,
)
from searce_scout.account_intelligence.domain.value_objects.filing_data import FilingData
from searce_scout.account_intelligence.domain.value_objects.industry import Industry
from searce_scout.account_intelligence.domain.value_objects.signal_type import (
    SignalStrength,
    SignalType,
)
from searce_scout.account_intelligence.domain.value_objects.tech_stack import (
    CloudProvider,
    TechComponent,
    TechStack,
)


@pytest.fixture()
def filing_scraper() -> AsyncMock:
    scraper = AsyncMock(spec=FilingScraperPort)
    scraper.scrape_10k.return_value = FilingData(
        fiscal_year=2025,
        revenue=5_000_000_000.0,
        it_spend_mentions=("increasing IT budget",),
        digital_transformation_mentions=("digital transformation initiative",),
        cloud_mentions=("migrating to the cloud",),
    )
    return scraper


@pytest.fixture()
def news_scraper() -> AsyncMock:
    scraper = AsyncMock(spec=NewsScraperPort)
    scraper.scrape_news.return_value = (
        NewsArticle(
            title="TestCo announces cloud migration",
            url=URL(value="https://news.example.com/testco"),
            published_at=datetime.now(UTC),
            summary="TestCo is migrating workloads to the cloud.",
        ),
    )
    return scraper


@pytest.fixture()
def job_board_scraper() -> AsyncMock:
    scraper = AsyncMock(spec=JobBoardScraperPort)
    scraper.scrape_jobs.return_value = (
        JobPosting(
            title="Senior Cloud Engineer",
            location="Remote",
            department="Engineering",
            posted_at=datetime.now(UTC),
            url=URL(value="https://jobs.example.com/testco/1"),
        ),
    )
    return scraper


@pytest.fixture()
def tech_detector() -> AsyncMock:
    detector = AsyncMock(spec=TechDetectorPort)
    detector.detect_tech_stack.return_value = TechStack(
        components=(
            TechComponent(name="EC2", category="compute", provider=CloudProvider.AWS),
        ),
        primary_cloud=CloudProvider.AWS,
    )
    return detector


@pytest.fixture()
def ai_analyzer() -> AsyncMock:
    analyzer = AsyncMock(spec=AIAnalyzerPort)
    analyzer.extract_signals.return_value = (
        BuyingSignal(
            signal_id="sig-1",
            signal_type=SignalType.CLOUD_MIGRATION_MENTION,
            strength=SignalStrength.STRONG,
            description="Cloud migration announcement detected",
            source_url=URL(value="https://news.example.com/testco"),
            detected_at=datetime.now(UTC),
        ),
    )
    analyzer.classify_industry.return_value = Industry(
        name="Technology", vertical="SaaS"
    )
    return analyzer


def _build_workflow(
    filing_scraper: AsyncMock,
    news_scraper: AsyncMock,
    job_board_scraper: AsyncMock,
    tech_detector: AsyncMock,
    ai_analyzer: AsyncMock,
) -> AccountResearchWorkflow:
    return AccountResearchWorkflow(
        filing_scraper=filing_scraper,
        news_scraper=news_scraper,
        job_board_scraper=job_board_scraper,
        tech_detector=tech_detector,
        ai_analyzer=ai_analyzer,
        signal_scoring_service=BuyingSignalScoringService(),
    )


async def test_workflow_runs_scrapers_in_parallel(
    filing_scraper: AsyncMock,
    news_scraper: AsyncMock,
    job_board_scraper: AsyncMock,
    tech_detector: AsyncMock,
    ai_analyzer: AsyncMock,
) -> None:
    """All scraper ports must be invoked during workflow execution."""
    workflow = _build_workflow(
        filing_scraper, news_scraper, job_board_scraper, tech_detector, ai_analyzer
    )

    await workflow.execute(
        company_name="TestCo",
        website="https://testco.example.com",
        ticker="TST",
    )

    # Verify all scraper ports were called
    filing_scraper.scrape_10k.assert_awaited_once_with(
        company_name="TestCo", ticker="TST"
    )
    news_scraper.scrape_news.assert_awaited_once_with(company_name="TestCo")
    job_board_scraper.scrape_jobs.assert_awaited_once_with(company_name="TestCo")
    tech_detector.detect_tech_stack.assert_awaited_once_with(
        "https://testco.example.com"
    )
    ai_analyzer.extract_signals.assert_awaited_once()
    ai_analyzer.classify_industry.assert_awaited_once()


async def test_workflow_composes_profile_from_results(
    filing_scraper: AsyncMock,
    news_scraper: AsyncMock,
    job_board_scraper: AsyncMock,
    tech_detector: AsyncMock,
    ai_analyzer: AsyncMock,
) -> None:
    """The workflow must compose an AccountProfile from all collected data."""
    workflow = _build_workflow(
        filing_scraper, news_scraper, job_board_scraper, tech_detector, ai_analyzer
    )

    account = await workflow.execute(
        company_name="TestCo",
        website="https://testco.example.com",
        ticker="TST",
    )

    # Verify the profile was assembled correctly
    assert str(account.company_name) == "TestCo"
    assert account.industry.name == "Technology"
    assert account.tech_stack is not None
    assert account.tech_stack.primary_cloud == CloudProvider.AWS
    assert len(account.buying_signals) == 1
    assert account.buying_signals[0].signal_type == SignalType.CLOUD_MIGRATION_MENTION
    assert account.filing_data is not None
    assert account.filing_data.revenue == 5_000_000_000.0

    # Must have an AccountResearchedEvent
    assert len(account.domain_events) >= 1
    from searce_scout.account_intelligence.domain.events.account_events import (
        AccountResearchedEvent,
    )
    assert any(
        isinstance(e, AccountResearchedEvent) for e in account.domain_events
    )
