"""
Weekly Research Batch Workflow

Runs the research pipeline for multiple companies in parallel (bounded by
max_concurrent_research) and returns the top results sorted by
migration_opportunity_score.
"""

from __future__ import annotations

import asyncio
from typing import Any

from searce_scout.account_intelligence.application.commands.research_account import (
    ResearchAccountCommand,
)

from searce_scout.scout_orchestrator.config.dependency_injection import Container


class WeeklyResearchBatchWorkflow:
    """Batch-researches a list of companies, returning top migration targets."""

    def __init__(self, container: Container) -> None:
        self._container = container

    async def execute(
        self,
        company_names: list[str],
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Research multiple companies in parallel and return sorted results.

        Args:
            company_names: Names of companies to research.
            max_results: Maximum number of results to return.

        Returns:
            A list of summary dicts sorted by migration_opportunity_score
            (descending), capped at *max_results*.
        """
        semaphore = asyncio.Semaphore(
            self._container.settings.max_concurrent_research
        )

        async def research_one(name: str) -> dict[str, Any] | None:
            async with semaphore:
                try:
                    cmd = ResearchAccountCommand(company_name=name)
                    dto = await self._container.research_account_handler.execute(cmd)
                    return {
                        "account_id": dto.account_id,
                        "company_name": dto.company_name,
                        "industry": dto.industry_name,
                        "migration_opportunity_score": dto.migration_opportunity_score,
                        "buying_signal_count": dto.buying_signal_count,
                        "is_migration_target": dto.is_migration_target,
                        "primary_cloud": dto.primary_cloud,
                    }
                except Exception:
                    return None

        results = await asyncio.gather(
            *(research_one(name) for name in company_names),
            return_exceptions=True,
        )

        # Filter out failures and exceptions
        valid: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, dict) and result is not None:
                valid.append(result)

        # Sort descending by migration_opportunity_score
        valid.sort(
            key=lambda r: r.get("migration_opportunity_score", 0.0),
            reverse=True,
        )

        return valid[:max_results]
