"""Application tests for AuditTechStackHandler.

Verifies that the handler detects the tech stack via the port, updates
the account aggregate, persists it, and publishes domain events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import AccountId
from searce_scout.shared_kernel.value_objects import CompanyName, URL

from searce_scout.account_intelligence.application.commands.audit_tech_stack import (
    AuditTechStackCommand,
    AuditTechStackHandler,
)
from searce_scout.account_intelligence.domain.entities.account_profile import AccountProfile
from searce_scout.account_intelligence.domain.ports.account_repository_port import (
    AccountRepositoryPort,
)
from searce_scout.account_intelligence.domain.ports.tech_detector_port import TechDetectorPort
from searce_scout.account_intelligence.domain.services.tech_stack_analysis import (
    TechStackAnalysisService,
)
from searce_scout.account_intelligence.domain.value_objects.industry import (
    CompanySize,
    Industry,
)
from searce_scout.account_intelligence.domain.value_objects.tech_stack import (
    CloudProvider,
    TechComponent,
    TechStack,
)


def _make_existing_account() -> AccountProfile:
    """Build an AccountProfile that already exists in the repository."""
    return AccountProfile(
        account_id=AccountId("acc-audit"),
        company_name=CompanyName(canonical="AuditCo"),
        industry=Industry(name="Finance", vertical="Banking"),
        company_size=CompanySize.ENTERPRISE,
        tech_stack=None,
        buying_signals=(),
        filing_data=None,
        website=URL(value="https://auditco.example.com"),
        researched_at=datetime.now(UTC),
        domain_events=(),
    )


@pytest.fixture()
def tech_detector() -> AsyncMock:
    return AsyncMock(spec=TechDetectorPort)


@pytest.fixture()
def account_repository() -> AsyncMock:
    return AsyncMock(spec=AccountRepositoryPort)


@pytest.fixture()
def event_bus() -> AsyncMock:
    bus = AsyncMock(spec=EventBusPort)
    bus.publish.return_value = None
    return bus


async def test_audit_updates_account_tech_stack(
    tech_detector: AsyncMock,
    account_repository: AsyncMock,
    event_bus: AsyncMock,
) -> None:
    """Handler must detect tech stack, update the account, save, and publish events."""
    existing_account = _make_existing_account()
    new_tech_stack = TechStack(
        components=(
            TechComponent(name="EC2", category="compute", provider=CloudProvider.AWS),
            TechComponent(name="RDS", category="database", provider=CloudProvider.AWS),
        ),
        primary_cloud=CloudProvider.AWS,
    )

    account_repository.get_by_id.return_value = existing_account
    tech_detector.detect_tech_stack.return_value = new_tech_stack

    handler = AuditTechStackHandler(
        tech_detector=tech_detector,
        account_repository=account_repository,
        event_bus=event_bus,
        tech_stack_analysis_service=TechStackAnalysisService(),
    )

    cmd = AuditTechStackCommand(account_id="acc-audit", domain="auditco.example.com")
    result = await handler.execute(cmd)

    # Verify the tech detector was called with the correct domain
    tech_detector.detect_tech_stack.assert_awaited_once_with("auditco.example.com")

    # Verify save was called (the account now has the new tech stack)
    account_repository.save.assert_awaited_once()
    saved_account: AccountProfile = account_repository.save.call_args[0][0]
    assert saved_account.tech_stack is not None
    assert saved_account.tech_stack.primary_cloud == CloudProvider.AWS
    assert len(saved_account.tech_stack.components) == 2

    # Verify events were published (set_tech_stack produces a TechStackAuditedEvent)
    event_bus.publish.assert_awaited_once()
    published_events = event_bus.publish.call_args[0][0]
    assert len(published_events) >= 1

    # Verify DTO
    assert result.primary_cloud == "AWS"
    assert result.is_migration_target is True  # AWS is a competitor cloud
