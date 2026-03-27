"""Integration tests for the weekly research batch pipeline.

These tests exercise the WeeklyResearchBatchWorkflow with mocked handlers,
verifying parallel research execution, error handling, and score-based sorting.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from searce_scout.scout_orchestrator.config.settings import ScoutSettings
from searce_scout.scout_orchestrator.workflows.weekly_research_batch import (
    WeeklyResearchBatchWorkflow,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_account_dto(
    company_name: str,
    score: float,
    account_id: str | None = None,
) -> MagicMock:
    """Return a mock AccountProfileDTO with the fields the workflow reads."""
    dto = MagicMock()
    dto.account_id = account_id or f"acc-{company_name.lower().replace(' ', '-')}"
    dto.company_name = company_name
    dto.industry_name = "Technology"
    dto.migration_opportunity_score = score
    dto.buying_signal_count = int(score * 10)
    dto.is_migration_target = score > 0.7
    dto.primary_cloud = "AWS"
    return dto


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_container() -> MagicMock:
    """Container mock with a research handler that returns varied scores."""
    container = MagicMock()
    container.settings = ScoutSettings(
        api_key="test-key",
        max_concurrent_research=2,
    )

    # Map company names to different scores for sort testing
    scores = {
        "AlphaCo": 0.95,
        "BetaCo": 0.60,
        "GammaCo": 0.80,
        "DeltaCo": 0.70,
        "EpsilonCo": 0.90,
    }

    async def _research(cmd):
        name = cmd.company_name
        score = scores.get(name, 0.5)
        return _make_account_dto(company_name=name, score=score)

    container.research_account_handler = MagicMock()
    container.research_account_handler.execute = AsyncMock(side_effect=_research)

    return container


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_weekly_batch_processes_multiple_companies(mock_container: MagicMock):
    """The batch workflow should research all provided companies."""
    workflow = WeeklyResearchBatchWorkflow(container=mock_container)

    results = await workflow.execute(
        company_names=["AlphaCo", "BetaCo", "GammaCo"],
        max_results=10,
    )

    assert len(results) == 3
    assert mock_container.research_account_handler.execute.await_count == 3

    # Verify each result has the expected shape
    for result in results:
        assert "account_id" in result
        assert "company_name" in result
        assert "migration_opportunity_score" in result
        assert "buying_signal_count" in result


@pytest.mark.integration
async def test_weekly_batch_returns_sorted_by_score(mock_container: MagicMock):
    """Results must be sorted by migration_opportunity_score descending."""
    workflow = WeeklyResearchBatchWorkflow(container=mock_container)

    results = await workflow.execute(
        company_names=["AlphaCo", "BetaCo", "GammaCo", "DeltaCo", "EpsilonCo"],
        max_results=10,
    )

    scores = [r["migration_opportunity_score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    # Verify the top result is AlphaCo (score=0.95)
    assert results[0]["company_name"] == "AlphaCo"
    assert results[0]["migration_opportunity_score"] == 0.95
    # BetaCo (0.60) should be last
    assert results[-1]["company_name"] == "BetaCo"


@pytest.mark.integration
async def test_weekly_batch_respects_max_results(mock_container: MagicMock):
    """max_results should cap the number of returned results."""
    workflow = WeeklyResearchBatchWorkflow(container=mock_container)

    results = await workflow.execute(
        company_names=["AlphaCo", "BetaCo", "GammaCo", "DeltaCo", "EpsilonCo"],
        max_results=3,
    )

    assert len(results) == 3
    # Should be the top 3 by score: AlphaCo(0.95), EpsilonCo(0.90), GammaCo(0.80)
    names = [r["company_name"] for r in results]
    assert names == ["AlphaCo", "EpsilonCo", "GammaCo"]


@pytest.mark.integration
async def test_weekly_batch_handles_research_failures(mock_container: MagicMock):
    """If a company research fails, it should be excluded from results."""
    original_side_effect = mock_container.research_account_handler.execute.side_effect

    async def _research_with_failure(cmd):
        if cmd.company_name == "FailCo":
            raise RuntimeError("External API error")
        return await original_side_effect(cmd)

    mock_container.research_account_handler.execute = AsyncMock(
        side_effect=_research_with_failure
    )

    workflow = WeeklyResearchBatchWorkflow(container=mock_container)

    results = await workflow.execute(
        company_names=["AlphaCo", "FailCo", "GammaCo"],
        max_results=10,
    )

    # FailCo should be excluded
    assert len(results) == 2
    names = [r["company_name"] for r in results]
    assert "FailCo" not in names
    assert "AlphaCo" in names
    assert "GammaCo" in names


@pytest.mark.integration
async def test_weekly_batch_empty_list_returns_empty(mock_container: MagicMock):
    """An empty company list should return an empty result list."""
    workflow = WeeklyResearchBatchWorkflow(container=mock_container)

    results = await workflow.execute(company_names=[], max_results=10)

    assert results == []
    mock_container.research_account_handler.execute.assert_not_awaited()
