"""Port for AI-powered message generation."""

from __future__ import annotations

from typing import Protocol

from searce_scout.messaging.domain.entities.message_template import MessageTemplate
from searce_scout.messaging.domain.value_objects.channel import Channel
from searce_scout.messaging.domain.value_objects.message_content import GeneratedMessage
from searce_scout.messaging.domain.value_objects.personalization import (
    PersonalizationContext,
)
from searce_scout.messaging.domain.value_objects.tone import Tone


class AIMessageGeneratorPort(Protocol):
    """Driven port for AI message generation.

    Infrastructure adapters implement this protocol to integrate with
    LLM providers (e.g., Claude, GPT) for generating personalized
    outreach messages.
    """

    async def generate(
        self,
        context: PersonalizationContext,
        channel: Channel,
        tone: Tone,
        template: MessageTemplate,
    ) -> GeneratedMessage:
        """Generate a personalized message using AI.

        Args:
            context: Personalization data for the target stakeholder.
            channel: The delivery channel determining message format.
            tone: The desired communication tone.
            template: The template guiding generation.

        Returns:
            A GeneratedMessage with subject, body, CTA, and quality score.
        """
        ...
