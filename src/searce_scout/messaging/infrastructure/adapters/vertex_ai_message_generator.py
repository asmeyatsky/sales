"""Vertex AI message generator adapter — implements AIMessageGeneratorPort.

Uses Google Cloud Vertex AI (Gemini 1.5 Pro) to generate personalized
outreach messages.  Builds a detailed prompt incorporating company context,
buying signals, case studies, tone instructions, and channel-specific
constraints, then parses the structured output into a GeneratedMessage.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from searce_scout.messaging.domain.entities.message_template import MessageTemplate
from searce_scout.messaging.domain.ports.ai_message_generator_port import (
    AIMessageGeneratorPort,
)
from searce_scout.messaging.domain.value_objects.channel import Channel
from searce_scout.messaging.domain.value_objects.message_content import GeneratedMessage
from searce_scout.messaging.domain.value_objects.personalization import (
    PersonalizationContext,
)
from searce_scout.messaging.domain.value_objects.tone import Tone

# ---------------------------------------------------------------------------
# Channel length constraints
# ---------------------------------------------------------------------------

_CHANNEL_CONSTRAINTS: dict[Channel, dict[str, int | str]] = {
    Channel.LINKEDIN_REQUEST: {
        "max_chars": 300,
        "instruction": "Keep the message under 300 characters. Be concise and compelling.",
    },
    Channel.LINKEDIN_MESSAGE: {
        "max_chars": 1000,
        "instruction": "Keep the message under 1000 characters. Be professional but personalized.",
    },
    Channel.EMAIL: {
        "max_chars": 3000,
        "instruction": (
            "Write a complete email with subject line. Body should be 3-5 short paragraphs. "
            "Include a clear call-to-action."
        ),
    },
    Channel.PHONE_SCRIPT: {
        "max_chars": 2000,
        "instruction": (
            "Create a phone call script with talking points. Include an opening hook, "
            "3-4 key talking points, objection handlers, and a close."
        ),
    },
}

# ---------------------------------------------------------------------------
# Tone instructions
# ---------------------------------------------------------------------------

_TONE_INSTRUCTIONS: dict[Tone, str] = {
    Tone.PROFESSIONAL_CONSULTANT: (
        "Use a formal, consultative tone. Position yourself as a trusted advisor "
        "who understands their business challenges. Avoid slang and keep language "
        "polished and authoritative."
    ),
    Tone.WITTY_TECH_PARTNER: (
        "Use a conversational, clever tone. Be relatable and show personality. "
        "Use light humor where appropriate but stay professional. Think 'smart friend "
        "who happens to be a tech expert'."
    ),
}


# ---------------------------------------------------------------------------
# Pydantic response schema
# ---------------------------------------------------------------------------


class _MessageResponse(BaseModel):
    """Structured output schema for a generated message."""

    subject: str | None = Field(
        default=None,
        description="Email subject line (null for non-email channels)",
    )
    body: str = Field(description="The main message body")
    call_to_action: str = Field(
        description="A specific, actionable CTA for the recipient"
    )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class VertexAIMessageGenerator:
    """Generates personalized outreach messages via Vertex AI Gemini.

    Implements :class:`AIMessageGeneratorPort`.
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
    # AIMessageGeneratorPort implementation
    # ------------------------------------------------------------------

    async def generate(
        self,
        context: PersonalizationContext,
        channel: Channel,
        tone: Tone,
        template: MessageTemplate,
    ) -> GeneratedMessage:
        """Generate a personalized message using Gemini."""
        prompt = self._build_prompt(context, channel, tone, template)
        response_text = await self._generate(prompt)
        parsed = self._parse_response(response_text)
        quality_score = self._compute_quality_score(context, parsed)

        return GeneratedMessage(
            subject=parsed.subject,
            body=parsed.body,
            call_to_action=parsed.call_to_action,
            quality_score=quality_score,
        )

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(
        context: PersonalizationContext,
        channel: Channel,
        tone: Tone,
        template: MessageTemplate,
    ) -> str:
        """Build a comprehensive prompt from all context elements."""
        channel_info = _CHANNEL_CONSTRAINTS.get(
            channel,
            {"max_chars": 2000, "instruction": "Write a professional message."},
        )
        tone_instruction = _TONE_INSTRUCTIONS.get(tone, "Be professional.")

        # Case study references
        case_study_lines: list[str] = []
        for cs in context.relevant_case_studies:
            case_study_lines.append(
                f"  - {cs.title} ({cs.industry}): {cs.outcome_summary} — Key metric: {cs.metric}"
            )
        case_studies_block = (
            "\n".join(case_study_lines) if case_study_lines else "  (none available)"
        )

        # Buying signals
        signals_block = "\n".join(
            f"  - {s}" for s in context.buying_signals
        ) if context.buying_signals else "  (none detected)"

        # Pain points
        pain_block = "\n".join(
            f"  - {p}" for p in context.pain_points
        ) if context.pain_points else "  (none identified)"

        prompt = (
            f"### SYSTEM\n{template.system_prompt}\n\n"
            f"### TONE\n{tone_instruction}\n\n"
            f"### CHANNEL: {channel.value}\n{channel_info['instruction']}\n\n"
            f"### RECIPIENT CONTEXT\n"
            f"Company: {context.company_name}\n"
            f"Stakeholder: {context.stakeholder_name}\n"
            f"Title: {context.job_title}\n"
            f"Tech stack: {context.tech_stack_summary}\n"
            f"Searce offering: {context.searce_offering}\n\n"
            f"### BUYING SIGNALS\n{signals_block}\n\n"
            f"### PAIN POINTS\n{pain_block}\n\n"
            f"### RELEVANT CASE STUDIES\n{case_studies_block}\n\n"
            f"### OUTPUT FORMAT\n"
            f"Respond ONLY with valid JSON:\n"
            f'{{"subject": "<subject or null>", "body": "<message body>", '
            f'"call_to_action": "<specific CTA>"}}\n\n'
            f"### EXAMPLE OUTPUT\n{template.example_output}"
        )
        return prompt

    # ------------------------------------------------------------------
    # Quality scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_quality_score(
        context: PersonalizationContext, response: _MessageResponse
    ) -> float:
        """Heuristic quality score based on how many context elements appear in output."""
        body_lower = response.body.lower()
        total_elements = 0
        used_elements = 0

        # Check company name
        total_elements += 1
        if context.company_name.lower() in body_lower:
            used_elements += 1

        # Check stakeholder name
        total_elements += 1
        if context.stakeholder_name.lower() in body_lower:
            used_elements += 1

        # Check buying signals
        for signal in context.buying_signals:
            total_elements += 1
            # Check if a meaningful fragment of the signal appears
            words = signal.lower().split()
            key_words = [w for w in words if len(w) > 4]
            if any(kw in body_lower for kw in key_words):
                used_elements += 1

        # Check pain points
        for pain in context.pain_points:
            total_elements += 1
            words = pain.lower().split()
            key_words = [w for w in words if len(w) > 4]
            if any(kw in body_lower for kw in key_words):
                used_elements += 1

        # Check case studies
        for cs in context.relevant_case_studies:
            total_elements += 1
            if cs.title.lower() in body_lower or cs.metric.lower() in body_lower:
                used_elements += 1

        # Check offering
        total_elements += 1
        if context.searce_offering.lower() in body_lower:
            used_elements += 1

        if total_elements == 0:
            return 0.5

        return round(used_elements / total_elements, 2)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _generate(self, prompt: str) -> str:
        """Call Gemini and return the raw text response."""
        response = await self._model.generate_content_async(prompt)
        return response.text

    @staticmethod
    def _parse_response(text: str) -> _MessageResponse:
        """Parse JSON from the model response into the response schema."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)
        data = json.loads(cleaned)
        return _MessageResponse.model_validate(data)


# Structural compatibility assertion
def _check_port_compliance() -> None:
    _: AIMessageGeneratorPort = VertexAIMessageGenerator(  # type: ignore[assignment]
        project_id="test"
    )
