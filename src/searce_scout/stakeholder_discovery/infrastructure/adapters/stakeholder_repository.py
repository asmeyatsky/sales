"""SQLAlchemy-based persistence adapter for the Stakeholder aggregate.

Implements StakeholderRepositoryPort using async SQLAlchemy to persist
and retrieve Stakeholder domain objects. The internal ORM model
(StakeholderModel) is a private implementation detail -- callers only
interact with the domain Stakeholder aggregate root.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from searce_scout.shared_kernel.types import AccountId, StakeholderId
from searce_scout.shared_kernel.value_objects import EmailAddress, PersonName, PhoneNumber, URL
from searce_scout.stakeholder_discovery.domain.entities.contact_info import ContactInfo
from searce_scout.stakeholder_discovery.domain.entities.stakeholder import Stakeholder
from searce_scout.stakeholder_discovery.domain.ports.stakeholder_repository_port import (
    StakeholderRepositoryPort,
)
from searce_scout.stakeholder_discovery.domain.value_objects.job_title import JobTitle
from searce_scout.stakeholder_discovery.domain.value_objects.relevance_score import (
    PersonaMatch,
    RelevanceScore,
)
from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    Department,
    Seniority,
    ValidationStatus,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model (private to this module)
# ---------------------------------------------------------------------------

class _Base(DeclarativeBase):
    pass


class StakeholderModel(_Base):
    """Relational mapping for the Stakeholder aggregate."""

    __tablename__ = "stakeholders"

    stakeholder_id = Column(String(64), primary_key=True)
    account_id = Column(String(64), nullable=False, index=True)

    # PersonName
    first_name = Column(String(128), nullable=False)
    last_name = Column(String(128), nullable=False)

    # JobTitle
    raw_title = Column(String(256), nullable=False, default="")
    normalized_title = Column(String(256), nullable=False, default="")

    seniority = Column(SAEnum(Seniority), nullable=False)
    department = Column(SAEnum(Department), nullable=False)

    # ContactInfo (nullable)
    email = Column(String(320), nullable=True)
    phone = Column(String(32), nullable=True)
    email_status = Column(SAEnum(ValidationStatus), nullable=True)
    phone_status = Column(SAEnum(ValidationStatus), nullable=True)
    contact_source = Column(String(64), nullable=True)
    contact_validated_at = Column(DateTime(timezone=True), nullable=True)

    # RelevanceScore (nullable)
    relevance_score = Column(Float, nullable=True)
    relevance_factors = Column(Text, nullable=True)  # comma-separated

    # PersonaMatch (nullable)
    persona_searce_offering = Column(String(256), nullable=True)
    persona_target = Column(String(256), nullable=True)
    persona_pain_points = Column(Text, nullable=True)  # comma-separated
    persona_confidence = Column(Float, nullable=True)

    linkedin_url = Column(String(512), nullable=True)


# ---------------------------------------------------------------------------
# Repository adapter
# ---------------------------------------------------------------------------

class StakeholderRepository:
    """Async SQLAlchemy adapter implementing :class:`StakeholderRepositoryPort`.

    Parameters
    ----------
    session:
        An async SQLAlchemy session (e.g., from an ``async_sessionmaker``).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # -- StakeholderRepositoryPort interface ---------------------------------

    async def save(self, stakeholder: Stakeholder) -> None:
        """Persist a Stakeholder aggregate (upsert)."""
        model = self._to_model(stakeholder)
        await self._session.merge(model)
        await self._session.flush()

    async def get_by_id(self, stakeholder_id: StakeholderId) -> Stakeholder | None:
        """Retrieve a single Stakeholder by its identifier."""
        stmt = select(StakeholderModel).where(
            StakeholderModel.stakeholder_id == str(stakeholder_id)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def find_by_account(self, account_id: AccountId) -> tuple[Stakeholder, ...]:
        """Return all stakeholders belonging to an account."""
        stmt = (
            select(StakeholderModel)
            .where(StakeholderModel.account_id == str(account_id))
            .order_by(StakeholderModel.last_name, StakeholderModel.first_name)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return tuple(self._to_domain(row) for row in rows)

    # -- Mapping helpers ----------------------------------------------------

    @staticmethod
    def _to_model(s: Stakeholder) -> StakeholderModel:
        """Map a domain Stakeholder to its ORM representation."""
        model = StakeholderModel(
            stakeholder_id=str(s.stakeholder_id),
            account_id=str(s.account_id),
            first_name=s.person_name.first_name,
            last_name=s.person_name.last_name,
            raw_title=s.job_title.raw_title,
            normalized_title=s.job_title.normalized_title,
            seniority=s.seniority,
            department=s.department,
            linkedin_url=s.linkedin_url.value if s.linkedin_url else None,
        )

        if s.contact_info is not None:
            ci = s.contact_info
            model.email = ci.email.value if ci.email else None
            model.phone = ci.phone.value if ci.phone else None
            model.email_status = ci.email_status
            model.phone_status = ci.phone_status
            model.contact_source = ci.source
            model.contact_validated_at = ci.validated_at

        if s.relevance_score is not None:
            model.relevance_score = s.relevance_score.score
            model.relevance_factors = ",".join(s.relevance_score.factors)

        if s.persona_match is not None:
            pm = s.persona_match
            model.persona_searce_offering = pm.searce_offering
            model.persona_target = pm.target_persona
            model.persona_pain_points = ",".join(pm.pain_points)
            model.persona_confidence = pm.confidence

        return model

    @staticmethod
    def _to_domain(m: StakeholderModel) -> Stakeholder:
        """Map an ORM model back to a domain Stakeholder aggregate."""
        contact_info: ContactInfo | None = None
        if m.email_status is not None or m.phone_status is not None:
            email: EmailAddress | None = None
            if m.email:
                try:
                    email = EmailAddress(value=m.email)
                except Exception:
                    logger.debug("Invalid email in DB row: %s", m.email)

            phone: PhoneNumber | None = None
            if m.phone:
                try:
                    phone = PhoneNumber(value=m.phone)
                except Exception:
                    logger.debug("Invalid phone in DB row: %s", m.phone)

            contact_info = ContactInfo(
                email=email,
                phone=phone,
                email_status=m.email_status or ValidationStatus.UNVALIDATED,
                phone_status=m.phone_status or ValidationStatus.UNVALIDATED,
                source=m.contact_source or "",
                validated_at=m.contact_validated_at or datetime.min,
            )

        relevance_score: RelevanceScore | None = None
        if m.relevance_score is not None:
            factors_str: str = m.relevance_factors or ""
            factors = tuple(f for f in factors_str.split(",") if f)
            relevance_score = RelevanceScore(score=m.relevance_score, factors=factors)

        persona_match: PersonaMatch | None = None
        if m.persona_searce_offering is not None:
            pain_str: str = m.persona_pain_points or ""
            pain_points = tuple(p for p in pain_str.split(",") if p)
            persona_match = PersonaMatch(
                searce_offering=m.persona_searce_offering,
                target_persona=m.persona_target or "",
                pain_points=pain_points,
                confidence=m.persona_confidence or 0.0,
            )

        linkedin_url: URL | None = None
        if m.linkedin_url:
            try:
                linkedin_url = URL(value=m.linkedin_url)
            except Exception:
                logger.debug("Invalid URL in DB row: %s", m.linkedin_url)

        return Stakeholder(
            stakeholder_id=StakeholderId(m.stakeholder_id),
            account_id=AccountId(m.account_id),
            person_name=PersonName(first_name=m.first_name, last_name=m.last_name),
            job_title=JobTitle(raw_title=m.raw_title, normalized_title=m.normalized_title),
            seniority=m.seniority,
            department=m.department,
            contact_info=contact_info,
            relevance_score=relevance_score,
            persona_match=persona_match,
            linkedin_url=linkedin_url,
            domain_events=(),
        )


# Structural compatibility check with the port Protocol.
_check: type[StakeholderRepositoryPort] = StakeholderRepository  # type: ignore[assignment]
