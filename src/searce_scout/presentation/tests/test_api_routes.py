"""Tests for the Searce Scout FastAPI routes using mocked container handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from searce_scout.presentation.api.app import create_app
from searce_scout.scout_orchestrator.config.settings import ScoutSettings

API_KEY = "test-secret-key"


@pytest.fixture
def mock_container() -> MagicMock:
    """Build a MagicMock container with all handler execute methods as AsyncMock."""
    container = MagicMock()

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
    container.stop_sequence_handler = MagicMock()
    container.stop_sequence_handler.execute = AsyncMock()
    container.process_reply_handler = MagicMock()
    container.process_reply_handler.execute = AsyncMock()
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

    # Settings (needed by some routes e.g. presentations)
    container.settings = ScoutSettings(api_key=API_KEY)

    return container


@pytest.fixture
def client(mock_container: MagicMock) -> TestClient:
    """Create a TestClient with the mocked container."""
    settings = ScoutSettings(api_key=API_KEY)
    app = create_app(settings=settings)
    app.state.container = mock_container
    return TestClient(app)


def _auth_headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------


def test_health_returns_200(client: TestClient) -> None:
    """The /health endpoint should return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ------------------------------------------------------------------
# Accounts
# ------------------------------------------------------------------


def test_research_account_returns_result(
    client: TestClient, mock_container: MagicMock
) -> None:
    """POST /api/v1/accounts/research with valid body returns a result."""
    dto = MagicMock()
    dto.account_id = "acc-001"
    dto.company_name = "Acme Corp"
    dto.migration_opportunity_score = 0.85
    dto.buying_signal_count = 3
    mock_container.research_account_handler.execute.return_value = dto

    response = client.post(
        "/api/v1/accounts/research",
        json={"company_name": "Acme Corp", "website": "https://acme.com"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == "acc-001"
    assert data["company_name"] == "Acme Corp"
    assert data["migration_score"] == 0.85
    assert data["signal_count"] == 3


def test_research_account_422_missing_field(client: TestClient) -> None:
    """POST /api/v1/accounts/research without company_name returns 422."""
    response = client.post(
        "/api/v1/accounts/research",
        json={"website": "https://acme.com"},
        headers=_auth_headers(),
    )
    assert response.status_code == 422


def test_get_account_found(
    client: TestClient, mock_container: MagicMock
) -> None:
    """GET /api/v1/accounts/{id} returns the account when found."""
    dto = MagicMock()
    dto.model_dump.return_value = {
        "account_id": "acc-001",
        "company_name": "Acme Corp",
        "industry_name": "Technology",
    }
    mock_container.get_account_profile_handler.execute.return_value = dto

    response = client.get(
        "/api/v1/accounts/acc-001",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == "acc-001"


def test_get_account_not_found(
    client: TestClient, mock_container: MagicMock
) -> None:
    """GET /api/v1/accounts/{id} returns 404 when not found."""
    mock_container.get_account_profile_handler.execute.return_value = None

    response = client.get(
        "/api/v1/accounts/nonexistent",
        headers=_auth_headers(),
    )

    assert response.status_code == 404


# ------------------------------------------------------------------
# Stakeholders
# ------------------------------------------------------------------


def test_discover_stakeholders(
    client: TestClient, mock_container: MagicMock
) -> None:
    """POST /api/v1/stakeholders/discover returns discovered stakeholders."""
    dto1 = MagicMock()
    dto1.model_dump.return_value = {"stakeholder_id": "stk-001", "name": "Jane Doe"}
    dto2 = MagicMock()
    dto2.model_dump.return_value = {"stakeholder_id": "stk-002", "name": "John Smith"}
    mock_container.discover_stakeholders_handler.execute.return_value = [dto1, dto2]

    response = client.post(
        "/api/v1/stakeholders/discover",
        json={"account_id": "acc-001", "company_name": "Acme Corp"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["stakeholder_id"] == "stk-001"


# ------------------------------------------------------------------
# Messaging
# ------------------------------------------------------------------


def test_generate_message(
    client: TestClient, mock_container: MagicMock
) -> None:
    """POST /api/v1/messages/generate returns generated message."""
    dto = MagicMock()
    dto.model_dump.return_value = {
        "message_id": "msg-001",
        "body": "Hello Jane...",
        "channel": "EMAIL",
    }
    mock_container.generate_message_handler.execute.return_value = dto

    response = client.post(
        "/api/v1/messages/generate",
        json={
            "account_id": "acc-001",
            "stakeholder_id": "stk-001",
            "channel": "EMAIL",
            "tone": "PROFESSIONAL_CONSULTANT",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message_id"] == "msg-001"


# ------------------------------------------------------------------
# Outreach / Sequences
# ------------------------------------------------------------------


def test_start_sequence(
    client: TestClient, mock_container: MagicMock
) -> None:
    """POST /api/v1/sequences starts a new outreach sequence."""
    dto = MagicMock()
    dto.model_dump.return_value = {
        "sequence_id": "seq-001",
        "status": "active",
    }
    mock_container.start_sequence_handler.execute.return_value = dto

    response = client.post(
        "/api/v1/sequences",
        json={
            "account_id": "acc-001",
            "stakeholder_id": "stk-001",
            "message_ids": {},
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["sequence_id"] == "seq-001"


# ------------------------------------------------------------------
# Presentations / Decks
# ------------------------------------------------------------------


def test_generate_deck(
    client: TestClient, mock_container: MagicMock
) -> None:
    """POST /api/v1/decks/generate creates a presentation deck."""
    # Mock the get_account_profile_handler so the route's profile lookup works
    profile_dto = MagicMock()
    profile_dto.company_name = "Acme Corp"
    profile_dto.industry_name = "Technology"
    profile_dto.tech_stack_summary = "AWS EC2, S3"
    profile_dto.migration_opportunity_score = 0.8
    mock_container.get_account_profile_handler.execute.return_value = profile_dto

    deck_dto = MagicMock()
    deck_dto.model_dump.return_value = {
        "deck_id": "deck-001",
        "account_id": "acc-001",
        "slide_count": 7,
    }
    mock_container.generate_deck_handler.execute.return_value = deck_dto

    response = client.post(
        "/api/v1/decks/generate",
        json={"account_id": "acc-001", "offering": "Cloud Migration"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["deck_id"] == "deck-001"


# ------------------------------------------------------------------
# CRM
# ------------------------------------------------------------------


def test_list_conflicts(
    client: TestClient, mock_container: MagicMock
) -> None:
    """GET /api/v1/crm/conflicts returns conflict list."""
    dto = MagicMock()
    dto.model_dump.return_value = {
        "record_id": "crm-001",
        "sync_status": "CONFLICT",
    }
    mock_container.list_conflicts_handler.execute.return_value = [dto]

    response = client.get(
        "/api/v1/crm/conflicts",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["sync_status"] == "CONFLICT"


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------


def test_auth_required(client: TestClient) -> None:
    """Protected endpoints without X-API-Key header return 401."""
    # Try several protected endpoints without auth
    endpoints = [
        ("GET", "/api/v1/accounts/acc-001"),
        ("POST", "/api/v1/accounts/research"),
        ("POST", "/api/v1/stakeholders/discover"),
        ("POST", "/api/v1/messages/generate"),
        ("POST", "/api/v1/sequences"),
        ("POST", "/api/v1/decks/generate"),
        ("GET", "/api/v1/crm/conflicts"),
    ]

    for method, path in endpoints:
        if method == "GET":
            response = client.get(path)
        else:
            response = client.post(path, json={})

        assert response.status_code == 401, (
            f"{method} {path} returned {response.status_code}, expected 401"
        )
