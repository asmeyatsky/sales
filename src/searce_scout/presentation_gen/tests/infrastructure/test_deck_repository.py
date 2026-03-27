"""Tests for the SQLAlchemy DeckRepository adapter using an in-memory SQLite database."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from searce_scout.presentation_gen.domain.entities.slide_deck import SlideDeck
from searce_scout.presentation_gen.domain.value_objects.slide import Slide, SlideType
from searce_scout.presentation_gen.domain.value_objects.template_id import TemplateId
from searce_scout.presentation_gen.infrastructure.adapters.deck_repository import (
    DeckRepository,
    _Base,
)
from searce_scout.shared_kernel.types import AccountId, DeckId
from searce_scout.shared_kernel.value_objects import URL


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _make_deck(
    deck_id: str = "deck-001",
    account_id: str = "acc-001",
) -> SlideDeck:
    return SlideDeck(
        deck_id=DeckId(deck_id),
        account_id=AccountId(account_id),
        slides=(
            Slide(
                slide_type=SlideType.TITLE,
                title="Introduction",
                body="Welcome to the presentation",
                speaker_notes="Greet the audience",
                order=0,
            ),
            Slide(
                slide_type=SlideType.HOOK,
                title="The Challenge",
                body="Legacy systems are slowing you down",
                speaker_notes="Emphasize pain points",
                order=1,
            ),
        ),
        template_id=TemplateId(google_slides_id="template-abc"),
        google_slides_url=URL(value="https://docs.google.com/presentation/d/123"),
        generated_at=datetime(2026, 3, 27, 10, 0, 0, tzinfo=timezone.utc),
        exported_at=None,
        domain_events=(),
    )


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_get_by_id(session: AsyncSession) -> None:
    """Save a deck and retrieve it by ID; verify fields match."""
    repo = DeckRepository(session)
    deck = _make_deck()

    await repo.save(deck)
    await session.commit()

    result = await repo.get_by_id(DeckId("deck-001"))

    assert result is not None
    assert str(result.deck_id) == "deck-001"
    assert str(result.account_id) == "acc-001"
    assert result.template_id.google_slides_id == "template-abc"
    assert result.google_slides_url is not None
    assert "123" in result.google_slides_url.value
    assert result.generated_at is not None
    assert len(result.slides) == 2
    assert result.slides[0].slide_type == SlideType.TITLE
    assert result.slides[0].title == "Introduction"
    assert result.slides[1].slide_type == SlideType.HOOK


@pytest.mark.asyncio
async def test_find_by_account(session: AsyncSession) -> None:
    """Save decks for different accounts and find by account_id."""
    repo = DeckRepository(session)

    deck1 = _make_deck(deck_id="deck-001", account_id="acc-001")
    deck2 = _make_deck(deck_id="deck-002", account_id="acc-001")
    deck3 = _make_deck(deck_id="deck-003", account_id="acc-002")

    await repo.save(deck1)
    await repo.save(deck2)
    await repo.save(deck3)
    await session.commit()

    results = await repo.find_by_account(AccountId("acc-001"))
    assert len(results) == 2
    result_ids = {str(d.deck_id) for d in results}
    assert result_ids == {"deck-001", "deck-002"}

    results_other = await repo.find_by_account(AccountId("acc-002"))
    assert len(results_other) == 1
    assert str(results_other[0].deck_id) == "deck-003"

    results_none = await repo.find_by_account(AccountId("acc-999"))
    assert len(results_none) == 0
