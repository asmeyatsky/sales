"""Application tests for ResearchAccountHandler.

Verifies that the handler correctly delegates to the workflow, persists
the resulting AccountProfile, and publishes domain events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import AccountId
from searce_scout.shared_kernel.value_objects import CompanyName, URL

from searce_scout.account_intelligence.application.commands.research_account import (
    ResearchAccountCommand,
    ResearchAccountHandler,
)
from searce_scout.account_intelligence.domain.entities.account_profile import AccountProfile
from searce_scout.account_intelligence.domain.events.account_events import (
    AccountResearchedEvent,
)
from searce_scout.account_intelligence.domain.ports.account_repository_port import (
    AccountRepositoryPort,
)
from searce_scout.account_intelligence.domain.ports.ai_analyzer_port import AIAnalyzerPort
from searce_scout.account_intelligence.domain.ports.filing_scraper_port import FilingScraperPort
from searce_scout.account_intelligence.domain.ports.job_board_scraper_port import (
    JobBoardScraperPort,
)
from searce_scout.account_intelligence.domain.ports.news_scraper_port import NewsScraperPort
from searce_scout.account_intelligence.domain.ports.tech_detector_port import TechDetectorPort
from searce_scout.account_intelligence.domain.value_objects.industry import (
    CompanySize,
    Industry,
)
from searce_scout.account_intelligence.domain.value_objects.tech_stack import (
    CloudProvider,
    TechStack,
)


def _make_account(*, with_events: bool = True) -> AccountProfile:
    """Build a minimal AccountProfile, optionally with domain events."""
    events = ()
    if with_events:
        events = (
            AccountResearchedEvent(
                aggregate_id="acc-test",
                company_name="TestCo",
            ),
        )
    return AccountProfile(
        account_id=AccountId("acc-test"),
        company_name=CompanyName(canonical="TestCo"),
        industry=Industry(name="Technology", vertical="SaaS"),
        company_size=CompanySize.ENTERPRISE,
        tech_stack=TechStack(components=(), primary_cloud=CloudProvider.GCP),
        buying_signals=(),
        filing_data=None,
        website=URL(value="https://testco.example.com"),
        researched_at=datetime.now(UTC),
        domain_events=events,
    )


@pytest.fixture()
def ports() -> dict[str, AsyncMock]:
    return {
        "filing_scraper": AsyncMock(spec=FilingScraperPort),
        "news_scraper": AsyncMock(spec=NewsScraperPort),
        "job_board_scraper": AsyncMock(spec=JobBoardScraperPort),
        "tech_detector": AsyncMock(spec=TechDetectorPort),
        "ai_analyzer": AsyncMock(spec=AIAnalyzerPort),
        "account_repository": AsyncMock(spec=AccountRepositoryPort),
        "event_bus": AsyncMock(spec=EventBusPort),
    }


def _build_handler(ports: dict[str, AsyncMock]) -> ResearchAccountHandler:
    return ResearchAccountHandler(
        filing_scraper=ports["filing_scraper"],
        news_scraper=ports["news_scraper"],
        job_board_scraper=ports["job_board_scraper"],
        tech_detector=ports["tech_detector"],
        ai_analyzer=ports["ai_analyzer"],
        account_repository=ports["account_repository"],
        event_bus=ports["event_bus"],
    )


async def test_research_account_saves_profile(ports: dict[str, AsyncMock]) -> None:
    """Handler must call account_repository.save with the researched account."""
    account = _make_account(with_events=True)

    with patch(
        "searce_scout.account_intelligence.application.commands.research_account.AccountResearchWorkflow"
    ) as MockWorkflow:
        mock_wf_instance = AsyncMock()
        mock_wf_instance.execute.return_value = account
        MockWorkflow.return_value = mock_wf_instance

        handler = _build_handler(ports)
        cmd = ResearchAccountCommand(
            company_name="TestCo",
            website="https://testco.example.com",
            ticker="TST",
        )

        result = await handler.execute(cmd)

    ports["account_repository"].save.assert_awaited_once_with(account)
    assert result.company_name == "TestCo"


async def test_research_account_publishes_events(ports: dict[str, AsyncMock]) -> None:
    """Handler must call event_bus.publish when the account has domain events."""
    account = _make_account(with_events=True)

    with patch(
        "searce_scout.account_intelligence.application.commands.research_account.AccountResearchWorkflow"
    ) as MockWorkflow:
        mock_wf_instance = AsyncMock()
        mock_wf_instance.execute.return_value = account
        MockWorkflow.return_value = mock_wf_instance

        handler = _build_handler(ports)
        cmd = ResearchAccountCommand(company_name="TestCo")

        await handler.execute(cmd)

    ports["event_bus"].publish.assert_awaited_once_with(account.domain_events)


async def test_research_account_no_publish_without_events(
    ports: dict[str, AsyncMock],
) -> None:
    """Handler must NOT call event_bus.publish when domain_events is empty."""
    account = _make_account(with_events=False)

    with patch(
        "searce_scout.account_intelligence.application.commands.research_account.AccountResearchWorkflow"
    ) as MockWorkflow:
        mock_wf_instance = AsyncMock()
        mock_wf_instance.execute.return_value = account
        MockWorkflow.return_value = mock_wf_instance

        handler = _build_handler(ports)
        cmd = ResearchAccountCommand(company_name="TestCo")

        await handler.execute(cmd)

    ports["event_bus"].publish.assert_not_awaited()
