"""SQLAlchemy-based persistence adapter for the SlideDeck aggregate.

Implements DeckRepositoryPort using async SQLAlchemy.  The internal ORM
model (DeckModel) is a private implementation detail -- callers interact
only with the domain SlideDeck aggregate root.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from searce_scout.shared_kernel.types import AccountId, DeckId
from searce_scout.shared_kernel.value_objects import URL
from searce_scout.presentation_gen.domain.entities.slide_deck import SlideDeck
from searce_scout.presentation_gen.domain.ports.deck_repository_port import (
    DeckRepositoryPort,
)
from searce_scout.presentation_gen.domain.value_objects.slide import Slide, SlideType
from searce_scout.presentation_gen.domain.value_objects.template_id import TemplateId

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model (private to this module)
# ---------------------------------------------------------------------------

class _Base(DeclarativeBase):
    pass


class DeckModel(_Base):
    """Relational mapping for the SlideDeck aggregate.

    Slides are stored as a JSON array in the ``slides_json`` column to
    keep the schema simple while the slide structure is a value object.
    """

    __tablename__ = "slide_decks"

    deck_id = Column(String(64), primary_key=True)
    account_id = Column(String(64), nullable=False, index=True)
    template_google_slides_id = Column(String(256), nullable=False)
    slides_json = Column(Text, nullable=False, default="[]")
    google_slides_url = Column(String(512), nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    exported_at = Column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Repository adapter
# ---------------------------------------------------------------------------

class DeckRepository:
    """Async SQLAlchemy adapter implementing :class:`DeckRepositoryPort`.

    Parameters
    ----------
    session:
        An async SQLAlchemy session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- DeckRepositoryPort interface ---------------------------------------

    async def save(self, deck: SlideDeck) -> None:
        """Persist a SlideDeck aggregate (upsert)."""
        model = self._to_model(deck)
        await self._session.merge(model)
        await self._session.flush()

    async def get_by_id(self, deck_id: DeckId) -> SlideDeck | None:
        """Retrieve a single SlideDeck by its identifier."""
        stmt = select(DeckModel).where(DeckModel.deck_id == str(deck_id))
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def find_by_account(self, account_id: AccountId) -> tuple[SlideDeck, ...]:
        """Return all decks associated with an account."""
        stmt = (
            select(DeckModel)
            .where(DeckModel.account_id == str(account_id))
            .order_by(DeckModel.generated_at.desc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return tuple(self._to_domain(r) for r in rows)

    # -- Mapping helpers ----------------------------------------------------

    @staticmethod
    def _to_model(deck: SlideDeck) -> DeckModel:
        """Map a domain SlideDeck to its ORM representation."""
        slides_data: list[dict[str, Any]] = [
            {
                "slide_type": slide.slide_type.value,
                "title": slide.title,
                "body": slide.body,
                "speaker_notes": slide.speaker_notes,
                "order": slide.order,
            }
            for slide in deck.slides
        ]

        return DeckModel(
            deck_id=str(deck.deck_id),
            account_id=str(deck.account_id),
            template_google_slides_id=deck.template_id.google_slides_id,
            slides_json=json.dumps(slides_data),
            google_slides_url=(
                deck.google_slides_url.value if deck.google_slides_url else None
            ),
            generated_at=deck.generated_at,
            exported_at=deck.exported_at,
        )

    @staticmethod
    def _to_domain(m: DeckModel) -> SlideDeck:
        """Map an ORM model back to a domain SlideDeck aggregate."""
        slides_data: list[dict[str, Any]] = json.loads(m.slides_json or "[]")
        domain_slides: list[Slide] = []

        for sd in slides_data:
            try:
                domain_slides.append(
                    Slide(
                        slide_type=SlideType(sd["slide_type"]),
                        title=sd.get("title", ""),
                        body=sd.get("body", ""),
                        speaker_notes=sd.get("speaker_notes", ""),
                        order=sd.get("order", 0),
                    )
                )
            except (KeyError, ValueError):
                logger.debug("Skipping invalid slide data in deck %s: %s", m.deck_id, sd)

        google_slides_url: URL | None = None
        if m.google_slides_url:
            try:
                google_slides_url = URL(value=m.google_slides_url)
            except Exception:
                logger.debug("Invalid Google Slides URL in DB: %s", m.google_slides_url)

        return SlideDeck(
            deck_id=DeckId(m.deck_id),
            account_id=AccountId(m.account_id),
            slides=tuple(domain_slides),
            template_id=TemplateId(google_slides_id=m.template_google_slides_id),
            google_slides_url=google_slides_url,
            generated_at=m.generated_at,
            exported_at=m.exported_at,
            domain_events=(),
        )


# Structural compatibility check with the port Protocol.
_check: type[DeckRepositoryPort] = DeckRepository  # type: ignore[assignment]
