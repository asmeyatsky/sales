"""Tests for the SQLAlchemy SyncLogRepository adapter using an in-memory SQLite database."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from searce_scout.crm_sync.domain.entities.crm_record import CRMRecord
from searce_scout.crm_sync.domain.value_objects.crm_provider import CRMProvider
from searce_scout.crm_sync.domain.value_objects.record_type import RecordType
from searce_scout.crm_sync.domain.value_objects.sync_status import SyncStatus
from searce_scout.crm_sync.infrastructure.adapters.sync_log_repository import (
    SyncLogRepository,
    _Base,
)
from searce_scout.shared_kernel.types import CRMRecordId


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _make_record(
    record_id: str = "crm-001",
    local_id: str = "local-001",
    sync_status: SyncStatus = SyncStatus.PENDING,
) -> CRMRecord:
    return CRMRecord(
        record_id=CRMRecordId(record_id),
        provider=CRMProvider.SALESFORCE,
        record_type=RecordType.LEAD,
        local_id=local_id,
        fields=(("name", "Jane Doe"), ("email", "jane@example.com")),
        sync_status=sync_status,
        external_id=None,
        last_synced_at=None,
        domain_events=(),
    )


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_get_by_id(session: AsyncSession) -> None:
    """Save a CRM record and retrieve it by ID; verify fields match."""
    repo = SyncLogRepository(session)
    record = _make_record()

    await repo.save(record)
    await session.commit()

    result = await repo.get_by_id(CRMRecordId("crm-001"))

    assert result is not None
    assert str(result.record_id) == "crm-001"
    assert result.provider == CRMProvider.SALESFORCE
    assert result.record_type == RecordType.LEAD
    assert result.local_id == "local-001"
    assert result.sync_status == SyncStatus.PENDING
    assert len(result.fields) == 2
    assert result.fields[0] == ("name", "Jane Doe")
    assert result.fields[1] == ("email", "jane@example.com")


@pytest.mark.asyncio
async def test_find_by_local_id(session: AsyncSession) -> None:
    """Save records with different local_ids and find by local_id."""
    repo = SyncLogRepository(session)

    rec1 = _make_record(record_id="crm-001", local_id="local-aaa")
    rec2 = _make_record(record_id="crm-002", local_id="local-aaa")
    rec3 = _make_record(record_id="crm-003", local_id="local-bbb")

    await repo.save(rec1)
    await repo.save(rec2)
    await repo.save(rec3)
    await session.commit()

    results = await repo.find_by_local_id("local-aaa")
    assert len(results) == 2
    result_ids = {str(r.record_id) for r in results}
    assert result_ids == {"crm-001", "crm-002"}

    results_other = await repo.find_by_local_id("local-bbb")
    assert len(results_other) == 1

    results_none = await repo.find_by_local_id("nonexistent")
    assert len(results_none) == 0


@pytest.mark.asyncio
async def test_find_pending(session: AsyncSession) -> None:
    """Save records with different statuses and find only PENDING ones."""
    repo = SyncLogRepository(session)

    rec_pending1 = _make_record(record_id="crm-p1", sync_status=SyncStatus.PENDING)
    rec_pending2 = _make_record(record_id="crm-p2", sync_status=SyncStatus.PENDING)
    rec_synced = _make_record(record_id="crm-s1", sync_status=SyncStatus.SYNCED)
    rec_conflict = _make_record(record_id="crm-c1", sync_status=SyncStatus.CONFLICT)
    rec_failed = _make_record(record_id="crm-f1", sync_status=SyncStatus.FAILED)

    await repo.save(rec_pending1)
    await repo.save(rec_pending2)
    await repo.save(rec_synced)
    await repo.save(rec_conflict)
    await repo.save(rec_failed)
    await session.commit()

    results = await repo.find_pending()

    assert len(results) == 2
    for r in results:
        assert r.sync_status == SyncStatus.PENDING
    result_ids = {str(r.record_id) for r in results}
    assert result_ids == {"crm-p1", "crm-p2"}
