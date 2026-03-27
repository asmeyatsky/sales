"""Application tests for DiscoverStakeholdersHandler.

Verifies that the handler discovers stakeholders via the workflow,
persists each one, and publishes domain events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, call, patch

import pytest

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import AccountId, StakeholderId
from searce_scout.shared_kernel.value_objects import EmailAddress, PersonName, URL

from searce_scout.stakeholder_discovery.application.commands.discover_stakeholders import (
    DiscoverStakeholdersCommand,
    DiscoverStakeholdersHandler,
)
from searce_scout.stakeholder_discovery.domain.entities.contact_info import ContactInfo
from searce_scout.stakeholder_discovery.domain.entities.stakeholder import Stakeholder
from searce_scout.stakeholder_discovery.domain.events.stakeholder_events import (
    ContactValidatedEvent,
    StakeholderIdentifiedEvent,
    StakeholderScoredEvent,
)
from searce_scout.stakeholder_discovery.domain.ports.contact_enrichment_port import (
    ContactEnrichmentPort,
)
from searce_scout.stakeholder_discovery.domain.ports.linkedin_port import LinkedInPort
from searce_scout.stakeholder_discovery.domain.ports.stakeholder_repository_port import (
    StakeholderRepositoryPort,
)
from searce_scout.stakeholder_discovery.domain.services.persona_matching import (
    PersonaMatchingService,
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


def _make_stakeholder(*, identified: bool = True, validated: bool = False) -> Stakeholder:
    """Build a test stakeholder with optional events."""
    events: list = []
    if identified:
        events.append(
            StakeholderIdentifiedEvent(
                aggregate_id="stk-test",
                person_name="Alice Smith",
                job_title="CTO",
                account_id="acc-test",
            )
        )

    contact_info = None
    if validated:
        contact_info = ContactInfo(
            email=EmailAddress(value="alice@testco.example.com"),
            phone=None,
            email_status=ValidationStatus.VALID,
            phone_status=ValidationStatus.UNVALIDATED,
            source="apollo",
            validated_at=datetime.now(UTC),
        )
        events.append(
            ContactValidatedEvent(
                aggregate_id="stk-test",
                email_status=ValidationStatus.VALID,
                phone_status=ValidationStatus.UNVALIDATED,
            )
        )

    return Stakeholder(
        stakeholder_id=StakeholderId("stk-test"),
        account_id=AccountId("acc-test"),
        person_name=PersonName(first_name="Alice", last_name="Smith"),
        job_title=JobTitle(raw_title="CTO", normalized_title="CTO"),
        seniority=Seniority.C_SUITE,
        department=Department.ENGINEERING,
        contact_info=contact_info,
        relevance_score=RelevanceScore(score=0.85, factors=("seniority:C_SUITE",)),
        persona_match=PersonaMatch(
            searce_offering="Cloud Migration",
            target_persona="CTO / VP Infrastructure",
            pain_points=("Legacy infrastructure costs",),
            confidence=0.85,
        ),
        linkedin_url=URL(value="https://linkedin.com/in/alicesmith"),
        domain_events=tuple(events),
    )


@pytest.fixture()
def linkedin_port() -> AsyncMock:
    return AsyncMock(spec=LinkedInPort)


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


async def test_discover_saves_stakeholders(
    linkedin_port: AsyncMock,
    contact_enrichment: AsyncMock,
    stakeholder_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Handler must persist each discovered stakeholder."""
    stakeholder = _make_stakeholder(identified=True, validated=True)

    with patch(
        "searce_scout.stakeholder_discovery.application.commands.discover_stakeholders.StakeholderDiscoveryWorkflow"
    ) as MockWorkflow:
        mock_wf = AsyncMock()
        mock_wf.execute.return_value = [stakeholder]
        MockWorkflow.return_value = mock_wf

        handler = DiscoverStakeholdersHandler(
            linkedin_port=linkedin_port,
            contact_enrichment=contact_enrichment,
            stakeholder_repository=stakeholder_repository,
            event_bus=event_bus,
            persona_matching_service=PersonaMatchingService(),
        )

        cmd = DiscoverStakeholdersCommand(
            account_id="acc-test", company_name="TestCo"
        )
        result = await handler.execute(cmd)

    stakeholder_repository.save.assert_awaited_once_with(stakeholder)
    assert len(result) == 1
    assert result[0].first_name == "Alice"
    assert result[0].last_name == "Smith"


async def test_discover_enriches_contacts(
    linkedin_port: AsyncMock,
    contact_enrichment: AsyncMock,
    stakeholder_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Handler must publish domain events for each stakeholder that has events."""
    stakeholder = _make_stakeholder(identified=True, validated=True)

    with patch(
        "searce_scout.stakeholder_discovery.application.commands.discover_stakeholders.StakeholderDiscoveryWorkflow"
    ) as MockWorkflow:
        mock_wf = AsyncMock()
        mock_wf.execute.return_value = [stakeholder]
        MockWorkflow.return_value = mock_wf

        handler = DiscoverStakeholdersHandler(
            linkedin_port=linkedin_port,
            contact_enrichment=contact_enrichment,
            stakeholder_repository=stakeholder_repository,
            event_bus=event_bus,
            persona_matching_service=PersonaMatchingService(),
        )

        cmd = DiscoverStakeholdersCommand(
            account_id="acc-test", company_name="TestCo"
        )
        await handler.execute(cmd)

    # Should have published the stakeholder's domain events
    event_bus.publish.assert_awaited_once_with(stakeholder.domain_events)
