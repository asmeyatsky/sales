"""Vertex AI content generator adapter — implements AIContentGeneratorPort.

Uses Google Cloud Vertex AI (Gemini) to generate presentation content
including attention-grabbing hooks and gap analyses for slide decks.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from searce_scout.presentation_gen.domain.ports.ai_content_generator_port import (
    AIContentGeneratorPort,
)
from searce_scout.presentation_gen.domain.value_objects.deck_content import (
    GapAnalysis,
    HookContent,
)


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------


class _HookResponse(BaseModel):
    """Structured output schema for hook content generation."""

    headline: str = Field(
        description="A compelling one-line headline that grabs attention"
    )
    key_insight: str = Field(
        description="A data-driven insight specific to the account"
    )
    supporting_data: str = Field(
        description="Supporting statistics or evidence for the insight"
    )


class _GapAnalysisResponse(BaseModel):
    """Structured output schema for gap analysis generation."""

    current_state: str = Field(
        description="Description of the account's current technology/process state"
    )
    future_state: str = Field(
        description="Description of the ideal future state with the proposed solution"
    )
    cost_of_inaction: str = Field(
        description="Quantified or qualified cost of not making the change"
    )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class VertexAIContentGenerator:
    """Generates presentation content via Vertex AI Gemini.

    Implements :class:`AIContentGeneratorPort`.
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
    # AIContentGeneratorPort implementation
    # ------------------------------------------------------------------

    async def generate_hook(
        self, account_data: str, signals: str
    ) -> HookContent:
        """Generate compelling hook content for the opening slide."""
        prompt = self._build_hook_prompt(account_data, signals)
        response_text = await self._generate(prompt)
        parsed = self._parse_json_response(response_text, _HookResponse)
        return HookContent(
            headline=parsed.headline,
            key_insight=parsed.key_insight,
            supporting_data=parsed.supporting_data,
        )

    async def generate_gap_analysis(
        self, tech_stack: str, offering: str
    ) -> GapAnalysis:
        """Generate a gap analysis comparing current state to proposed solution."""
        prompt = self._build_gap_analysis_prompt(tech_stack, offering)
        response_text = await self._generate(prompt)
        parsed = self._parse_json_response(response_text, _GapAnalysisResponse)
        return GapAnalysis(
            current_state=parsed.current_state,
            future_state=parsed.future_state,
            cost_of_inaction=parsed.cost_of_inaction,
        )

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_hook_prompt(account_data: str, signals: str) -> str:
        """Build the hook-generation prompt."""
        return (
            "You are an expert presentation designer for a Google Cloud Premier Partner.\n"
            "Create a compelling opening hook for a sales presentation.\n\n"
            "The hook should:\n"
            "- Lead with a provocative insight specific to this account\n"
            "- Reference their industry challenges or buying signals\n"
            "- Create urgency without being pushy\n"
            "- Be backed by data or a clear business impact\n\n"
            f"### ACCOUNT DATA\n{account_data}\n\n"
            f"### BUYING SIGNALS\n{signals}\n\n"
            "Respond ONLY with valid JSON:\n"
            '{"headline": "...", "key_insight": "...", "supporting_data": "..."}'
        )

    @staticmethod
    def _build_gap_analysis_prompt(tech_stack: str, offering: str) -> str:
        """Build the gap-analysis-generation prompt."""
        return (
            "You are a cloud solutions architect preparing a gap analysis slide.\n"
            "Compare the account's current technology stack to what they could achieve "
            "with the proposed Searce offering.\n\n"
            "The analysis should:\n"
            "- Accurately describe their current infrastructure limitations\n"
            "- Paint a compelling picture of the future state\n"
            "- Quantify or clearly articulate the cost of staying on the current path\n\n"
            f"### CURRENT TECH STACK\n{tech_stack}\n\n"
            f"### PROPOSED OFFERING\n{offering}\n\n"
            "Respond ONLY with valid JSON:\n"
            '{"current_state": "...", "future_state": "...", "cost_of_inaction": "..."}'
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _generate(self, prompt: str) -> str:
        """Call Gemini and return the raw text response."""
        response = await self._model.generate_content_async(prompt)
        return response.text

    @staticmethod
    def _parse_json_response(text: str, schema: type[BaseModel]) -> BaseModel:
        """Extract JSON from model output and parse into a Pydantic model."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)
        data = json.loads(cleaned)
        return schema.model_validate(data)


# Structural compatibility assertion
def _check_port_compliance() -> None:
    _: AIContentGeneratorPort = VertexAIContentGenerator(  # type: ignore[assignment]
        project_id="test"
    )
