"""
GenerateDeckCommand and handler.

Orchestrates full deck generation: AI content creation, domain composition,
slide rendering, and persistence — delegating to DeckGenerationWorkflow.
"""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort

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

from searce_scout.presentation_gen.application.dtos.presentation_dtos import DeckDTO
from searce_scout.presentation_gen.application.orchestration.deck_generation_workflow import (
    DeckGenerationWorkflow,
)


@dataclass(frozen=True)
class GenerateDeckCommand:
    account_id: str
    offering: str | None = None
    template_id: str = ""


class GenerateDeckHandler:
    """Handles GenerateDeckCommand by delegating to the deck generation workflow."""

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

    async def execute(
        self, cmd: GenerateDeckCommand, account_context: dict
    ) -> DeckDTO:
        """Generate a full sales deck for the given account.

        *account_context* carries research data from BC1 (Account Research),
        passed cross-BC by the calling layer.
        """
        workflow = DeckGenerationWorkflow(
            ai_content_generator=self._ai_content_generator,
            slide_renderer=self._slide_renderer,
            deck_repository=self._deck_repository,
            deck_composition_service=self._deck_composition_service,
            event_bus=self._event_bus,
        )

        deck = await workflow.run(
            account_id=cmd.account_id,
            offering=cmd.offering or "",
            template_id=cmd.template_id,
            account_context=account_context,
        )

        return DeckDTO.from_domain(deck)
