"""Integration tests for the full prospect pipeline.

These tests exercise the FullPipelineWorkflow with mocked external adapters
but real domain and application layers, verifying that all six bounded
contexts collaborate correctly through the DAG orchestrator.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from searce_scout.scout_orchestrator.config.dependency_injection import Container
from searce_scout.scout_orchestrator.config.settings import ScoutSettings
from searce_scout.scout_orchestrator.workflows.full_pipeline import (
    FullPipelineWorkflow,
)


# ---------------------------------------------------------------------------
# Helpers: build mock DTOs that match what handlers actually return
# ---------------------------------------------------------------------------


def _make_account_dto() -> MagicMock:
    """Return a mock AccountProfileDTO with the fields the pipeline reads."""
    dto = MagicMock()
    dto.account_id = "acc-integration-1"
    dto.company_name = "TestCo"
    dto.industry_name = "Technology"
    dto.website = "https://testco.com"
    dto.tech_stack_summary = "EC2, S3, RDS"
    dto.migration_opportunity_score = 0.85
    dto.buying_signal_count = 3
    dto.is_migration_target = True
    dto.primary_cloud = "AWS"
    return dto


def _make_stakeholder_dto(stakeholder_id: str, name: str) -> MagicMock:
    """Return a mock StakeholderDTO."""
    dto = MagicMock()
    dto.stakeholder_id = stakeholder_id
    dto.full_name = name
    dto.job_title = "CTO"
    return dto


def _make_message_dto(message_id: str, stakeholder_id: str) -> MagicMock:
    """Return a mock MessageDTO."""
    dto = MagicMock()
    dto.message_id = message_id
    dto.stakeholder_id = stakeholder_id
    return dto


def _make_sequence_dto(sequence_id: str) -> MagicMock:
    """Return a mock OutreachSequenceDTO."""
    dto = MagicMock()
    dto.sequence_id = sequence_id
    dto.status = "ACTIVE"
    return dto


def _make_deck_dto() -> MagicMock:
    """Return a mock DeckDTO."""
    dto = MagicMock()
    dto.deck_id = "deck-1"
    dto.google_slides_url = "https://docs.google.com/presentation/d/abc123"
    return dto


def _make_crm_dto() -> MagicMock:
    """Return a mock CRMRecordDTO."""
    dto = MagicMock()
    dto.record_id = "crm-1"
    dto.sync_status = "SYNCED"
    return dto


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_container() -> MagicMock:
    """Build a MagicMock Container with all handler mocks wired up.

    External adapters are mocked, but the workflow reads from these
    handler-level mocks so we can verify the orchestration logic.
    """
    container = MagicMock(spec=Container)
    container.settings = ScoutSettings(
        api_key="test-key",
        max_concurrent_research=2,
        max_concurrent_outreach=3,
        slides_template_id="tmpl-001",
        crm_provider="salesforce",
    )

    # Research handler
    account_dto = _make_account_dto()
    container.research_account_handler = MagicMock()
    container.research_account_handler.execute = AsyncMock(return_value=account_dto)

    # Discover handler -- returns 2 stakeholders
    stakeholders = [
        _make_stakeholder_dto("sh-1", "Jane Doe"),
        _make_stakeholder_dto("sh-2", "John Smith"),
    ]
    container.discover_stakeholders_handler = MagicMock()
    container.discover_stakeholders_handler.execute = AsyncMock(
        return_value=stakeholders
    )

    # Generate message handler -- returns a message for each call
    msg_counter = {"n": 0}

    async def _generate_message(cmd, account_context, stakeholder_context):
        msg_counter["n"] += 1
        return _make_message_dto(f"msg-{msg_counter['n']}", cmd.stakeholder_id)

    container.generate_message_handler = MagicMock()
    container.generate_message_handler.execute = AsyncMock(
        side_effect=_generate_message
    )

    # Start sequence handler
    seq_counter = {"n": 0}

    async def _start_sequence(cmd):
        seq_counter["n"] += 1
        return _make_sequence_dto(f"seq-{seq_counter['n']}")

    container.start_sequence_handler = MagicMock()
    container.start_sequence_handler.execute = AsyncMock(
        side_effect=_start_sequence
    )

    # Deck handler
    container.generate_deck_handler = MagicMock()
    container.generate_deck_handler.execute = AsyncMock(
        return_value=_make_deck_dto()
    )

    # CRM handler
    container.push_to_crm_handler = MagicMock()
    container.push_to_crm_handler.execute = AsyncMock(
        return_value=_make_crm_dto()
    )

    return container


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_full_pipeline_end_to_end(mock_container: MagicMock):
    """The full pipeline should research, discover, message, outreach, deck, and CRM sync.

    Verifies:
    - Summary dict contains expected keys and values.
    - Each BC handler was invoked at least once.
    - Message generation was called 10 times (5 steps x 2 stakeholders).
    - Two outreach sequences were started.
    """
    workflow = FullPipelineWorkflow(container=mock_container)

    summary = await workflow.execute(
        company_name="TestCo",
        website="https://testco.com",
        tone="PROFESSIONAL_CONSULTANT",
    )

    # Verify summary shape
    assert summary["account_id"] == "acc-integration-1"
    assert summary["stakeholder_count"] == 2
    assert summary["sequences_started"] == 2
    assert summary["deck_url"] == "https://docs.google.com/presentation/d/abc123"
    assert summary["crm_synced"] is True

    # Verify each handler was called
    mock_container.research_account_handler.execute.assert_awaited_once()
    mock_container.discover_stakeholders_handler.execute.assert_awaited_once()

    # 2 stakeholders x 5 steps = 10 message generations
    assert mock_container.generate_message_handler.execute.await_count == 10

    # 2 sequences started (one per stakeholder)
    assert mock_container.start_sequence_handler.execute.await_count == 2

    # Deck generation called once
    mock_container.generate_deck_handler.execute.assert_awaited_once()

    # CRM push called once (for the account record)
    mock_container.push_to_crm_handler.execute.assert_awaited_once()


@pytest.mark.integration
async def test_full_pipeline_with_no_stakeholders(mock_container: MagicMock):
    """If discovery returns zero stakeholders, messages and sequences are skipped."""
    mock_container.discover_stakeholders_handler.execute = AsyncMock(return_value=[])

    workflow = FullPipelineWorkflow(container=mock_container)

    summary = await workflow.execute(company_name="EmptyCo")

    assert summary["stakeholder_count"] == 0
    assert summary["sequences_started"] == 0
    mock_container.generate_message_handler.execute.assert_not_awaited()
    mock_container.start_sequence_handler.execute.assert_not_awaited()


@pytest.mark.integration
async def test_full_pipeline_deck_failure_non_critical(mock_container: MagicMock):
    """Deck generation is non-critical; pipeline should succeed even if it fails."""
    mock_container.generate_deck_handler.execute = AsyncMock(
        side_effect=RuntimeError("Slides API down")
    )

    workflow = FullPipelineWorkflow(container=mock_container)
    summary = await workflow.execute(company_name="TestCo")

    # Pipeline should still succeed
    assert summary["account_id"] == "acc-integration-1"
    assert summary["deck_url"] is None
    assert summary["stakeholder_count"] == 2
    assert summary["sequences_started"] == 2
