"""Pure domain tests for the CRMRecord aggregate root.

No mocks — exercises frozen-dataclass behaviour, sync/conflict
status transitions, field updates, and domain event emission.
"""

from datetime import datetime, UTC

from searce_scout.shared_kernel.types import CRMRecordId

from searce_scout.crm_sync.domain.entities.crm_record import CRMRecord
from searce_scout.crm_sync.domain.events.crm_events import (
    RecordSyncedEvent,
    SyncConflictDetectedEvent,
)
from searce_scout.crm_sync.domain.value_objects.crm_provider import CRMProvider
from searce_scout.crm_sync.domain.value_objects.record_type import RecordType
from searce_scout.crm_sync.domain.value_objects.sync_status import SyncStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(
    sync_status: SyncStatus = SyncStatus.PENDING,
    fields: tuple[tuple[str, str], ...] = (("name", "Acme"), ("industry", "Tech")),
) -> CRMRecord:
    return CRMRecord(
        record_id=CRMRecordId("crm-001"),
        provider=CRMProvider.SALESFORCE,
        record_type=RecordType.ACCOUNT,
        local_id="local-001",
        fields=fields,
        sync_status=sync_status,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMarkSynced:
    def test_mark_synced_sets_status_and_external_id(self) -> None:
        record = _make_record()
        now = datetime.now(UTC)
        synced = record.mark_synced("sf-ext-001", now)

        assert synced.sync_status is SyncStatus.SYNCED
        assert synced.external_id == "sf-ext-001"
        assert synced.last_synced_at is now

        # Original unchanged
        assert record.sync_status is SyncStatus.PENDING
        assert record.external_id is None

    def test_mark_synced_appends_event(self) -> None:
        record = _make_record()
        now = datetime.now(UTC)
        synced = record.mark_synced("sf-ext-001", now)

        assert len(synced.domain_events) == 1
        event = synced.domain_events[0]
        assert isinstance(event, RecordSyncedEvent)
        assert event.provider == CRMProvider.SALESFORCE.value
        assert event.record_type == RecordType.ACCOUNT.value
        assert event.external_id == "sf-ext-001"


class TestMarkConflict:
    def test_mark_conflict_sets_status(self) -> None:
        record = _make_record()
        conflicted = record.mark_conflict("name field mismatch")

        assert conflicted.sync_status is SyncStatus.CONFLICT
        assert len(conflicted.domain_events) == 1
        event = conflicted.domain_events[0]
        assert isinstance(event, SyncConflictDetectedEvent)
        assert event.field_name == "name field mismatch"


class TestUpdateFields:
    def test_update_fields_returns_new_instance(self) -> None:
        record = _make_record(sync_status=SyncStatus.SYNCED)
        new_fields = (("name", "Acme Inc"), ("industry", "Technology"))
        updated = record.update_fields(new_fields)

        # New instance has updated fields and reset status
        assert updated.fields == new_fields
        assert updated.sync_status is SyncStatus.PENDING

        # Original unchanged
        assert record.fields == (("name", "Acme"), ("industry", "Tech"))
        assert record.sync_status is SyncStatus.SYNCED
