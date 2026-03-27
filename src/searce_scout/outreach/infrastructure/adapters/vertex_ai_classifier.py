"""Vertex AI reply classifier adapter — implements AIClassifierPort.

Uses Google Cloud Vertex AI (Gemini) to classify the intent of email
and LinkedIn replies from outreach recipients, returning a
ReplyClassification enum and a confidence score.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from searce_scout.outreach.domain.ports.ai_classifier_port import AIClassifierPort
from searce_scout.outreach.domain.value_objects.reply_classification import (
    ReplyClassification,
)

_VALID_CLASSIFICATIONS = {e.value for e in ReplyClassification}


# ---------------------------------------------------------------------------
# Pydantic response schema
# ---------------------------------------------------------------------------


class _ClassificationResponse(BaseModel):
    """Structured output schema for reply classification."""

    classification: str = Field(
        description=(
            "One of: ooo, not_interested, positive, neutral, unsubscribe, bounce"
        )
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0",
        ge=0.0,
        le=1.0,
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of why this classification was chosen",
    )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class VertexAIClassifier:
    """Classifies outreach reply intent via Vertex AI Gemini.

    Implements :class:`AIClassifierPort`.
    """

    def __init__(
        self,
        *,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "gemini-1.5-pro",
    ) -> None:
        self._project_id = project_id
        self._location = location
        self._model_name = model_name
        self._model = self._init_model()

    def _init_model(self):  # type: ignore[no-untyped-def]
        """Initialize the Vertex AI GenerativeModel."""
        import vertexai
        from vertexai.generative_models import GenerativeModel

        vertexai.init(project=self._project_id, location=self._location)
        return GenerativeModel(self._model_name)

    # ------------------------------------------------------------------
    # AIClassifierPort implementation
    # ------------------------------------------------------------------

    async def classify_reply(
        self, raw_content: str
    ) -> tuple[ReplyClassification, float]:
        """Classify a raw reply into a ReplyClassification with confidence."""
        prompt = self._build_prompt(raw_content)
        response_text = await self._generate(prompt)
        parsed = self._parse_response(response_text)

        # Safely map to enum, defaulting to NEUTRAL on unknown values
        classification_value = parsed.classification.lower()
        if classification_value in _VALID_CLASSIFICATIONS:
            classification = ReplyClassification(classification_value)
        else:
            classification = ReplyClassification.NEUTRAL

        confidence = max(0.0, min(1.0, parsed.confidence))
        return classification, confidence

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(raw_content: str) -> str:
        """Build the classification prompt."""
        return (
            "You are an expert at classifying replies to B2B sales outreach emails.\n"
            "Analyze the following reply and classify it into exactly one category.\n\n"
            "Categories:\n"
            "- ooo: Out-of-office / auto-reply indicating the person is unavailable\n"
            "- not_interested: Explicit decline, rejection, or lack of interest\n"
            "- positive: Interest in learning more, scheduling a meeting, or discussing further\n"
            "- neutral: Acknowledgment without clear intent (e.g., 'thanks', 'noted')\n"
            "- unsubscribe: Request to stop receiving messages or be removed from list\n"
            "- bounce: Delivery failure, invalid address, or mailbox-full notification\n\n"
            "Respond ONLY with valid JSON:\n"
            '{"classification": "<category>", "confidence": <0.0-1.0>, "reasoning": "<brief explanation>"}\n\n'
            f"Reply content:\n---\n{raw_content}\n---"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _generate(self, prompt: str) -> str:
        """Call Gemini and return the raw text response."""
        response = await self._model.generate_content_async(prompt)
        return response.text

    @staticmethod
    def _parse_response(text: str) -> _ClassificationResponse:
        """Parse JSON from the model output into the response schema."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)
        data = json.loads(cleaned)
        return _ClassificationResponse.model_validate(data)


# Structural compatibility assertion
def _check_port_compliance() -> None:
    _: AIClassifierPort = VertexAIClassifier(  # type: ignore[assignment]
        project_id="test"
    )
