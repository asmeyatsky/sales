"""Command and handler for generating a personalized outreach message."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import AccountId, MessageId, StakeholderId

from searce_scout.messaging.application.dtos.message_dtos import MessageDTO
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


@dataclass(frozen=True)
class GenerateMessageCommand:
    account_id: str
    stakeholder_id: str
    channel: str
    tone: str
    step_number: int


class GenerateMessageHandler:
    """Orchestrates message generation from context assembly through persistence."""

    def __init__(
        self,
        ai_message_generator: AIMessageGeneratorPort,
        case_study_port: CaseStudyPort,
        message_repository: MessageRepositoryPort,
        event_bus: EventBusPort,
        personalization_service: PersonalizationService,
    ) -> None:
        self._ai_message_generator = ai_message_generator
        self._case_study_port = case_study_port
        self._message_repository = message_repository
        self._event_bus = event_bus
        self._personalization_service = personalization_service

    async def execute(
        self,
        cmd: GenerateMessageCommand,
        account_context: dict,
        stakeholder_context: dict,
    ) -> MessageDTO:
        """Generate a personalized message and persist it.

        Args:
            cmd: The generation command with channel, tone, and step info.
            account_context: Cross-BC account data as a dict for decoupling.
                Expected keys: company_name, industry, tech_stack_summary,
                buying_signals, pain_points, searce_offering.
            stakeholder_context: Cross-BC stakeholder data as a dict.
                Expected keys: stakeholder_name, job_title.

        Returns:
            A MessageDTO representing the newly generated message.
        """
        channel = Channel(cmd.channel)
        tone = Tone(cmd.tone)

        # Find relevant case studies by industry and offering
        industry = account_context.get("industry", "")
        offering = account_context.get("searce_offering", "")

        industry_studies = await self._case_study_port.find_by_industry(industry)
        offering_studies = await self._case_study_port.find_by_offering(offering)

        # Deduplicate case studies by title
        seen_titles: set[str] = set()
        all_studies = []
        for study in (*industry_studies, *offering_studies):
            if study.title not in seen_titles:
                seen_titles.add(study.title)
                all_studies.append(study)
        case_studies = tuple(all_studies)

        # Build personalization context from cross-BC data
        personalization_context = self._personalization_service.build_context(
            company_name=account_context.get("company_name", ""),
            stakeholder_name=stakeholder_context.get("stakeholder_name", ""),
            job_title=stakeholder_context.get("job_title", ""),
            buying_signals=tuple(account_context.get("buying_signals", [])),
            tech_stack_summary=account_context.get("tech_stack_summary", ""),
            pain_points=tuple(account_context.get("pain_points", [])),
            case_studies=case_studies,
            offering=offering,
        )

        # Find or create a template for the channel+tone+step combination
        template = MessageTemplate(
            template_id=f"{channel.value}_{tone.value}_step{cmd.step_number}",
            channel=channel,
            tone=tone,
            step_number=cmd.step_number,
            system_prompt=f"Generate a {tone.value} {channel.value} message for step {cmd.step_number}.",
            example_output="",
        )

        # Generate message content via AI
        generated = await self._ai_message_generator.generate(
            context=personalization_context,
            channel=channel,
            tone=tone,
            template=template,
        )

        # Create the Message aggregate
        message_id = MessageId(str(uuid4()))
        event = MessageGeneratedEvent(
            aggregate_id=message_id,
            channel=channel.value,
            tone=tone.value,
            quality_score=generated.quality_score,
        )
        message = Message(
            message_id=message_id,
            account_id=AccountId(cmd.account_id),
            stakeholder_id=StakeholderId(cmd.stakeholder_id),
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

        # Persist and publish
        await self._message_repository.save(message)
        if message.domain_events:
            await self._event_bus.publish(message.domain_events)

        return MessageDTO.from_domain(message)
