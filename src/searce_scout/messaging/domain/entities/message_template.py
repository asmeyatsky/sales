"""Message template entity."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.messaging.domain.value_objects.channel import Channel
from searce_scout.messaging.domain.value_objects.tone import Tone


@dataclass(frozen=True)
class MessageTemplate:
    """A template that guides AI message generation for a specific
    channel, tone, and sequence step.
    """

    template_id: str
    channel: Channel
    tone: Tone
    step_number: int
    system_prompt: str
    example_output: str
