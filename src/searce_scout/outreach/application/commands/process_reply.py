"""Command and handler for processing and classifying a reply."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.errors import DomainError
from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import SequenceId

from searce_scout.outreach.application.dtos.outreach_dtos import OutreachSequenceDTO
from searce_scout.outreach.domain.events.outreach_events import ReplyReceivedEvent
from searce_scout.outreach.domain.ports.ai_classifier_port import AIClassifierPort
from searce_scout.outreach.domain.ports.sequence_repository_port import (
    SequenceRepositoryPort,
)
from searce_scout.outreach.domain.services.reply_classification_service import (
    ReplyClassificationService,
)


@dataclass(frozen=True)
class ProcessReplyCommand:
    sequence_id: str
    raw_content: str


class ProcessReplyHandler:
    """Classifies a reply and applies the appropriate action to the sequence."""

    def __init__(
        self,
        ai_classifier: AIClassifierPort,
        reply_classification_service: ReplyClassificationService,
        sequence_repository: SequenceRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._ai_classifier = ai_classifier
        self._reply_classification_service = reply_classification_service
        self._sequence_repository = sequence_repository
        self._event_bus = event_bus

    async def execute(self, cmd: ProcessReplyCommand) -> OutreachSequenceDTO:
        """Classify a reply and apply the resulting action to the sequence.

        Args:
            cmd: The command containing the sequence ID and raw reply content.

        Returns:
            An OutreachSequenceDTO reflecting the updated sequence state.

        Raises:
            DomainError: If the sequence is not found.
        """
        sequence = await self._sequence_repository.get_by_id(
            SequenceId(cmd.sequence_id)
        )
        if sequence is None:
            raise DomainError(f"Sequence not found: {cmd.sequence_id}")

        # Classify the reply via AI
        classification, confidence = await self._ai_classifier.classify_reply(
            cmd.raw_content
        )

        # Record the reply received event
        reply_event = ReplyReceivedEvent(
            aggregate_id=sequence.sequence_id,
            classification=classification.value,
            confidence=confidence,
        )

        # Determine action based on classification
        if self._reply_classification_service.should_stop_sequence(classification):
            reason = f"Reply classified as {classification.value} (confidence: {confidence:.2f})"
            sequence = sequence.stop(reason)
        elif self._reply_classification_service.should_pause_sequence(classification):
            sequence = sequence.pause()

        # Append the reply event to the sequence's domain events
        from dataclasses import replace
        sequence = replace(
            sequence,
            domain_events=sequence.domain_events + (reply_event,),
        )

        # Persist and publish all events
        await self._sequence_repository.save(sequence)
        if sequence.domain_events:
            await self._event_bus.publish(sequence.domain_events)

        return OutreachSequenceDTO.from_domain(sequence)
