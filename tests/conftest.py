"""Shared test fixtures for Searce Scout integration and E2E tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from searce_scout.shared_kernel.ports.clock_port import ClockPort
from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import AccountId, StakeholderId
from searce_scout.shared_kernel.value_objects import CompanyName, PersonName, URL

from searce_scout.account_intelligence.domain.entities.account_profile import AccountProfile
from searce_scout.account_intelligence.domain.value_objects.industry import CompanySize, Industry
from searce_scout.account_intelligence.domain.value_objects.tech_stack import (
    CloudProvider,
    TechComponent,
    TechStack,
)
from searce_scout.stakeholder_discovery.domain.entities.stakeholder import Stakeholder
from searce_scout.stakeholder_discovery.domain.value_objects.job_title import JobTitle
from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    Department,
    Seniority,
)

from searce_scout.scout_orchestrator.config.settings import ScoutSettings

FROZEN_NOW = datetime(2026, 3, 27, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_event_bus() -> AsyncMock:
    """An AsyncMock that satisfies EventBusPort (publish / subscribe)."""
    bus = AsyncMock()
    bus.publish = AsyncMock(return_value=None)
    bus.subscribe = AsyncMock(return_value=None)
    return bus


# ---------------------------------------------------------------------------
# Frozen clock
# ---------------------------------------------------------------------------


@pytest.fixture()
def frozen_clock() -> MagicMock:
    """Return a mock ClockPort that always returns a fixed datetime."""
    clock = MagicMock(spec=ClockPort)
    clock.now.return_value = FROZEN_NOW
    return clock


# ---------------------------------------------------------------------------
# Sample domain objects
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_account_profile() -> AccountProfile:
    """Return a fully-populated AccountProfile for use in tests."""
    return AccountProfile(
        account_id=AccountId("acc-001"),
        company_name=CompanyName(canonical="Acme Corp"),
        industry=Industry(name="Technology", vertical="SaaS"),
        company_size=CompanySize.ENTERPRISE,
        tech_stack=TechStack(
            components=(
                TechComponent(name="EC2", category="compute", provider=CloudProvider.AWS),
                TechComponent(name="S3", category="storage", provider=CloudProvider.AWS),
            ),
            primary_cloud=CloudProvider.AWS,
        ),
        buying_signals=(),
        filing_data=None,
        website=URL(value="https://acme.example.com"),
        researched_at=FROZEN_NOW,
        domain_events=(),
    )


@pytest.fixture()
def sample_stakeholder() -> Stakeholder:
    """Return a fully-populated Stakeholder for use in tests."""
    return Stakeholder(
        stakeholder_id=StakeholderId("stk-001"),
        account_id=AccountId("acc-001"),
        person_name=PersonName(first_name="Jane", last_name="Doe"),
        job_title=JobTitle(raw_title="CTO", normalized_title="CTO"),
        seniority=Seniority.C_SUITE,
        department=Department.ENGINEERING,
        contact_info=None,
        relevance_score=None,
        persona_match=None,
        linkedin_url=URL(value="https://linkedin.com/in/janedoe"),
        domain_events=(),
    )


# ---------------------------------------------------------------------------
# External ports (all AsyncMock)
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_external_ports() -> dict[str, AsyncMock]:
    """Return a dict of AsyncMock objects keyed by adapter role name.

    Covers every external port in the system so tests can inject them into
    handlers or the DI container without touching real services.
    """
    return {
        # Account Intelligence
        "filing_scraper": AsyncMock(),
        "news_scraper": AsyncMock(),
        "job_board_scraper": AsyncMock(),
        "tech_detector": AsyncMock(),
        "ai_analyzer": AsyncMock(),
        "account_repository": AsyncMock(),
        # Stakeholder Discovery
        "linkedin_port": AsyncMock(),
        "contact_enrichment": AsyncMock(),
        "stakeholder_repository": AsyncMock(),
        # Messaging
        "ai_message_generator": AsyncMock(),
        "case_study_port": AsyncMock(),
        "message_repository": AsyncMock(),
        # Outreach
        "email_sender": AsyncMock(),
        "linkedin_messenger": AsyncMock(),
        "ai_classifier": AsyncMock(),
        "sequence_repository": AsyncMock(),
        "task_creator": AsyncMock(),
        "inbox_reader": AsyncMock(),
        # Presentation Gen
        "ai_content_generator": AsyncMock(),
        "slide_renderer": AsyncMock(),
        "deck_repository": AsyncMock(),
        # CRM Sync
        "crm_client": AsyncMock(),
        "sync_log_repository": AsyncMock(),
    }


# ---------------------------------------------------------------------------
# FastAPI TestClient with mocked container
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_settings() -> ScoutSettings:
    """Minimal settings suitable for test runs."""
    return ScoutSettings(
        database_url="sqlite+aiosqlite:///./test_scout.db",
        api_key="test-secret-key",
    )


@pytest.fixture()
def mock_container(mock_event_bus: AsyncMock) -> MagicMock:
    """A MagicMock Container whose handler attributes are all AsyncMocks.

    Each handler exposes an ``execute`` coroutine that can be configured
    per-test via ``container.<handler_name>.execute.return_value = ...``.
    """
    container = MagicMock()
    container.event_bus = mock_event_bus

    # Command handlers
    container.research_account_handler = MagicMock()
    container.research_account_handler.execute = AsyncMock()
    container.discover_stakeholders_handler = MagicMock()
    container.discover_stakeholders_handler.execute = AsyncMock()
    container.validate_contact_handler = MagicMock()
    container.validate_contact_handler.execute = AsyncMock()
    container.generate_message_handler = MagicMock()
    container.generate_message_handler.execute = AsyncMock()
    container.adjust_tone_handler = MagicMock()
    container.adjust_tone_handler.execute = AsyncMock()
    container.start_sequence_handler = MagicMock()
    container.start_sequence_handler.execute = AsyncMock()
    container.execute_next_step_handler = MagicMock()
    container.execute_next_step_handler.execute = AsyncMock()
    container.process_reply_handler = MagicMock()
    container.process_reply_handler.execute = AsyncMock()
    container.stop_sequence_handler = MagicMock()
    container.stop_sequence_handler.execute = AsyncMock()
    container.generate_deck_handler = MagicMock()
    container.generate_deck_handler.execute = AsyncMock()
    container.push_to_crm_handler = MagicMock()
    container.push_to_crm_handler.execute = AsyncMock()
    container.pull_from_crm_handler = MagicMock()
    container.pull_from_crm_handler.execute = AsyncMock()
    container.resolve_conflict_handler = MagicMock()
    container.resolve_conflict_handler.execute = AsyncMock()

    # Query handlers
    container.get_account_profile_handler = MagicMock()
    container.get_account_profile_handler.execute = AsyncMock()
    container.list_buying_signals_handler = MagicMock()
    container.list_buying_signals_handler.execute = AsyncMock()
    container.find_migration_targets_handler = MagicMock()
    container.find_migration_targets_handler.execute = AsyncMock()
    container.get_stakeholders_for_account_handler = MagicMock()
    container.get_stakeholders_for_account_handler.execute = AsyncMock()
    container.get_message_handler = MagicMock()
    container.get_message_handler.execute = AsyncMock()
    container.preview_message_handler = MagicMock()
    container.preview_message_handler.execute = AsyncMock()
    container.get_sequence_status_handler = MagicMock()
    container.get_sequence_status_handler.execute = AsyncMock()
    container.list_active_sequences_handler = MagicMock()
    container.list_active_sequences_handler.execute = AsyncMock()
    container.get_deck_handler = MagicMock()
    container.get_deck_handler.execute = AsyncMock()
    container.list_decks_for_account_handler = MagicMock()
    container.list_decks_for_account_handler.execute = AsyncMock()
    container.list_conflicts_handler = MagicMock()
    container.list_conflicts_handler.execute = AsyncMock()

    # Settings (needed for auth middleware)
    container.settings = ScoutSettings(api_key="test-secret-key")

    return container


@pytest.fixture()
def api_client(test_settings: ScoutSettings, mock_container: MagicMock) -> TestClient:
    """FastAPI TestClient with all dependencies mocked via the container."""
    from searce_scout.presentation.api.app import create_app

    app = create_app(settings=test_settings)
    app.state.container = mock_container

    return TestClient(app)
