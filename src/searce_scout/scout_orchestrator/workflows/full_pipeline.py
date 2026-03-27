"""
Full Pipeline Workflow

End-to-end Scout pipeline: research -> discover -> generate messages ->
start outreach sequences -> generate presentation -> sync to CRM.

Uses DAGOrchestrator for parallelism-first execution with dependency ordering.
"""

from __future__ import annotations

import asyncio
from typing import Any

from searce_scout.shared_kernel.orchestration.dag_orchestrator import (
    DAGOrchestrator,
    WorkflowStep,
)

from searce_scout.account_intelligence.application.commands.research_account import (
    ResearchAccountCommand,
)
from searce_scout.stakeholder_discovery.application.commands.discover_stakeholders import (
    DiscoverStakeholdersCommand,
)
from searce_scout.messaging.application.commands.generate_message import (
    GenerateMessageCommand,
)
from searce_scout.outreach.application.commands.start_sequence import (
    StartSequenceCommand,
)
from searce_scout.presentation_gen.application.commands.generate_deck import (
    GenerateDeckCommand,
)
from searce_scout.crm_sync.application.commands.push_to_crm import PushToCRMCommand

from searce_scout.scout_orchestrator.config.dependency_injection import Container


class FullPipelineWorkflow:
    """Orchestrates the complete Searce Scout pipeline for a single account."""

    def __init__(self, container: Container) -> None:
        self._container = container

    async def execute(
        self,
        company_name: str,
        website: str | None = None,
        ticker: str | None = None,
        tone: str = "PROFESSIONAL_CONSULTANT",
    ) -> dict[str, Any]:
        """Run the full pipeline and return a summary dict.

        Returns:
            A dict with keys: account_id, stakeholder_count,
            sequences_started, deck_url, crm_synced.
        """
        dag = DAGOrchestrator(
            steps=[
                WorkflowStep(
                    name="research_account",
                    execute=self._research_account,
                    timeout_seconds=120.0,
                ),
                WorkflowStep(
                    name="discover_stakeholders",
                    execute=self._discover_stakeholders,
                    depends_on=("research_account",),
                    timeout_seconds=120.0,
                ),
                WorkflowStep(
                    name="generate_messages",
                    execute=self._generate_messages,
                    depends_on=("discover_stakeholders",),
                    timeout_seconds=300.0,
                ),
                WorkflowStep(
                    name="start_outreach_sequences",
                    execute=self._start_outreach_sequences,
                    depends_on=("generate_messages",),
                    timeout_seconds=120.0,
                ),
                WorkflowStep(
                    name="generate_presentations",
                    execute=self._generate_presentations,
                    depends_on=("research_account",),
                    timeout_seconds=120.0,
                    is_critical=False,
                ),
                WorkflowStep(
                    name="sync_to_crm",
                    execute=self._sync_to_crm,
                    depends_on=("start_outreach_sequences",),
                    timeout_seconds=60.0,
                    is_critical=False,
                ),
            ]
        )

        context: dict[str, Any] = {
            "company_name": company_name,
            "website": website,
            "ticker": ticker,
            "tone": tone,
        }

        results = await dag.execute(context)

        # Build summary
        account_dto = results.get("research_account")
        stakeholders = results.get("discover_stakeholders") or []
        sequences = results.get("start_outreach_sequences") or []
        deck_result = results.get("generate_presentations")
        crm_result = results.get("sync_to_crm")

        return {
            "account_id": account_dto.account_id if account_dto else None,
            "stakeholder_count": len(stakeholders),
            "sequences_started": len(sequences),
            "deck_url": (
                deck_result.google_slides_url
                if deck_result and hasattr(deck_result, "google_slides_url")
                else None
            ),
            "crm_synced": crm_result is not None,
        }

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    async def _research_account(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> Any:
        """Step 1: Research the target account."""
        cmd = ResearchAccountCommand(
            company_name=context["company_name"],
            website=context.get("website"),
            ticker=context.get("ticker"),
        )
        return await self._container.research_account_handler.execute(cmd)

    async def _discover_stakeholders(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> list[Any]:
        """Step 2: Discover stakeholders at the researched account."""
        account_dto = completed["research_account"]
        cmd = DiscoverStakeholdersCommand(
            account_id=account_dto.account_id,
            company_name=account_dto.company_name,
        )
        return await self._container.discover_stakeholders_handler.execute(cmd)

    async def _generate_messages(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> list[Any]:
        """Step 3: Generate all 5 sequence messages for each stakeholder."""
        account_dto = completed["research_account"]
        stakeholders = completed["discover_stakeholders"]
        tone = context.get("tone", "PROFESSIONAL_CONSULTANT")

        channels = ["EMAIL", "LINKEDIN_REQUEST", "EMAIL", "LINKEDIN_MESSAGE", "EMAIL"]
        all_messages: list[Any] = []

        async def generate_for_stakeholder(stakeholder: Any) -> list[Any]:
            account_context = {
                "company_name": account_dto.company_name,
                "industry": account_dto.industry_name,
                "tech_stack_summary": account_dto.tech_stack_summary or "",
                "buying_signals": [],
                "pain_points": [],
                "searce_offering": "Cloud Migration & Data Engineering",
            }
            stakeholder_context = {
                "stakeholder_name": stakeholder.full_name,
                "job_title": stakeholder.job_title,
            }

            msgs: list[Any] = []
            for step_num, channel in enumerate(channels, start=1):
                cmd = GenerateMessageCommand(
                    account_id=account_dto.account_id,
                    stakeholder_id=stakeholder.stakeholder_id,
                    channel=channel,
                    tone=tone,
                    step_number=step_num,
                )
                msg = await self._container.generate_message_handler.execute(
                    cmd, account_context, stakeholder_context,
                )
                msgs.append(msg)
            return msgs

        # Fan-out message generation across stakeholders (bounded concurrency)
        sem = asyncio.Semaphore(self._container.settings.max_concurrent_outreach)

        async def bounded_generate(s: Any) -> list[Any]:
            async with sem:
                return await generate_for_stakeholder(s)

        results = await asyncio.gather(
            *(bounded_generate(s) for s in stakeholders),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, list):
                all_messages.extend(result)

        return all_messages

    async def _start_outreach_sequences(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> list[Any]:
        """Step 4: Start outreach sequences for each stakeholder."""
        account_dto = completed["research_account"]
        stakeholders = completed["discover_stakeholders"]
        messages = completed["generate_messages"]

        # Group messages by stakeholder_id
        messages_by_stakeholder: dict[str, list[Any]] = {}
        for msg in messages:
            messages_by_stakeholder.setdefault(msg.stakeholder_id, []).append(msg)

        sequences: list[Any] = []
        for stakeholder in stakeholders:
            stakeholder_msgs = messages_by_stakeholder.get(
                stakeholder.stakeholder_id, []
            )
            if not stakeholder_msgs:
                continue

            # Build step-type -> message-id mapping
            step_types = [
                "EMAIL_1", "LINKEDIN_REQUEST", "EMAIL_2", "LINKEDIN_MESSAGE", "PHONE_TASK",
            ]
            message_ids: dict[str, str] = {}
            for i, step_type in enumerate(step_types):
                if i < len(stakeholder_msgs):
                    message_ids[step_type] = stakeholder_msgs[i].message_id

            cmd = StartSequenceCommand(
                account_id=account_dto.account_id,
                stakeholder_id=stakeholder.stakeholder_id,
                message_ids=message_ids,
            )
            seq = await self._container.start_sequence_handler.execute(cmd)
            sequences.append(seq)

        return sequences

    async def _generate_presentations(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> Any:
        """Step 5: Generate a presentation deck for the account."""
        account_dto = completed["research_account"]
        cmd = GenerateDeckCommand(
            account_id=account_dto.account_id,
            offering="Cloud Migration & Data Engineering",
            template_id=self._container.settings.slides_template_id,
        )
        account_context = {
            "company_name": account_dto.company_name,
            "industry": account_dto.industry_name,
            "tech_stack_summary": account_dto.tech_stack_summary or "",
            "migration_score": account_dto.migration_opportunity_score,
        }
        return await self._container.generate_deck_handler.execute(cmd, account_context)

    async def _sync_to_crm(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> Any:
        """Step 6: Push account + stakeholders + activities to CRM."""
        account_dto = completed["research_account"]
        provider = self._container.settings.crm_provider

        # Push the account record
        cmd = PushToCRMCommand(
            local_id=account_dto.account_id,
            record_type="ACCOUNT",
            provider=provider,
            fields={
                "Name": account_dto.company_name,
                "Industry": account_dto.industry_name,
                "Website": account_dto.website or "",
            },
        )
        result = await self._container.push_to_crm_handler.execute(cmd)
        return result
