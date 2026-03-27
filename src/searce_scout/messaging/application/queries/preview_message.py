"""Query and handler for previewing a message without persisting it."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from searce_scout.shared_kernel.types import AccountId, MessageId, StakeholderId

from searce_scout.messaging.application.dtos.message_dtos import MessageDTO
from searce_scout.messaging.domain.entities.message import Message
from searce_scout.messaging.domain.entities.message_template import MessageTemplate
from searce_scout.messaging.domain.ports.ai_message_generator_port import (
    AIMessageGeneratorPort,
)
from searce_scout.messaging.domain.ports.case_study_port import CaseStudyPort
from searce_scout.messaging.domain.services.personalization_service import (
    PersonalizationService,
)
from searce_scout.messaging.domain.value_objects.channel import Channel
from searce_scout.messaging.domain.value_objects.message_content import MessageStatus
from searce_scout.messaging.domain.value_objects.tone import Tone


@dataclass(frozen=True)
class PreviewMessageQuery:
    account_id: str
    stakeholder_id: str
    channel: str
    tone: str


class PreviewMessageHandler:
    """Generates a message preview without persisting it."""

    def __init__(
        self,
        ai_message_generator: AIMessageGeneratorPort,
        case_study_port: CaseStudyPort,
        personalization_service: PersonalizationService,
    ) -> None:
        self._ai_message_generator = ai_message_generator
        self._case_study_port = case_study_port
        self._personalization_service = personalization_service

    async def execute(
        self,
        query: PreviewMessageQuery,
        account_context: dict,
        stakeholder_context: dict,
    ) -> MessageDTO:
        """Generate a message preview (not persisted).

        Args:
            query: The preview query with channel and tone.
            account_context: Cross-BC account data as a dict.
                Expected keys: company_name, industry, tech_stack_summary,
                buying_signals, pain_points, searce_offering.
            stakeholder_context: Cross-BC stakeholder data as a dict.
                Expected keys: stakeholder_name, job_title.

        Returns:
            A MessageDTO representing the preview (not saved to repository).
        """
        channel = Channel(query.channel)
        tone = Tone(query.tone)

        industry = account_context.get("industry", "")
        offering = account_context.get("searce_offering", "")

        industry_studies = await self._case_study_port.find_by_industry(industry)
        offering_studies = await self._case_study_port.find_by_offering(offering)

        seen_titles: set[str] = set()
        all_studies = []
        for study in (*industry_studies, *offering_studies):
            if study.title not in seen_titles:
                seen_titles.add(study.title)
                all_studies.append(study)
        case_studies = tuple(all_studies)

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

        template = MessageTemplate(
            template_id=f"{channel.value}_{tone.value}_preview",
            channel=channel,
            tone=tone,
            step_number=1,
            system_prompt=f"Generate a {tone.value} {channel.value} message preview.",
            example_output="",
        )

        generated = await self._ai_message_generator.generate(
            context=personalization_context,
            channel=channel,
            tone=tone,
            template=template,
        )

        # Build a transient Message entity (not persisted)
        message = Message(
            message_id=MessageId(str(uuid4())),
            account_id=AccountId(query.account_id),
            stakeholder_id=StakeholderId(query.stakeholder_id),
            channel=channel,
            tone=tone,
            subject=generated.subject,
            body=generated.body,
            call_to_action=generated.call_to_action,
            personalization_context=personalization_context,
            quality_score=generated.quality_score,
            status=MessageStatus.DRAFT,
        )

        return MessageDTO.from_domain(message)
