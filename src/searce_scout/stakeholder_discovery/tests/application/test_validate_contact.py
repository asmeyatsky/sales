"""Application tests for ValidateContactHandler.

Verifies that the handler enriches a stakeholder's contact info,
updates the aggregate, persists it, and publishes domain events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import AccountId, StakeholderId
from searce_scout.shared_kernel.value_objects import EmailAddress, PersonName, URL

from searce_scout.stakeholder_discovery.application.commands.validate_contact import (
    ValidateContactCommand,
    ValidateContactHandler,
)
from searce_scout.stakeholder_discovery.domain.entities.contact_info import ContactInfo
from searce_scout.stakeholder_discovery.domain.entities.stakeholder import Stakeholder
from searce_scout.stakeholder_discovery.domain.events.stakeholder_events import (
    ContactValidatedEvent,
)
from searce_scout.stakeholder_discovery.domain.ports.contact_enrichment_port import (
    ContactEnrichmentPort,
)
from searce_scout.stakeholder_discovery.domain.ports.stakeholder_repository_port import (
    StakeholderRepositoryPort,
)
from searce_scout.stakeholder_discovery.domain.value_objects.job_title import JobTitle
from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    Department,
    Seniority,
    ValidationStatus,
)


def _make_stakeholder() -> Stakeholder:
    """Build a stakeholder without contact info (pre-validation)."""
    return Stakeholder(
        stakeholder_id=StakeholderId("stk-val"),
        account_id=AccountId("acc-val"),
        person_name=PersonName(first_name="Bob", last_name="Jones"),
        job_title=JobTitle(raw_title="VP Engineering", normalized_title="VP Engineering"),
        seniority=Seniority.VP,
        department=Department.ENGINEERING,
        contact_info=None,
        relevance_score=None,
        persona_match=None,
        linkedin_url=URL(value="https://linkedin.com/in/bobjones"),
        domain_events=(),
    )


def _make_contact_info() -> ContactInfo:
    """Build a validated ContactInfo."""
    return ContactInfo(
        email=EmailAddress(value="bob@testco.example.com"),
        phone=None,
        email_status=ValidationStatus.VALID,
        phone_status=ValidationStatus.UNVALIDATED,
        source="zoominfo",
        validated_at=datetime.now(UTC),
    )


@pytest.fixture()
def contact_enrichment() -> AsyncMock:
    return AsyncMock(spec=ContactEnrichmentPort)


@pytest.fixture()
def stakeholder_repository() -> AsyncMock:
    return AsyncMock(spec=StakeholderRepositoryPort)


@pytest.fixture()
def event_bus() -> AsyncMock:
    bus = AsyncMock(spec=EventBusPort)
    bus.publish.return_value = None
    return bus


async def test_validate_updates_stakeholder_contact(
    contact_enrichment: AsyncMock,
    stakeholder_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Handler must enrich contact info, update stakeholder, save, and publish events."""
    stakeholder = _make_stakeholder()
    contact_info = _make_contact_info()

    stakeholder_repository.get_by_id.return_value = stakeholder
    contact_enrichment.enrich_contact.return_value = contact_info

    handler = ValidateContactHandler(
        contact_enrichment=contact_enrichment,
        stakeholder_repository=stakeholder_repository,
        event_bus=event_bus,
    )

    cmd = ValidateContactCommand(stakeholder_id="stk-val")
    result = await handler.execute(cmd)

    # Verify enrichment was called with the stakeholder's name
    contact_enrichment.enrich_contact.assert_awaited_once_with(
        person_name=stakeholder.person_name,
        company_name="",
    )

    # Verify save was called with an updated stakeholder
    stakeholder_repository.save.assert_awaited_once()
    saved: Stakeholder = stakeholder_repository.save.call_args[0][0]
    assert saved.contact_info is not None
    assert saved.contact_info.email_status == ValidationStatus.VALID

    # Verify events were published (validate_contact produces a ContactValidatedEvent)
    event_bus.publish.assert_awaited_once()
    published_events = event_bus.publish.call_args[0][0]
    assert any(isinstance(e, ContactValidatedEvent) for e in published_events)

    # Verify DTO
    assert result.email == "bob@testco.example.com"
    assert result.email_status == "VALID"
