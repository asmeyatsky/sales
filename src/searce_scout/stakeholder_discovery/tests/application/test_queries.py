"""Tests for Stakeholder Discovery query handlers."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from searce_scout.shared_kernel.types import AccountId, StakeholderId
from searce_scout.shared_kernel.value_objects import EmailAddress, PersonName

from searce_scout.stakeholder_discovery.application.queries.get_stakeholders_for_account import (
    GetStakeholdersForAccountHandler,
    GetStakeholdersForAccountQuery,
)
from searce_scout.stakeholder_discovery.application.queries.get_validated_contacts import (
    GetValidatedContactsHandler,
    GetValidatedContactsQuery,
)
from searce_scout.stakeholder_discovery.domain.entities.contact_info import ContactInfo
from searce_scout.stakeholder_discovery.domain.entities.stakeholder import Stakeholder
from searce_scout.stakeholder_discovery.domain.value_objects.job_title import JobTitle
from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    Department,
    Seniority,
    ValidationStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_stakeholder(
    stakeholder_id: str = "stk-1",
    email_status: ValidationStatus = ValidationStatus.VALID,
    has_contact: bool = True,
) -> Stakeholder:
    contact: ContactInfo | None = None
    if has_contact:
        contact = ContactInfo(
            email=EmailAddress("jane@acme.com"),
            phone=None,
            email_status=email_status,
            phone_status=ValidationStatus.UNVALIDATED,
            source="linkedin",
            validated_at=datetime(2026, 2, 1),
        )
    return Stakeholder(
        stakeholder_id=StakeholderId(stakeholder_id),
        account_id=AccountId("acc-1"),
        person_name=PersonName(first_name="Jane", last_name="Doe"),
        job_title=JobTitle(raw_title="CTO", normalized_title="Chief Technology Officer"),
        seniority=Seniority.C_SUITE,
        department=Department.ENGINEERING,
        contact_info=contact,
        relevance_score=None,
        persona_match=None,
        linkedin_url=None,
        domain_events=(),
    )


# ---------------------------------------------------------------------------
# GetStakeholdersForAccount
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_stakeholders_for_account():
    """Returns a list of StakeholderDTOs for the given account."""
    stk = _make_stakeholder()
    repo = AsyncMock()
    repo.find_by_account.return_value = (stk,)

    handler = GetStakeholdersForAccountHandler(stakeholder_repository=repo)
    result = await handler.execute(
        GetStakeholdersForAccountQuery(account_id="acc-1")
    )

    assert len(result) == 1
    assert result[0].stakeholder_id == "stk-1"
    assert result[0].full_name == "Jane Doe"
    assert result[0].job_title == "CTO"
    repo.find_by_account.assert_awaited_once_with(AccountId("acc-1"))


# ---------------------------------------------------------------------------
# GetValidatedContacts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_validated_contacts():
    """Filters to stakeholders with VALID email status only."""
    valid_stk = _make_stakeholder(
        stakeholder_id="stk-valid", email_status=ValidationStatus.VALID
    )
    invalid_stk = _make_stakeholder(
        stakeholder_id="stk-invalid", email_status=ValidationStatus.INVALID
    )
    no_contact_stk = _make_stakeholder(
        stakeholder_id="stk-none", has_contact=False
    )

    repo = AsyncMock()
    repo.find_by_account.return_value = (valid_stk, invalid_stk, no_contact_stk)

    handler = GetValidatedContactsHandler(stakeholder_repository=repo)
    result = await handler.execute(
        GetValidatedContactsQuery(account_id="acc-1")
    )

    assert len(result) == 1
    assert result[0].stakeholder_id == "stk-valid"
    assert result[0].email_status == "VALID"
