"""SQLAlchemy-backed sync log repository — implements SyncLogRepositoryPort.

Persists :class:`CRMRecord` aggregates in a relational table using
SQLAlchemy async sessions.  The frozen domain dataclass is mapped to /
from a mutable ORM model on every read/write boundary so the domain
layer stays free of infrastructure concerns.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from searce_scout.shared_kernel.types import CRMRecordId

from searce_scout.crm_sync.domain.entities.crm_record import CRMRecord
from searce_scout.crm_sync.domain.ports.sync_log_repository_port import (
    SyncLogRepositoryPort,
)
from searce_scout.crm_sync.domain.value_objects.crm_provider import CRMProvider
from searce_scout.crm_sync.domain.value_objects.record_type import RecordType
from searce_scout.crm_sync.domain.value_objects.sync_status import SyncStatus


# ------------------------------------------------------------------
# ORM model
# ------------------------------------------------------------------

class _Base(DeclarativeBase):
    pass


class SyncLogModel(_Base):
    """ORM representation of a CRM sync log entry."""

    __tablename__ = "crm_sync_log"

    record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    record_type: Mapped[str] = mapped_column(String(32), nullable=False)
    local_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fields_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    sync_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=SyncStatus.PENDING.value, index=True
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ------------------------------------------------------------------
# Mapping helpers
# ------------------------------------------------------------------

def _model_to_entity(model: SyncLogModel) -> CRMRecord:
    """Convert a SQLAlchemy ORM row into a frozen domain dataclass."""
    raw_fields: list[list[str]] = json.loads(model.fields_json)
    fields = tuple(tuple(pair) for pair in raw_fields)  # type: ignore[misc]
    return CRMRecord(
        record_id=CRMRecordId(model.record_id),
        provider=CRMProvider(model.provider),
        record_type=RecordType(model.record_type),
        local_id=model.local_id,
        external_id=model.external_id,
        fields=fields,  # type: ignore[arg-type]
        sync_status=SyncStatus(model.sync_status),
        last_synced_at=model.last_synced_at,
        # Domain events are transient and never persisted.
        domain_events=(),
    )


def _entity_to_model(entity: CRMRecord) -> SyncLogModel:
    """Convert a frozen domain dataclass into a mutable ORM model."""
    return SyncLogModel(
        record_id=str(entity.record_id),
        provider=entity.provider.value,
        record_type=entity.record_type.value,
        local_id=entity.local_id,
        external_id=entity.external_id,
        fields_json=json.dumps([list(pair) for pair in entity.fields]),
        sync_status=entity.sync_status.value,
        last_synced_at=entity.last_synced_at,
    )


# ------------------------------------------------------------------
# Repository implementation
# ------------------------------------------------------------------

class SyncLogRepository:
    """SQLAlchemy async repository implementing :class:`SyncLogRepositoryPort`.

    Parameters
    ----------
    session:
        An ``AsyncSession`` managed by the caller (unit-of-work pattern).
        The repository does *not* commit — the caller controls the
        transaction boundary.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: CRMRecord) -> None:
        """Persist or update a CRM record in the sync log."""
        model = _entity_to_model(record)
        await self._session.merge(model)
        await self._session.flush()

    async def get_by_id(
        self, record_id: CRMRecordId
    ) -> CRMRecord | None:
        """Look up a single record by its aggregate id."""
        stmt = select(SyncLogModel).where(
            SyncLogModel.record_id == str(record_id)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _model_to_entity(row)

    async def find_by_local_id(
        self, local_id: str
    ) -> tuple[CRMRecord, ...]:
        """Return all sync log entries that reference *local_id*."""
        stmt = select(SyncLogModel).where(
            SyncLogModel.local_id == local_id
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return tuple(_model_to_entity(row) for row in rows)

    async def find_pending(self) -> tuple[CRMRecord, ...]:
        """Return all records whose sync status is PENDING."""
        stmt = select(SyncLogModel).where(
            SyncLogModel.sync_status == SyncStatus.PENDING.value
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return tuple(_model_to_entity(row) for row in rows)


# Structural compatibility assertion
def _check_port_compliance() -> None:
    _: SyncLogRepositoryPort = SyncLogRepository(  # type: ignore[assignment]
        session=None,  # type: ignore[arg-type]
    )
