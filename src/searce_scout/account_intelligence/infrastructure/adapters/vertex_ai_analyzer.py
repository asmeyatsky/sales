"""Vertex AI analyzer adapter — implements AIAnalyzerPort.

Uses Google Cloud Vertex AI (Gemini generative models) to extract buying
signals from raw research text and classify company industries.  Structured
output is parsed via lightweight Pydantic response schemas.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from searce_scout.account_intelligence.domain.entities.buying_signal import (
    BuyingSignal,
)
from searce_scout.account_intelligence.domain.ports.ai_analyzer_port import (
    AIAnalyzerPort,
)
from searce_scout.account_intelligence.domain.value_objects.industry import Industry
from searce_scout.account_intelligence.domain.value_objects.signal_type import (
    SignalStrength,
    SignalType,
)

# ---------------------------------------------------------------------------
# Pydantic response schemas for structured Gemini output
# ---------------------------------------------------------------------------

_VALID_SIGNAL_TYPES = {e.value for e in SignalType}
_VALID_STRENGTHS = {e.value for e in SignalStrength}


class _SignalResponse(BaseModel):
    """Schema for a single buying signal extracted by Gemini."""

    signal_type: str = Field(
        description="One of: NEW_EXECUTIVE, HIRING_SPREE, DIGITAL_TRANSFORMATION_GOAL, "
        "CLOUD_MIGRATION_MENTION, FUNDING_ROUND, TECH_DEBT_COMPLAINT, VENDOR_CONTRACT_EXPIRY"
    )
    strength: str = Field(description="One of: WEAK, MODERATE, STRONG, CRITICAL")
    description: str = Field(description="Brief explanation of the signal")
    source_url: str | None = Field(
        default=None, description="URL where the signal was found, if available"
    )


class _ExtractSignalsResponse(BaseModel):
    """Top-level schema for the extract_signals prompt."""

    signals: list[_SignalResponse] = Field(default_factory=list)


class _IndustryResponse(BaseModel):
    """Schema for industry classification output."""

    name: str = Field(description="Industry name, e.g. 'Financial Services'")
    vertical: str = Field(description="Vertical within the industry, e.g. 'Banking'")


class VertexAIAnalyzer:
    """Analyzes raw research data using Vertex AI Gemini models.

    Implements :class:`AIAnalyzerPort`.
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
        """Lazily initialize the Vertex AI GenerativeModel."""
        import vertexai
        from vertexai.generative_models import GenerativeModel

        vertexai.init(project=self._project_id, location=self._location)
        return GenerativeModel(self._model_name)

    # ------------------------------------------------------------------
    # AIAnalyzerPort implementation
    # ------------------------------------------------------------------

    async def extract_signals(
        self, raw_data: str
    ) -> tuple[BuyingSignal, ...]:
        """Send raw research text to Gemini and parse buying signals."""
        prompt = self._build_extract_signals_prompt(raw_data)
        response_text = await self._generate(prompt)
        parsed = self._parse_json_response(response_text, _ExtractSignalsResponse)

        signals: list[BuyingSignal] = []
        for item in parsed.signals:
            signal_type = self._safe_enum(SignalType, item.signal_type, _VALID_SIGNAL_TYPES)
            strength = self._safe_enum(SignalStrength, item.strength, _VALID_STRENGTHS)
            if signal_type is None or strength is None:
                continue

            source_url = None
            if item.source_url:
                from searce_scout.shared_kernel.value_objects import URL

                try:
                    source_url = URL(value=item.source_url)
                except Exception:
                    source_url = None

            signals.append(
                BuyingSignal(
                    signal_id=str(uuid.uuid4()),
                    signal_type=signal_type,
                    strength=strength,
                    description=item.description,
                    source_url=source_url,
                    detected_at=datetime.now(tz=timezone.utc),
                )
            )

        return tuple(signals)

    async def classify_industry(
        self, company_name: str, description: str
    ) -> Industry:
        """Ask Gemini to classify a company into an industry vertical."""
        prompt = self._build_classify_industry_prompt(company_name, description)
        response_text = await self._generate(prompt)
        parsed = self._parse_json_response(response_text, _IndustryResponse)
        return Industry(name=parsed.name, vertical=parsed.vertical)

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_extract_signals_prompt(raw_data: str) -> str:
        return (
            "You are a B2B sales intelligence analyst specializing in cloud services.\n"
            "Analyze the following raw research data about a company and extract buying signals.\n\n"
            "For each signal, identify:\n"
            "- signal_type: one of NEW_EXECUTIVE, HIRING_SPREE, DIGITAL_TRANSFORMATION_GOAL, "
            "CLOUD_MIGRATION_MENTION, FUNDING_ROUND, TECH_DEBT_COMPLAINT, VENDOR_CONTRACT_EXPIRY\n"
            "- strength: one of WEAK, MODERATE, STRONG, CRITICAL\n"
            "- description: a concise explanation of the signal\n"
            "- source_url: the URL where this was found (if available)\n\n"
            "Respond ONLY with valid JSON in this format:\n"
            '{"signals": [{"signal_type": "...", "strength": "...", "description": "...", "source_url": null}]}\n\n'
            f"Raw data:\n{raw_data}"
        )

    @staticmethod
    def _build_classify_industry_prompt(
        company_name: str, description: str
    ) -> str:
        return (
            "You are an industry classification expert.\n"
            f"Classify the company '{company_name}' into an industry and vertical.\n\n"
            f"Company description:\n{description}\n\n"
            "Respond ONLY with valid JSON:\n"
            '{"name": "<Industry Name>", "vertical": "<Vertical>"}\n\n'
            "Examples of industries: Technology, Financial Services, Healthcare, "
            "Retail, Manufacturing, Energy, Media & Entertainment, etc.\n"
            "Examples of verticals: Banking, Insurance, E-commerce, SaaS, "
            "Pharmaceuticals, Oil & Gas, etc."
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _generate(self, prompt: str) -> str:
        """Call Gemini and return the text response."""
        response = await self._model.generate_content_async(prompt)
        return response.text

    @staticmethod
    def _parse_json_response(text: str, schema: type[BaseModel]) -> BaseModel:
        """Extract JSON from model output and parse into a Pydantic model."""
        # Strip markdown code fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last lines (fences)
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        data = json.loads(cleaned)
        return schema.model_validate(data)

    @staticmethod
    def _safe_enum(
        enum_cls: type, value: str, valid_values: set[str]
    ):  # type: ignore[no-untyped-def]
        """Safely convert a string to an enum member, returning None if invalid."""
        if value not in valid_values:
            return None
        return enum_cls(value)


# Structural compatibility assertion
def _check_port_compliance() -> None:
    _: AIAnalyzerPort = VertexAIAnalyzer(  # type: ignore[assignment]
        project_id="test"
    )
