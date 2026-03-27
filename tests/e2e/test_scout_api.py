"""End-to-end tests for the Searce Scout REST API.

Uses FastAPI TestClient with a mocked DI container to verify HTTP-level
behavior: status codes, request/response shapes, authentication, and routing.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
class TestHealthEndpoint:
    """Tests for the /health endpoint (no auth required)."""

    def test_health_endpoint_returns_ok(self, api_client: TestClient):
        """GET /health should return 200 with {"status": "ok"}."""
        response = api_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_does_not_require_api_key(self, api_client: TestClient):
        """GET /health should succeed without X-API-Key header."""
        # api_client is already configured without default headers
        response = api_client.get("/health")
        assert response.status_code == 200


@pytest.mark.e2e
class TestAuthentication:
    """Tests for API key authentication middleware."""

    def test_unauthorized_without_api_key(self, api_client: TestClient):
        """Requests to protected endpoints without X-API-Key should return 401."""
        response = api_client.get("/api/v1/accounts/some-id")
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_unauthorized_with_wrong_api_key(self, api_client: TestClient):
        """Requests with an incorrect X-API-Key should return 401."""
        response = api_client.get(
            "/api/v1/accounts/some-id",
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401

    def test_authorized_with_correct_api_key(
        self, api_client: TestClient, mock_container: MagicMock
    ):
        """Requests with the correct X-API-Key should pass auth."""
        # Configure the handler to return None (triggers 404)
        mock_container.get_account_profile_handler.execute.return_value = None

        response = api_client.get(
            "/api/v1/accounts/acc-1",
            headers={"X-API-Key": "test-secret-key"},
        )
        # Should get past auth -- 404 is expected because mock returns None
        assert response.status_code == 404


@pytest.mark.e2e
class TestResearchAccountEndpoint:
    """Tests for POST /api/v1/accounts/research."""

    def test_research_account_endpoint(
        self, api_client: TestClient, mock_container: MagicMock
    ):
        """POST /api/v1/accounts/research should return a ResearchResponse."""
        # Arrange: configure mock handler to return a DTO-like object
        mock_dto = MagicMock()
        mock_dto.account_id = "acc-test-1"
        mock_dto.company_name = "TestCo"
        mock_dto.migration_opportunity_score = 0.85
        mock_dto.buying_signal_count = 3
        mock_container.research_account_handler.execute.return_value = mock_dto

        # Act
        response = api_client.post(
            "/api/v1/accounts/research",
            json={"company_name": "TestCo", "website": "https://testco.com"},
            headers={"X-API-Key": "test-secret-key"},
        )

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["account_id"] == "acc-test-1"
        assert body["company_name"] == "TestCo"
        assert body["migration_score"] == 0.85
        assert body["signal_count"] == 3
        assert body["stakeholders_found"] == 0

        # Verify handler was called with correct command
        mock_container.research_account_handler.execute.assert_awaited_once()

    def test_research_account_missing_company_name(self, api_client: TestClient):
        """POST /api/v1/accounts/research without company_name should return 422."""
        response = api_client.post(
            "/api/v1/accounts/research",
            json={},
            headers={"X-API-Key": "test-secret-key"},
        )
        assert response.status_code == 422

    def test_research_account_with_optional_fields(
        self, api_client: TestClient, mock_container: MagicMock
    ):
        """POST with optional ticker and website should pass them through."""
        mock_dto = MagicMock()
        mock_dto.account_id = "acc-test-2"
        mock_dto.company_name = "BigCorp"
        mock_dto.migration_opportunity_score = 0.70
        mock_dto.buying_signal_count = 1
        mock_container.research_account_handler.execute.return_value = mock_dto

        response = api_client.post(
            "/api/v1/accounts/research",
            json={
                "company_name": "BigCorp",
                "website": "https://bigcorp.com",
                "ticker": "BIG",
            },
            headers={"X-API-Key": "test-secret-key"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["company_name"] == "BigCorp"


@pytest.mark.e2e
class TestGetAccountEndpoint:
    """Tests for GET /api/v1/accounts/{account_id}."""

    def test_get_account_returns_404_for_missing(
        self, api_client: TestClient, mock_container: MagicMock
    ):
        """GET /api/v1/accounts/{id} should return 404 when not found."""
        mock_container.get_account_profile_handler.execute.return_value = None

        response = api_client.get(
            "/api/v1/accounts/nonexistent-id",
            headers={"X-API-Key": "test-secret-key"},
        )

        assert response.status_code == 404
        assert "Account not found" in response.json()["detail"]

    def test_get_account_returns_profile(
        self, api_client: TestClient, mock_container: MagicMock
    ):
        """GET /api/v1/accounts/{id} should return the account profile when found."""
        mock_dto = MagicMock()
        mock_dto.model_dump.return_value = {
            "account_id": "acc-1",
            "company_name": "TestCo",
            "industry_name": "Technology",
            "migration_opportunity_score": 0.85,
        }
        mock_container.get_account_profile_handler.execute.return_value = mock_dto

        response = api_client.get(
            "/api/v1/accounts/acc-1",
            headers={"X-API-Key": "test-secret-key"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["account_id"] == "acc-1"
        assert body["company_name"] == "TestCo"


@pytest.mark.e2e
class TestMigrationTargetsEndpoint:
    """Tests for GET /api/v1/accounts/migration-targets."""

    def test_list_migration_targets(
        self, api_client: TestClient, mock_container: MagicMock
    ):
        """GET /api/v1/accounts/migration-targets should return a list."""
        mock_dto_1 = MagicMock()
        mock_dto_1.model_dump.return_value = {
            "account_id": "acc-1",
            "company_name": "HighScoreCo",
            "migration_opportunity_score": 0.9,
        }
        mock_dto_2 = MagicMock()
        mock_dto_2.model_dump.return_value = {
            "account_id": "acc-2",
            "company_name": "AlsoHighCo",
            "migration_opportunity_score": 0.8,
        }
        mock_container.find_migration_targets_handler.execute.return_value = [
            mock_dto_1,
            mock_dto_2,
        ]

        response = api_client.get(
            "/api/v1/accounts/migration-targets",
            headers={"X-API-Key": "test-secret-key"},
        )

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 2

    def test_migration_targets_empty(
        self, api_client: TestClient, mock_container: MagicMock
    ):
        """GET /api/v1/accounts/migration-targets should return [] when none exist."""
        mock_container.find_migration_targets_handler.execute.return_value = []

        response = api_client.get(
            "/api/v1/accounts/migration-targets",
            headers={"X-API-Key": "test-secret-key"},
        )

        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.e2e
class TestBuyingSignalsEndpoint:
    """Tests for GET /api/v1/accounts/{account_id}/signals."""

    def test_list_buying_signals(
        self, api_client: TestClient, mock_container: MagicMock
    ):
        """GET /api/v1/accounts/{id}/signals should return a list of signals."""
        mock_signal = MagicMock()
        mock_signal.model_dump.return_value = {
            "signal_id": "sig-1",
            "signal_type": "JOB_POSTING",
            "strength": "STRONG",
            "description": "Hiring cloud engineers",
        }
        mock_container.list_buying_signals_handler.execute.return_value = [mock_signal]

        response = api_client.get(
            "/api/v1/accounts/acc-1/signals",
            headers={"X-API-Key": "test-secret-key"},
        )

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["signal_type"] == "JOB_POSTING"
