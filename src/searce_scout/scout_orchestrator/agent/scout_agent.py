"""
Scout Agent

Top-level agent orchestrating all workflows.  Provides a simple interface
for the presentation layer (API / CLI) to trigger research, outreach,
inbox monitoring, and batch discovery.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from searce_scout.scout_orchestrator.config.dependency_injection import Container
from searce_scout.scout_orchestrator.workflows.full_pipeline import FullPipelineWorkflow
from searce_scout.scout_orchestrator.workflows.weekly_research_batch import (
    WeeklyResearchBatchWorkflow,
)


class ScoutAgent:
    """Top-level orchestrating agent for all Searce Scout workflows."""

    def __init__(self, container: Container) -> None:
        self.container = container
        self.full_pipeline = FullPipelineWorkflow(container)
        self.weekly_batch = WeeklyResearchBatchWorkflow(container)

    async def research_and_outreach(
        self,
        company_name: str,
        website: str | None = None,
        ticker: str | None = None,
        tone: str = "PROFESSIONAL_CONSULTANT",
    ) -> dict[str, Any]:
        """Run the full pipeline: research -> discover -> outreach -> deck -> CRM sync.

        Returns:
            Summary dict with account_id, stakeholder_count,
            sequences_started, deck_url, crm_synced.
        """
        return await self.full_pipeline.execute(
            company_name=company_name,
            website=website,
            ticker=ticker,
            tone=tone,
        )

    async def weekly_discovery(
        self,
        company_names: list[str],
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Batch-research multiple companies and return top migration targets.

        Returns:
            List of summary dicts sorted by migration_opportunity_score.
        """
        return await self.weekly_batch.execute(
            company_names=company_names,
            max_results=max_results,
        )

    async def check_inbox_and_respond(self) -> dict[str, Any]:
        """Check inboxes for replies, classify them, and apply actions.

        Returns:
            Summary dict with replies_found, classified, and actions_taken.
        """
        since = datetime.now(UTC) - timedelta(hours=24)
        return await self.container.inbox_monitoring_workflow.execute(since=since)
