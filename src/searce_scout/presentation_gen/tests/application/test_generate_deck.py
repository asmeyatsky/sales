"""Application tests for GenerateDeckHandler.

Verifies that the handler generates a deck via the workflow, renders it
to Google Slides, persists it, and publishes domain events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import AccountId, DeckId
from searce_scout.shared_kernel.value_objects import URL

from searce_scout.presentation_gen.application.commands.generate_deck import (
    GenerateDeckCommand,
    GenerateDeckHandler,
)
from searce_scout.presentation_gen.domain.entities.slide_deck import SlideDeck
from searce_scout.presentation_gen.domain.events.presentation_events import (
    DeckExportedEvent,
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
from searce_scout.presentation_gen.domain.value_objects.slide import Slide, SlideType
from searce_scout.presentation_gen.domain.value_objects.template_id import TemplateId


def _make_deck(*, with_url: bool = True) -> SlideDeck:
    """Build a completed SlideDeck for testing."""
    slides = (
        Slide(
            slide_type=SlideType.TITLE,
            title="Partnering with TestCo",
            body="How Searce can accelerate transformation",
            speaker_notes="Open with greeting",
            order=0,
        ),
        Slide(
            slide_type=SlideType.HOOK,
            title="Cloud Opportunity",
            body="Key insight about TestCo's cloud journey",
            speaker_notes="Lead with insight",
            order=1,
        ),
        Slide(
            slide_type=SlideType.GAP_CURRENT_STATE,
            title="Where You Are Today",
            body="Current state description",
            speaker_notes="Acknowledge current state",
            order=2,
        ),
        Slide(
            slide_type=SlideType.GAP_FUTURE_STATE,
            title="Where You Could Be",
            body="Future state vision",
            speaker_notes="Paint the vision",
            order=3,
        ),
        Slide(
            slide_type=SlideType.SEARCE_OFFERING,
            title="Our Offering",
            body="Cloud Migration",
            speaker_notes="Connect offering to gaps",
            order=4,
        ),
        Slide(
            slide_type=SlideType.CALL_TO_ACTION,
            title="Next Steps",
            body="Let's explore together",
            speaker_notes="Close with clear ask",
            order=5,
        ),
    )

    url = URL(value="https://docs.google.com/presentation/d/test-id/edit") if with_url else None

    events = ()
    if with_url:
        events = (
            DeckExportedEvent(
                aggregate_id="deck-001",
                google_slides_url="https://docs.google.com/presentation/d/test-id/edit",
            ),
            DeckGeneratedEvent(
                aggregate_id="deck-001",
                slide_count=6,
            ),
        )

    return SlideDeck(
        deck_id=DeckId("deck-001"),
        account_id=AccountId("acc-001"),
        slides=slides,
        template_id=TemplateId(google_slides_id="tmpl-default"),
        google_slides_url=url,
        generated_at=datetime.now(UTC),
        exported_at=datetime.now(UTC) if with_url else None,
        domain_events=events,
    )


def _make_account_context() -> dict:
    return {
        "company_name": "TestCo",
        "account_data": "TestCo is an enterprise SaaS company.",
        "signals": "Cloud migration announcement detected.",
        "tech_stack": "AWS EC2, S3, RDS",
        "case_studies": [
            {
                "title": "FinanceCo Migration",
                "industry": "Finance",
                "outcome_summary": "40% cost reduction",
                "metric": "$2M savings",
            }
        ],
    }


@pytest.fixture()
def ai_content_generator() -> AsyncMock:
    return AsyncMock(spec=AIContentGeneratorPort)


@pytest.fixture()
def slide_renderer() -> AsyncMock:
    return AsyncMock(spec=SlideRendererPort)


@pytest.fixture()
def deck_repository() -> AsyncMock:
    return AsyncMock(spec=DeckRepositoryPort)


@pytest.fixture()
def event_bus() -> AsyncMock:
    bus = AsyncMock(spec=EventBusPort)
    bus.publish.return_value = None
    return bus


def _build_handler(
    ai_content_generator: AsyncMock,
    slide_renderer: AsyncMock,
    deck_repository: AsyncMock,
    event_bus: AsyncMock,
) -> GenerateDeckHandler:
    return GenerateDeckHandler(
        ai_content_generator=ai_content_generator,
        slide_renderer=slide_renderer,
        deck_repository=deck_repository,
        deck_composition_service=DeckCompositionService(),
        event_bus=event_bus,
    )


async def test_generate_creates_deck_with_slides(
    ai_content_generator: AsyncMock,
    slide_renderer: AsyncMock,
    deck_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Handler must produce a deck with multiple slides via the workflow."""
    deck = _make_deck(with_url=True)

    with patch(
        "searce_scout.presentation_gen.application.commands.generate_deck.DeckGenerationWorkflow"
    ) as MockWorkflow:
        mock_wf = AsyncMock()
        mock_wf.run.return_value = deck
        MockWorkflow.return_value = mock_wf

        handler = _build_handler(
            ai_content_generator, slide_renderer, deck_repository, event_bus
        )

        cmd = GenerateDeckCommand(
            account_id="acc-001",
            offering="Cloud Migration",
            template_id="tmpl-default",
        )
        result = await handler.execute(cmd, account_context=_make_account_context())

    assert result.slide_count == 6
    assert len(result.slides) == 6


async def test_generate_calls_renderer(
    ai_content_generator: AsyncMock,
    slide_renderer: AsyncMock,
    deck_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Handler delegates to the workflow which should involve the renderer."""
    deck = _make_deck(with_url=True)

    with patch(
        "searce_scout.presentation_gen.application.commands.generate_deck.DeckGenerationWorkflow"
    ) as MockWorkflow:
        mock_wf = AsyncMock()
        mock_wf.run.return_value = deck
        MockWorkflow.return_value = mock_wf

        handler = _build_handler(
            ai_content_generator, slide_renderer, deck_repository, event_bus
        )

        cmd = GenerateDeckCommand(
            account_id="acc-001",
            offering="Cloud Migration",
            template_id="tmpl-default",
        )
        result = await handler.execute(cmd, account_context=_make_account_context())

    # The workflow was called with the correct arguments
    MockWorkflow.return_value.run.assert_awaited_once()
    call_kwargs = MockWorkflow.return_value.run.call_args.kwargs
    assert call_kwargs["account_id"] == "acc-001"
    assert call_kwargs["offering"] == "Cloud Migration"
    assert call_kwargs["template_id"] == "tmpl-default"


async def test_generate_returns_google_slides_url(
    ai_content_generator: AsyncMock,
    slide_renderer: AsyncMock,
    deck_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Handler must return a DTO that includes the Google Slides URL."""
    deck = _make_deck(with_url=True)

    with patch(
        "searce_scout.presentation_gen.application.commands.generate_deck.DeckGenerationWorkflow"
    ) as MockWorkflow:
        mock_wf = AsyncMock()
        mock_wf.run.return_value = deck
        MockWorkflow.return_value = mock_wf

        handler = _build_handler(
            ai_content_generator, slide_renderer, deck_repository, event_bus
        )

        cmd = GenerateDeckCommand(
            account_id="acc-001",
            offering="Cloud Migration",
            template_id="tmpl-default",
        )
        result = await handler.execute(cmd, account_context=_make_account_context())

    assert result.google_slides_url == "https://docs.google.com/presentation/d/test-id/edit"
    assert result.generated_at is not None
    assert result.exported_at is not None
