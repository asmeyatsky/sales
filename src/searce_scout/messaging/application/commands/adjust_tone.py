"""Command and handler for adjusting the tone of an existing message."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.errors import DomainError
from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import MessageId

from searce_scout.messaging.application.dtos.message_dtos import MessageDTO
from searce_scout.messaging.domain.entities.message_template import MessageTemplate
from searce_scout.messaging.domain.ports.ai_message_generator_port import (
    AIMessageGeneratorPort,
)
from searce_scout.messaging.domain.ports.message_repository_port import (
    MessageRepositoryPort,
)
from searce_scout.messaging.domain.value_objects.tone import Tone


@dataclass(frozen=True)
class AdjustToneCommand:
    message_id: str
    new_tone: str


class AdjustToneHandler:
    """Regenerates a message with a new tone using the AI engine."""

    def __init__(
        self,
        ai_message_generator: AIMessageGeneratorPort,
        message_repository: MessageRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._ai_message_generator = ai_message_generator
        self._message_repository = message_repository
        self._event_bus = event_bus

    async def execute(self, cmd: AdjustToneCommand) -> MessageDTO:
        """Load a message, regenerate it with a new tone, and persist.

        Args:
            cmd: The tone adjustment command.

        Returns:
            A MessageDTO representing the updated message.

        Raises:
            DomainError: If the message is not found.
        """
        message = await self._message_repository.get_by_id(
            MessageId(cmd.message_id)
        )
        if message is None:
            raise DomainError(f"Message not found: {cmd.message_id}")

        new_tone = Tone(cmd.new_tone)

        # Build a template for regeneration with the new tone
        template = MessageTemplate(
            template_id=f"{message.channel.value}_{new_tone.value}_step_retone",
            channel=message.channel,
            tone=new_tone,
            step_number=1,
            system_prompt=f"Regenerate this message with a {new_tone.value} tone.",
            example_output="",
        )

        # Regenerate via AI with the new tone
        generated = await self._ai_message_generator.generate(
            context=message.personalization_context,
            channel=message.channel,
            tone=new_tone,
            template=template,
        )

        # Apply the tone adjustment on the domain entity
        updated_message = message.adjust_tone(
            new_tone=new_tone,
            new_body=generated.body,
        )

        # Persist and publish
        await self._message_repository.save(updated_message)
        if updated_message.domain_events:
            await self._event_bus.publish(updated_message.domain_events)

        return MessageDTO.from_domain(updated_message)
