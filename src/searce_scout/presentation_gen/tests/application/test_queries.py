"""Tests for Presentation Gen query handlers."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from searce_scout.shared_kernel.types import AccountId, DeckId

from searce_scout.presentation_gen.application.queries.get_deck import (
    GetDeckHandler,
    GetDeckQuery,
)
from searce_scout.presentation_gen.application.queries.list_decks_for_account import (
    ListDecksForAccountHandler,
    ListDecksForAccountQuery,
)
from searce_scout.presentation_gen.domain.entities.slide_deck import SlideDeck
from searce_scout.presentation_gen.domain.value_objects.slide import Slide, SlideType
from searce_scout.presentation_gen.domain.value_objects.template_id import TemplateId


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_deck(deck_id: str = "deck-1", account_id: str = "acc-1") -> SlideDeck:
    slide = Slide(
        slide_type=SlideType.TITLE,
        title="Welcome",
        body="Introduction slide",
        speaker_notes="Greet the audience",
        order=1,
    )
    return SlideDeck(
        deck_id=DeckId(deck_id),
        account_id=AccountId(account_id),
        slides=(slide,),
        template_id=TemplateId(google_slides_id="tmpl-abc"),
        google_slides_url=None,
        generated_at=datetime(2026, 3, 1),
        exported_at=None,
    )


# ---------------------------------------------------------------------------
# GetDeck
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_deck_found():
    """Returns a DeckDTO when the deck exists."""
    deck = _make_deck()
    repo = AsyncMock()
    repo.get_by_id.return_value = deck

    handler = GetDeckHandler(deck_repository=repo)
    result = await handler.execute(GetDeckQuery(deck_id="deck-1"))

    assert result is not None
    assert result.deck_id == "deck-1"
    assert result.slide_count == 1
    assert result.slides[0].slide_type == "TITLE"
    assert result.slides[0].title == "Welcome"
    repo.get_by_id.assert_awaited_once_with(DeckId("deck-1"))


@pytest.mark.asyncio
async def test_get_deck_not_found():
    """Returns None when the deck does not exist."""
    repo = AsyncMock()
    repo.get_by_id.return_value = None

    handler = GetDeckHandler(deck_repository=repo)
    result = await handler.execute(GetDeckQuery(deck_id="nonexistent"))

    assert result is None


# ---------------------------------------------------------------------------
# ListDecksForAccount
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_decks_for_account():
    """Returns DeckDTOs for all decks belonging to an account."""
    deck_a = _make_deck(deck_id="deck-a")
    deck_b = _make_deck(deck_id="deck-b")

    repo = AsyncMock()
    repo.find_by_account.return_value = (deck_a, deck_b)

    handler = ListDecksForAccountHandler(deck_repository=repo)
    result = await handler.execute(
        ListDecksForAccountQuery(account_id="acc-1")
    )

    assert len(result) == 2
    assert result[0].deck_id == "deck-a"
    assert result[1].deck_id == "deck-b"
    repo.find_by_account.assert_awaited_once_with(AccountId("acc-1"))
