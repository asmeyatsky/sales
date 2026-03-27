"""Application tests for PullFromCRMHandler.

Verifies that the handler fetches changes from the CRM, maps fields
back to local representation, persists each record, and publishes events.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort

from searce_scout.crm_sync.application.commands.pull_from_crm import (
    PullFromCRMCommand,
    PullFromCRMHandler,
)
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


def _make_field_mappings() -> tuple[FieldMapping, ...]:
    """Build test field mappings for HUBSPOT CONTACT (pull direction)."""
    return (
        FieldMapping(
            mapping_id="fm-p1",
            provider=CRMProvider.HUBSPOT,
            record_type=RecordType.CONTACT,
            local_field="company_name",
            crm_field="company",
            direction=SyncDirection.PULL,
        ),
        FieldMapping(
            mapping_id="fm-p2",
            provider=CRMProvider.HUBSPOT,
            record_type=RecordType.CONTACT,
            local_field="contact_email",
            crm_field="email",
            direction=SyncDirection.BIDIRECTIONAL,
        ),
    )


@pytest.fixture()
def crm_client() -> AsyncMock:
    return AsyncMock(spec=CRMClientPort)


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
) -> PullFromCRMHandler:
    return PullFromCRMHandler(
        crm_client=crm_client,
        field_mapper_service=FieldMapperService(),
        sync_log_repository=sync_log_repository,
        event_bus=event_bus,
        field_mappings=_make_field_mappings(),
    )


async def test_pull_fetches_and_saves_records(
    crm_client: AsyncMock,
    sync_log_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Handler must fetch remote changes, map fields, persist each record, and publish events."""
    # Simulate two records returned from the CRM
    crm_client.get_changes_since.return_value = (
        {
            "Id": "ext-hs-001",
            "company": "AlphaCo",
            "email": "alice@alphaco.com",
        },
        {
            "Id": "ext-hs-002",
            "company": "BetaCo",
            "email": "bob@betaco.com",
        },
    )

    handler = _build_handler(crm_client, sync_log_repository, event_bus)

    cmd = PullFromCRMCommand(
        provider="HUBSPOT",
        record_type="CONTACT",
        since="2026-03-01T00:00:00+00:00",
    )

    results = await handler.execute(cmd)

    # Verify CRM client was called
    crm_client.get_changes_since.assert_awaited_once()
    call_args = crm_client.get_changes_since.call_args
    assert call_args.kwargs["record_type"] == RecordType.CONTACT

    # Verify two records were saved
    assert sync_log_repository.save.await_count == 2
    assert len(results) == 2

    # Verify first record's fields were mapped correctly
    first_result = results[0]
    assert first_result.local_id == "ext-hs-001"
    assert first_result.provider == "HUBSPOT"
    assert first_result.sync_status == "SYNCED"
    assert first_result.external_id == "ext-hs-001"
    assert first_result.fields["company_name"] == "AlphaCo"
    assert first_result.fields["contact_email"] == "alice@alphaco.com"

    # Verify second record
    second_result = results[1]
    assert second_result.local_id == "ext-hs-002"
    assert second_result.fields["company_name"] == "BetaCo"

    # Verify events were published (batch of RecordSyncedEvents)
    event_bus.publish.assert_awaited_once()
    published_events = event_bus.publish.call_args[0][0]
    assert len(published_events) == 2
    assert all(isinstance(e, RecordSyncedEvent) for e in published_events)
