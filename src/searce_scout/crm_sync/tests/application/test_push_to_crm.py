"""Application tests for PushToCRMHandler.

Verifies that the handler maps local fields to CRM fields, creates or
updates a record in the external CRM, persists the sync log, and
publishes events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import CRMRecordId

from searce_scout.crm_sync.application.commands.push_to_crm import (
    PushToCRMCommand,
    PushToCRMHandler,
)
from searce_scout.crm_sync.domain.entities.crm_record import CRMRecord
from searce_scout.crm_sync.domain.entities.field_mapping import FieldMapping
from searce_scout.crm_sync.domain.events.crm_events import RecordSyncedEvent
from searce_scout.crm_sync.domain.ports.crm_client_port import CRMClientPort
from searce_scout.crm_sync.domain.ports.sync_log_repository_port import (
    SyncLogRepositoryPort,
)
from searce_scout.crm_sync.domain.services.field_mapper import FieldMapperService
from searce_scout.crm_sync.domain.value_objects.crm_provider import CRMProvider
from searce_scout.crm_sync.domain.value_objects.record_type import RecordType
from searce_scout.crm_sync.domain.value_objects.sync_direction import SyncDirection
from searce_scout.crm_sync.domain.value_objects.sync_status import SyncStatus


def _make_field_mappings() -> tuple[FieldMapping, ...]:
    """Build test field mappings for SALESFORCE LEAD."""
    return (
        FieldMapping(
            mapping_id="fm-1",
            provider=CRMProvider.SALESFORCE,
            record_type=RecordType.LEAD,
            local_field="company_name",
            crm_field="Company",
            direction=SyncDirection.PUSH,
        ),
        FieldMapping(
            mapping_id="fm-2",
            provider=CRMProvider.SALESFORCE,
            record_type=RecordType.LEAD,
            local_field="contact_email",
            crm_field="Email",
            direction=SyncDirection.BIDIRECTIONAL,
        ),
    )


@pytest.fixture()
def crm_client() -> AsyncMock:
    client = AsyncMock(spec=CRMClientPort)
    client.create_record.return_value = "ext-sf-001"
    client.update_record.return_value = None
    return client


@pytest.fixture()
def sync_log_repository() -> AsyncMock:
    return AsyncMock(spec=SyncLogRepositoryPort)


@pytest.fixture()
def event_bus() -> AsyncMock:
    bus = AsyncMock(spec=EventBusPort)
    bus.publish.return_value = None
    return bus


def _build_handler(
    crm_client: AsyncMock,
    sync_log_repository: AsyncMock,
    event_bus: AsyncMock,
) -> PushToCRMHandler:
    return PushToCRMHandler(
        crm_client=crm_client,
        field_mapper_service=FieldMapperService(),
        sync_log_repository=sync_log_repository,
        event_bus=event_bus,
        field_mappings=_make_field_mappings(),
    )


async def test_push_creates_record_in_crm(
    crm_client: AsyncMock,
    sync_log_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """When no existing record is found, handler must create a new CRM record."""
    # No existing records
    sync_log_repository.find_by_local_id.return_value = ()

    handler = _build_handler(crm_client, sync_log_repository, event_bus)

    cmd = PushToCRMCommand(
        local_id="local-001",
        record_type="LEAD",
        provider="SALESFORCE",
        fields={"company_name": "TestCo", "contact_email": "alice@testco.com"},
    )

    result = await handler.execute(cmd)

    # Verify create was called with mapped fields
    crm_client.create_record.assert_awaited_once()
    call_args = crm_client.create_record.call_args
    assert call_args.kwargs["record_type"] == RecordType.LEAD
    mapped_fields = call_args.kwargs["fields"]
    assert mapped_fields["Company"] == "TestCo"
    assert mapped_fields["Email"] == "alice@testco.com"

    # Verify sync log was saved
    sync_log_repository.save.assert_awaited_once()
    saved_record: CRMRecord = sync_log_repository.save.call_args[0][0]
    assert saved_record.external_id == "ext-sf-001"
    assert saved_record.sync_status == SyncStatus.SYNCED

    # Verify events were published
    event_bus.publish.assert_awaited_once()
    published_events = event_bus.publish.call_args[0][0]
    assert any(isinstance(e, RecordSyncedEvent) for e in published_events)

    # Verify DTO
    assert result.external_id == "ext-sf-001"
    assert result.sync_status == "SYNCED"
    assert result.provider == "SALESFORCE"


async def test_push_updates_existing_record(
    crm_client: AsyncMock,
    sync_log_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """When an existing record is found, handler must update it in the CRM."""
    existing = CRMRecord(
        record_id=CRMRecordId("rec-existing"),
        provider=CRMProvider.SALESFORCE,
        record_type=RecordType.LEAD,
        local_id="local-001",
        fields=(("company_name", "OldCo"),),
        sync_status=SyncStatus.SYNCED,
        external_id="ext-sf-existing",
        last_synced_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    sync_log_repository.find_by_local_id.return_value = (existing,)

    handler = _build_handler(crm_client, sync_log_repository, event_bus)

    cmd = PushToCRMCommand(
        local_id="local-001",
        record_type="LEAD",
        provider="SALESFORCE",
        fields={"company_name": "NewCo", "contact_email": "bob@newco.com"},
    )

    result = await handler.execute(cmd)

    # Verify update was called (not create)
    crm_client.update_record.assert_awaited_once()
    call_args = crm_client.update_record.call_args
    assert call_args.kwargs["external_id"] == "ext-sf-existing"
    mapped_fields = call_args.kwargs["fields"]
    assert mapped_fields["Company"] == "NewCo"
    assert mapped_fields["Email"] == "bob@newco.com"

    crm_client.create_record.assert_not_awaited()

    # Verify sync log was saved
    sync_log_repository.save.assert_awaited_once()

    # Verify result
    assert result.external_id == "ext-sf-existing"
    assert result.sync_status == "SYNCED"
