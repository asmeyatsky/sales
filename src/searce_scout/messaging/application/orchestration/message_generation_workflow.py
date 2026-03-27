"""DAG-based workflow for message generation.

Architectural Intent:
- Parallelism-first: case study fetches run in parallel (Step 1)
- Sequential where needed: personalization depends on case studies,
  AI generation depends on personalization, persistence depends on generation
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from searce_scout.shared_kernel.orchestration.dag_orchestrator import (
    DAGOrchestrator,
    WorkflowStep,
)
from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import AccountId, MessageId, StakeholderId

from searce_scout.messaging.domain.entities.message import Message
from searce_scout.messaging.domain.entities.message_template import MessageTemplate
from searce_scout.messaging.domain.events.message_events import MessageGeneratedEvent
from searce_scout.messaging.domain.ports.ai_message_generator_port import (
    AIMessageGeneratorPort,
)
from searce_scout.messaging.domain.ports.case_study_port import CaseStudyPort
from searce_scout.messaging.domain.ports.message_repository_port import (
    MessageRepositoryPort,
)
from searce_scout.messaging.domain.services.personalization_service import (
    PersonalizationService,
)
from searce_scout.messaging.domain.value_objects.channel import Channel
from searce_scout.messaging.domain.value_objects.message_content import MessageStatus
from searce_scout.messaging.domain.value_objects.tone import Tone


class MessageGenerationWorkflow:
    """Orchestrates message generation through a DAG of dependent steps.

    Steps:
        1. fetch_case_studies (parallel) - retrieves case studies by industry/offering
        2. build_personalization (depends on 1) - assembles PersonalizationContext
        3. generate_via_ai (depends on 2) - calls AI message generator
        4. create_and_save (depends on 3) - creates Message entity, persists, publishes
    """

    def __init__(
        self,
        case_study_port: CaseStudyPort,
        ai_message_generator: AIMessageGeneratorPort,
        message_repository: MessageRepositoryPort,
        event_bus: EventBusPort,
        personalization_service: PersonalizationService,
    ) -> None:
        self._case_study_port = case_study_port
        self._ai_message_generator = ai_message_generator
        self._message_repository = message_repository
        self._event_bus = event_bus
        self._personalization_service = personalization_service

    async def execute(
        self,
        account_id: str,
        stakeholder_id: str,
        channel: str,
        tone: str,
        step_number: int,
        account_context: dict,
        stakeholder_context: dict,
    ) -> Message:
        """Run the full message generation workflow.

        Args:
            account_id: Target account identifier.
            stakeholder_id: Target stakeholder identifier.
            channel: Delivery channel name.
            tone: Desired tone name.
            step_number: The sequence step number for template selection.
            account_context: Cross-BC account data dict.
            stakeholder_context: Cross-BC stakeholder data dict.

        Returns:
            The persisted Message aggregate.
        """
        dag = DAGOrchestrator(
            steps=[
                WorkflowStep(
                    name="fetch_case_studies",
                    execute=self._fetch_case_studies,
                    timeout_seconds=30.0,
                ),
                WorkflowStep(
                    name="build_personalization",
                    execute=self._build_personalization,
                    depends_on=("fetch_case_studies",),
                ),
                WorkflowStep(
                    name="generate_via_ai",
                    execute=self._generate_via_ai,
                    depends_on=("build_personalization",),
                    timeout_seconds=60.0,
                ),
                WorkflowStep(
                    name="create_and_save",
                    execute=self._create_and_save,
                    depends_on=("generate_via_ai",),
                ),
            ]
        )

        context: dict[str, Any] = {
            "account_id": account_id,
            "stakeholder_id": stakeholder_id,
            "channel": channel,
            "tone": tone,
            "step_number": step_number,
            "account_context": account_context,
            "stakeholder_context": stakeholder_context,
        }

        results = await dag.execute(context)
        return results["create_and_save"]

    async def _fetch_case_studies(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> dict[str, Any]:
        """Step 1: Fetch case studies by industry and offering in parallel."""
        account_ctx = context["account_context"]
        industry = account_ctx.get("industry", "")
        offering = account_ctx.get("searce_offering", "")

        industry_studies = await self._case_study_port.find_by_industry(industry)
        offering_studies = await self._case_study_port.find_by_offering(offering)

        # Deduplicate by title
        seen_titles: set[str] = set()
        all_studies = []
        for study in (*industry_studies, *offering_studies):
            if study.title not in seen_titles:
                seen_titles.add(study.title)
                all_studies.append(study)

        return {"case_studies": tuple(all_studies)}

    async def _build_personalization(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> dict[str, Any]:
        """Step 2: Build PersonalizationContext from cross-BC data and case studies."""
        account_ctx = context["account_context"]
        stakeholder_ctx = context["stakeholder_context"]
        case_studies = completed["fetch_case_studies"]["case_studies"]

        personalization_context = self._personalization_service.build_context(
            company_name=account_ctx.get("company_name", ""),
            stakeholder_name=stakeholder_ctx.get("stakeholder_name", ""),
            job_title=stakeholder_ctx.get("job_title", ""),
            buying_signals=tuple(account_ctx.get("buying_signals", [])),
            tech_stack_summary=account_ctx.get("tech_stack_summary", ""),
            pain_points=tuple(account_ctx.get("pain_points", [])),
            case_studies=case_studies,
            offering=account_ctx.get("searce_offering", ""),
        )

        return {"personalization_context": personalization_context}

    async def _generate_via_ai(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> dict[str, Any]:
        """Step 3: Generate message content via the AI port."""
        channel = Channel(context["channel"])
        tone = Tone(context["tone"])
        step_number = context["step_number"]
        personalization_context = completed["build_personalization"][
            "personalization_context"
        ]

        template = MessageTemplate(
            template_id=f"{channel.value}_{tone.value}_step{step_number}",
            channel=channel,
            tone=tone,
            step_number=step_number,
            system_prompt=(
                f"Generate a {tone.value} {channel.value} message "
                f"for step {step_number}."
            ),
            example_output="",
        )

        generated = await self._ai_message_generator.generate(
            context=personalization_context,
            channel=channel,
            tone=tone,
            template=template,
        )

        return {"generated": generated, "channel": channel, "tone": tone}

    async def _create_and_save(
        self, context: dict[str, Any], completed: dict[str, Any]
    ) -> Message:
        """Step 4: Create Message entity, persist, and publish events."""
        generated = completed["generate_via_ai"]["generated"]
        channel = completed["generate_via_ai"]["channel"]
        tone = completed["generate_via_ai"]["tone"]
        personalization_context = completed["build_personalization"][
            "personalization_context"
        ]

        message_id = MessageId(str(uuid4()))
        event = MessageGeneratedEvent(
            aggregate_id=message_id,
            channel=channel.value,
            tone=tone.value,
            quality_score=generated.quality_score,
        )

        message = Message(
            message_id=message_id,
            account_id=AccountId(context["account_id"]),
            stakeholder_id=StakeholderId(context["stakeholder_id"]),
            channel=channel,
            tone=tone,
            subject=generated.subject,
            body=generated.body,
            call_to_action=generated.call_to_action,
            personalization_context=personalization_context,
            quality_score=generated.quality_score,
            status=MessageStatus.DRAFT,
            domain_events=(event,),
        )

        await self._message_repository.save(message)
        if message.domain_events:
            await self._event_bus.publish(message.domain_events)

        return message
