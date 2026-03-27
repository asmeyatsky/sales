"""SQLAlchemy account repository adapter — implements AccountRepositoryPort.

Persists AccountProfile aggregates using an async SQLAlchemy session.
Provides an ORM model (AccountProfileModel) that maps between the
relational representation and the frozen domain dataclass.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from searce_scout.account_intelligence.domain.entities.account_profile import (
    AccountProfile,
)
from searce_scout.account_intelligence.domain.entities.buying_signal import (
    BuyingSignal,
)
from searce_scout.account_intelligence.domain.ports.account_repository_port import (
    AccountRepositoryPort,
)
from searce_scout.account_intelligence.domain.value_objects.filing_data import (
    FilingData,
)
from searce_scout.account_intelligence.domain.value_objects.industry import (
    CompanySize,
    Industry,
)
from searce_scout.account_intelligence.domain.value_objects.signal_type import (
    SignalStrength,
    SignalType,
)
from searce_scout.account_intelligence.domain.value_objects.tech_stack import (
    CloudProvider,
    TechComponent,
    TechStack,
)
from searce_scout.shared_kernel.types import AccountId
from searce_scout.shared_kernel.value_objects import URL, CompanyName


# ---------------------------------------------------------------------------
# ORM base and table model
# ---------------------------------------------------------------------------


class _Base(DeclarativeBase):
    pass


class AccountProfileModel(_Base):
    """Relational mapping for the AccountProfile aggregate."""

    __tablename__ = "account_profiles"

    account_id: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    company_name: Mapped[str] = mapped_column(sa.String(256), nullable=False)
    company_aliases: Mapped[str] = mapped_column(
        sa.Text, nullable=False, default="[]"
    )
    industry_name: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    industry_vertical: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    company_size: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    tech_stack_json: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    buying_signals_json: Mapped[str] = mapped_column(
        sa.Text, nullable=False, default="[]"
    )
    filing_data_json: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    website: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    researched_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    intent_score: Mapped[float] = mapped_column(
        sa.Float, nullable=False, default=0.0
    )


# ---------------------------------------------------------------------------
# Repository implementation
# ---------------------------------------------------------------------------


class AccountRepository:
    """Persists and retrieves AccountProfile aggregates via SQLAlchemy async.

    Implements :class:`AccountRepositoryPort`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # AccountRepositoryPort implementation
    # ------------------------------------------------------------------

    async def save(self, account: AccountProfile) -> None:
        """Upsert an AccountProfile into the database."""
        model = self._to_model(account)
        await self._session.merge(model)
        await self._session.flush()

    async def get_by_id(self, account_id: AccountId) -> AccountProfile | None:
        """Retrieve an AccountProfile by its unique identifier."""
        stmt = sa.select(AccountProfileModel).where(
            AccountProfileModel.account_id == str(account_id)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def find_by_company(
        self, company_name: CompanyName
    ) -> AccountProfile | None:
        """Find an AccountProfile by company name (case-insensitive)."""
        stmt = sa.select(AccountProfileModel).where(
            sa.func.lower(AccountProfileModel.company_name)
            == company_name.canonical.lower()
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    async def list_high_intent(
        self, min_score: float
    ) -> tuple[AccountProfile, ...]:
        """Return all AccountProfiles whose intent score meets the threshold."""
        stmt = (
            sa.select(AccountProfileModel)
            .where(AccountProfileModel.intent_score >= min_score)
            .order_by(AccountProfileModel.intent_score.desc())
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return tuple(self._to_domain(row) for row in rows)

    # ------------------------------------------------------------------
    # Domain <-> ORM mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _to_model(account: AccountProfile) -> AccountProfileModel:
        """Convert a domain AccountProfile to an ORM model."""
        tech_stack_json: str | None = None
        if account.tech_stack is not None:
            tech_stack_json = json.dumps(
                {
                    "components": [
                        {
                            "name": c.name,
                            "category": c.category,
                            "provider": c.provider.value,
                        }
                        for c in account.tech_stack.components
                    ],
                    "primary_cloud": (
                        account.tech_stack.primary_cloud.value
                        if account.tech_stack.primary_cloud
                        else None
                    ),
                }
            )

        signals_json = json.dumps(
            [
                {
                    "signal_id": s.signal_id,
                    "signal_type": s.signal_type.value,
                    "strength": s.strength.value,
                    "description": s.description,
                    "source_url": s.source_url.value if s.source_url else None,
                    "detected_at": s.detected_at.isoformat(),
                }
                for s in account.buying_signals
            ]
        )

        filing_json: str | None = None
        if account.filing_data is not None:
            fd = account.filing_data
            filing_json = json.dumps(
                {
                    "fiscal_year": fd.fiscal_year,
                    "revenue": fd.revenue,
                    "it_spend_mentions": list(fd.it_spend_mentions),
                    "digital_transformation_mentions": list(
                        fd.digital_transformation_mentions
                    ),
                    "cloud_mentions": list(fd.cloud_mentions),
                }
            )

        return AccountProfileModel(
            account_id=str(account.account_id),
            company_name=account.company_name.canonical,
            company_aliases=json.dumps(list(account.company_name.aliases)),
            industry_name=account.industry.name,
            industry_vertical=account.industry.vertical,
            company_size=account.company_size.value,
            tech_stack_json=tech_stack_json,
            buying_signals_json=signals_json,
            filing_data_json=filing_json,
            website=account.website.value if account.website else None,
            researched_at=account.researched_at,
            intent_score=account.migration_opportunity_score(),
        )

    @staticmethod
    def _to_domain(model: AccountProfileModel) -> AccountProfile:
        """Convert an ORM model back to a domain AccountProfile."""
        # Company name
        aliases = tuple(json.loads(model.company_aliases))
        company_name = CompanyName(canonical=model.company_name, aliases=aliases)

        # Industry
        industry = Industry(name=model.industry_name, vertical=model.industry_vertical)

        # Company size
        company_size = CompanySize(model.company_size)

        # Tech stack
        tech_stack: TechStack | None = None
        if model.tech_stack_json:
            ts_data = json.loads(model.tech_stack_json)
            components = tuple(
                TechComponent(
                    name=c["name"],
                    category=c["category"],
                    provider=CloudProvider(c["provider"]),
                )
                for c in ts_data.get("components", [])
            )
            primary_raw = ts_data.get("primary_cloud")
            primary_cloud = CloudProvider(primary_raw) if primary_raw else None
            tech_stack = TechStack(components=components, primary_cloud=primary_cloud)

        # Buying signals
        signals_data = json.loads(model.buying_signals_json)
        buying_signals = tuple(
            BuyingSignal(
                signal_id=s["signal_id"],
                signal_type=SignalType(s["signal_type"]),
                strength=SignalStrength(s["strength"]),
                description=s["description"],
                source_url=URL(value=s["source_url"]) if s.get("source_url") else None,
                detected_at=datetime.fromisoformat(s["detected_at"]),
            )
            for s in signals_data
        )

        # Filing data
        filing_data: FilingData | None = None
        if model.filing_data_json:
            fd = json.loads(model.filing_data_json)
            filing_data = FilingData(
                fiscal_year=fd["fiscal_year"],
                revenue=fd.get("revenue"),
                it_spend_mentions=tuple(fd.get("it_spend_mentions", [])),
                digital_transformation_mentions=tuple(
                    fd.get("digital_transformation_mentions", [])
                ),
                cloud_mentions=tuple(fd.get("cloud_mentions", [])),
            )

        # Website
        website: URL | None = None
        if model.website:
            website = URL(value=model.website)

        return AccountProfile(
            account_id=AccountId(model.account_id),
            company_name=company_name,
            industry=industry,
            company_size=company_size,
            tech_stack=tech_stack,
            buying_signals=buying_signals,
            filing_data=filing_data,
            website=website,
            researched_at=model.researched_at,
            domain_events=(),
        )


# Structural compatibility assertion
def _check_port_compliance(session: AsyncSession) -> None:
    _: AccountRepositoryPort = AccountRepository(session=session)  # type: ignore[assignment]
