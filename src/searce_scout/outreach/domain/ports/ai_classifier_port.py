"""Port for AI-powered reply classification."""

from __future__ import annotations

from typing import Protocol

from searce_scout.outreach.domain.value_objects.reply_classification import (
    ReplyClassification,
)


class AIClassifierPort(Protocol):
    """Driven port for classifying stakeholder replies using AI.

    Infrastructure adapters implement this to integrate with LLM
    providers for intent classification.
    """

    async def classify_reply(
        self,
        raw_content: str,
    ) -> tuple[ReplyClassification, float]:
        """Classify a raw reply into a ReplyClassification.

        Args:
            raw_content: The full text content of the reply.

        Returns:
            A tuple of (classification, confidence) where confidence
            is a float in [0.0, 1.0].
        """
        ...
