"""Tests for Account Intelligence query handlers."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from searce_scout.shared_kernel.types import AccountId
from searce_scout.shared_kernel.value_objects import CompanyName

from searce_scout.account_intelligence.application.queries.get_account_profile import (
    GetAccountProfileHandler,
    GetAccountProfileQuery,
)
from searce_scout.account_intelligence.application.queries.list_buying_signals import (
    ListBuyingSignalsHandler,
    ListBuyingSignalsQuery,
)
from searce_scout.account_intelligence.application.queries.find_migration_targets import (
    FindMigrationTargetsHandler,
    FindMigrationTargetsQuery,
)
from searce_scout.account_intelligence.domain.entities.account_profile import (
    AccountProfile,
)
from searce_scout.account_intelligence.domain.entities.buying_signal import BuyingSignal
from searce_scout.account_intelligence.domain.value_objects.industry import (
    CompanySize,
    Industry,
)
from searce_scout.account_intelligence.domain.value_objects.signal_type import (
    SignalStrength,
    SignalType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_signal(signal_id: str = "sig-1") -> BuyingSignal:
    return BuyingSignal(
        signal_id=signal_id,
        signal_type=SignalType.CLOUD_MIGRATION_MENTION,
        strength=SignalStrength.STRONG,
        description="Mentioned cloud migration in earnings call",
        source_url=None,
        detected_at=datetime(2026, 1, 15),
    )


def _make_account(
    account_id: str = "acc-1",
    signals: tuple[BuyingSignal, ...] = (),
) -> AccountProfile:
    return AccountProfile(
        account_id=AccountId(account_id),
        company_name=CompanyName(canonical="Acme Corp"),
        industry=Industry(name="Technology", vertical="Cloud"),
        company_size=CompanySize.ENTERPRISE,
        tech_stack=None,
        buying_signals=signals,
        filing_data=None,
        website=None,
        researched_at=datetime(2026, 1, 10),
        domain_events=(),
    )


# ---------------------------------------------------------------------------
# GetAccountProfile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_account_profile_found():
    """When the account exists, the handler returns a DTO."""
    account = _make_account()
    repo = AsyncMock()
    repo.get_by_id.return_value = account

    handler = GetAccountProfileHandler(account_repository=repo)
    result = await handler.execute(GetAccountProfileQuery(account_id="acc-1"))

    assert result is not None
    assert result.account_id == "acc-1"
    assert result.company_name == "Acme Corp"
    assert result.industry_name == "Technology"
    repo.get_by_id.assert_awaited_once_with(AccountId("acc-1"))


@pytest.mark.asyncio
async def test_get_account_profile_not_found():
    """When the account does not exist, the handler returns None."""
    repo = AsyncMock()
    repo.get_by_id.return_value = None

    handler = GetAccountProfileHandler(account_repository=repo)
    result = await handler.execute(GetAccountProfileQuery(account_id="nonexistent"))

    assert result is None


# ---------------------------------------------------------------------------
# ListBuyingSignals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_buying_signals():
    """Returns BuyingSignalDTOs for an account with signals."""
    signal = _make_signal()
    account = _make_account(signals=(signal,))

    repo = AsyncMock()
    repo.get_by_id.return_value = account

    handler = ListBuyingSignalsHandler(account_repository=repo)
    result = await handler.execute(ListBuyingSignalsQuery(account_id="acc-1"))

    assert len(result) == 1
    assert result[0].signal_id == "sig-1"
    assert result[0].signal_type == "CLOUD_MIGRATION_MENTION"
    assert result[0].strength == "STRONG"


@pytest.mark.asyncio
async def test_list_buying_signals_account_not_found():
    """Returns empty list when the account does not exist."""
    repo = AsyncMock()
    repo.get_by_id.return_value = None

    handler = ListBuyingSignalsHandler(account_repository=repo)
    result = await handler.execute(ListBuyingSignalsQuery(account_id="missing"))

    assert result == []


# ---------------------------------------------------------------------------
# FindMigrationTargets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_migration_targets():
    """Returns AccountProfileDTOs for high-intent accounts."""
    account_a = _make_account(account_id="acc-a")
    account_b = _make_account(account_id="acc-b")

    repo = AsyncMock()
    repo.list_high_intent.return_value = (account_a, account_b)

    handler = FindMigrationTargetsHandler(account_repository=repo)
    result = await handler.execute(FindMigrationTargetsQuery(min_score=0.5))

    assert len(result) == 2
    assert result[0].account_id == "acc-a"
    assert result[1].account_id == "acc-b"
    repo.list_high_intent.assert_awaited_once_with(0.5)
