"""
DeckGenerationWorkflow — DAG-orchestrated deck creation.

Parallelises independent content-generation steps, then sequences
composition, rendering, and persistence using the shared DAGOrchestrator.

Step graph:
  generate_hook ─┐
  generate_gap  ──┤── compose_deck ── render_slides ── save_deck
  find_cases   ──┘
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from searce_scout.shared_kernel.orchestration.dag_orchestrator import (
    DAGOrchestrator,
    WorkflowStep,
)
from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import AccountId, DeckId

from searce_scout.presentation_gen.domain.entities.slide_deck import SlideDeck
from searce_scout.presentation_gen.domain.events.presentation_events import (
    DeckGeneratedEvent,
)
from searce_scout.presentation_gen.domain.ports.ai_content_generator_port import (
    AIContentGeneratorPort,
)
from searce_scout.presentation_gen.domain.ports.deck_repository_port import (
    DeckRepositoryPort,
)
from searce_scout.presentation_gen.domain.ports.slide_renderer_port import (
    SlideRendererPort,
)
from searce_scout.presentation_gen.domain.services.deck_composition import (
    DeckCompositionService,
)
from searce_scout.presentation_gen.domain.value_objects.deck_content import (
    CaseStudyReference,
)
from searce_scout.presentation_gen.domain.value_objects.template_id import TemplateId


class DeckGenerationWorkflow:
    """Orchestrates end-to-end deck generation via a DAG of async steps."""

    def __init__(
        self,
        ai_content_generator: AIContentGeneratorPort,
        slide_renderer: SlideRendererPort,
        deck_repository: DeckRepositoryPort,
        deck_composition_service: DeckCompositionService,
        event_bus: EventBusPort,
    ) -> None:
        self._ai_content_generator = ai_content_generator
        self._slide_renderer = slide_renderer
        self._deck_repository = deck_repository
        self._deck_composition_service = deck_composition_service
        self._event_bus = event_bus

    async def run(
        self,
        account_id: str,
        offering: str,
        template_id: str,
        account_context: dict,
    ) -> SlideDeck:
        """Execute the full workflow and return the persisted SlideDeck."""

        # ------------------------------------------------------------------
        # Step functions — each receives (context, completed) per DAGOrchestrator
        # ------------------------------------------------------------------

        async def generate_hook(
            context: dict[str, Any], _completed: dict[str, Any]
        ) -> Any:
            account_data = context.get("account_data", "")
            signals = context.get("signals", "")
            return await self._ai_content_generator.generate_hook(
                account_data=account_data,
                signals=signals,
            )

        async def generate_gap(
            context: dict[str, Any], _completed: dict[str, Any]
        ) -> Any:
            tech_stack = context.get("tech_stack", "")
            return await self._ai_content_generator.generate_gap_analysis(
                tech_stack=tech_stack,
                offering=context["offering"],
            )

        async def find_case_studies(
            context: dict[str, Any], _completed: dict[str, Any]
        ) -> Any:
            raw = context.get("case_studies", [])
            return tuple(
                CaseStudyReference(
                    title=cs.get("title", ""),
                    industry=cs.get("industry", ""),
                    outcome_summary=cs.get("outcome_summary", ""),
                    metric=cs.get("metric", ""),
                )
                for cs in raw
            )

        async def compose_deck(
            context: dict[str, Any], completed: dict[str, Any]
        ) -> Any:
            hook = completed["generate_hook"]
            gap = completed["generate_gap"]
            case_studies = completed["find_case_studies"]
            return self._deck_composition_service.compose(
                hook=hook,
                gap=gap,
                case_studies=case_studies,
                offering=context["offering"],
                company_name=context.get("company_name", ""),
            )

        async def render_slides(
            context: dict[str, Any], completed: dict[str, Any]
        ) -> Any:
            slides = completed["compose_deck"]
            tid = TemplateId(google_slides_id=context["template_id"])
            return await self._slide_renderer.create_from_template(
                template_id=tid,
                slides=slides,
            )

        async def save_deck(
            context: dict[str, Any], completed: dict[str, Any]
        ) -> Any:
            slides = completed["compose_deck"]
            url = completed["render_slides"]
            now = datetime.now(UTC)
            deck_id = DeckId(str(uuid4()))

            deck = SlideDeck(
                deck_id=deck_id,
                account_id=AccountId(context["account_id"]),
                slides=slides,
                template_id=TemplateId(google_slides_id=context["template_id"]),
                generated_at=now,
            )

            deck = deck.set_exported(url)

            generated_event = DeckGeneratedEvent(
                aggregate_id=deck_id,
                slide_count=deck.slide_count(),
            )
            deck_with_events = SlideDeck(
                deck_id=deck.deck_id,
                account_id=deck.account_id,
                slides=deck.slides,
                template_id=deck.template_id,
                google_slides_url=deck.google_slides_url,
                generated_at=deck.generated_at,
                exported_at=deck.exported_at,
                domain_events=deck.domain_events + (generated_event,),
            )

            await self._deck_repository.save(deck_with_events)
            await self._event_bus.publish(deck_with_events.domain_events)
            return deck_with_events

        # ------------------------------------------------------------------
        # Build the DAG and execute
        # ------------------------------------------------------------------

        steps = [
            WorkflowStep(name="generate_hook", execute=generate_hook),
            WorkflowStep(name="generate_gap", execute=generate_gap),
            WorkflowStep(name="find_case_studies", execute=find_case_studies),
            WorkflowStep(
                name="compose_deck",
                execute=compose_deck,
                depends_on=("generate_hook", "generate_gap", "find_case_studies"),
            ),
            WorkflowStep(
                name="render_slides",
                execute=render_slides,
                depends_on=("compose_deck",),
            ),
            WorkflowStep(
                name="save_deck",
                execute=save_deck,
                depends_on=("render_slides",),
            ),
        ]

        orchestrator = DAGOrchestrator(steps)

        context: dict[str, Any] = {
            "account_id": account_id,
            "offering": offering,
            "template_id": template_id,
            "company_name": account_context.get("company_name", ""),
            "account_data": account_context.get("account_data", ""),
            "signals": account_context.get("signals", ""),
            "tech_stack": account_context.get("tech_stack", ""),
            "case_studies": account_context.get("case_studies", []),
        }

        results = await orchestrator.execute(context)
        return results["save_deck"]
