"""Pure domain tests for the SlideDeck aggregate root.

No mocks — exercises frozen-dataclass immutability, slide addition,
export event recording, and slide_count.
"""

from searce_scout.shared_kernel.types import AccountId, DeckId
from searce_scout.shared_kernel.value_objects import URL

from searce_scout.presentation_gen.domain.entities.slide_deck import SlideDeck
from searce_scout.presentation_gen.domain.events.presentation_events import (
    DeckExportedEvent,
)
from searce_scout.presentation_gen.domain.value_objects.slide import Slide, SlideType
from searce_scout.presentation_gen.domain.value_objects.template_id import TemplateId


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_deck(slides: tuple[Slide, ...] = ()) -> SlideDeck:
    return SlideDeck(
        deck_id=DeckId("deck-001"),
        account_id=AccountId("acct-001"),
        slides=slides,
        template_id=TemplateId(google_slides_id="tmpl-abc"),
    )


def _make_slide(order: int = 0, slide_type: SlideType = SlideType.TITLE) -> Slide:
    return Slide(
        slide_type=slide_type,
        title="Title Slide",
        body="Body text",
        speaker_notes="Notes",
        order=order,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAddSlide:
    def test_add_slide_returns_new_instance(self) -> None:
        deck = _make_deck()
        slide = _make_slide(order=0)
        updated = deck.add_slide(slide)

        # Original unchanged
        assert deck.slides == ()
        assert deck.slide_count() == 0

        # New instance has the slide
        assert len(updated.slides) == 1
        assert updated.slides[0] is slide


class TestSetExported:
    def test_set_exported_appends_event(self) -> None:
        deck = _make_deck()
        url = URL(value="https://docs.google.com/presentation/d/abc123")
        updated = deck.set_exported(url)

        assert updated.google_slides_url is url
        assert updated.exported_at is not None
        assert len(updated.domain_events) == 1
        event = updated.domain_events[0]
        assert isinstance(event, DeckExportedEvent)
        assert event.google_slides_url == url.value


class TestSlideCount:
    def test_slide_count(self) -> None:
        slides = (
            _make_slide(order=0, slide_type=SlideType.TITLE),
            _make_slide(order=1, slide_type=SlideType.HOOK),
            _make_slide(order=2, slide_type=SlideType.CALL_TO_ACTION),
        )
        deck = _make_deck(slides=slides)
        assert deck.slide_count() == 3

    def test_slide_count_empty(self) -> None:
        deck = _make_deck()
        assert deck.slide_count() == 0
