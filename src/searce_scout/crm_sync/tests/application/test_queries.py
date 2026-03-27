"""Tests for CRM Sync query handlers."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from searce_scout.shared_kernel.types import CRMRecordId

from searce_scout.crm_sync.application.queries.get_sync_status import (
    GetSyncStatusHandler,
    GetSyncStatusQuery,
)
from searce_scout.crm_sync.application.queries.list_conflicts import (
    ListConflictsHandler,
    ListConflictsQuery,
)
from searce_scout.crm_sync.domain.entities.crm_record import CRMRecord
from searce_scout.crm_sync.domain.value_objects.crm_provider import CRMProvider
from searce_scout.crm_sync.domain.value_objects.record_type import RecordType
from searce_scout.crm_sync.domain.value_objects.sync_status import SyncStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_record(
    record_id: str = "rec-1",
    local_id: str = "local-1",
    sync_status: SyncStatus = SyncStatus.SYNCED,
) -> CRMRecord:
    return CRMRecord(
        record_id=CRMRecordId(record_id),
        provider=CRMProvider.SALESFORCE,
        record_type=RecordType.LEAD,
        local_id=local_id,
        fields=(("email", "jane@acme.com"), ("name", "Jane Doe")),
        sync_status=sync_status,
        external_id="sf-ext-001" if sync_status == SyncStatus.SYNCED else None,
        last_synced_at=datetime(2026, 3, 15) if sync_status == SyncStatus.SYNCED else None,
    )


# ---------------------------------------------------------------------------
# GetSyncStatus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_sync_status_found():
    """Returns a CRMRecordDTO when records exist for the local_id."""
    record = _make_record()
    repo = AsyncMock()
    repo.find_by_local_id.return_value = (record,)

    handler = GetSyncStatusHandler(sync_log_repository=repo)
    result = await handler.execute(GetSyncStatusQuery(local_id="local-1"))

    assert result is not None
    assert result.record_id == "rec-1"
    assert result.provider == "SALESFORCE"
    assert result.sync_status == "SYNCED"
    assert result.local_id == "local-1"
    repo.find_by_local_id.assert_awaited_once_with("local-1")


@pytest.mark.asyncio
async def test_get_sync_status_not_found():
    """Returns None when no records exist for the local_id."""
    repo = AsyncMock()
    repo.find_by_local_id.return_value = ()

    handler = GetSyncStatusHandler(sync_log_repository=repo)
    result = await handler.execute(GetSyncStatusQuery(local_id="nonexistent"))

    assert result is None


@pytest.mark.asyncio
async def test_get_sync_status_returns_last_record():
    """When multiple records exist, the handler returns the most recent (last)."""
    older = _make_record(record_id="rec-old")
    newer = _make_record(record_id="rec-new")
    repo = AsyncMock()
    repo.find_by_local_id.return_value = (older, newer)

    handler = GetSyncStatusHandler(sync_log_repository=repo)
    result = await handler.execute(GetSyncStatusQuery(local_id="local-1"))

    assert result is not None
    assert result.record_id == "rec-new"


# ---------------------------------------------------------------------------
# ListConflicts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_conflicts():
    """Returns only records with CONFLICT status from pending records."""
    conflict_record = _make_record(
        record_id="rec-conflict",
        sync_status=SyncStatus.CONFLICT,
    )
    pending_record = _make_record(
        record_id="rec-pending",
        sync_status=SyncStatus.PENDING,
    )

    repo = AsyncMock()
    repo.find_pending.return_value = (conflict_record, pending_record)

    handler = ListConflictsHandler(sync_log_repository=repo)
    result = await handler.execute(ListConflictsQuery())

    assert len(result) == 1
    assert result[0].record_id == "rec-conflict"
    assert result[0].sync_status == "CONFLICT"
    repo.find_pending.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_conflicts_empty():
    """Returns an empty list when no records are in CONFLICT status."""
    pending_record = _make_record(
        record_id="rec-pending",
        sync_status=SyncStatus.PENDING,
    )

    repo = AsyncMock()
    repo.find_pending.return_value = (pending_record,)

    handler = ListConflictsHandler(sync_log_repository=repo)
    result = await handler.execute(ListConflictsQuery())

    assert result == []
