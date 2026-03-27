"""Pure domain tests for the Stakeholder aggregate root.

No mocks — exercises frozen-dataclass behaviour, contact validation,
relevance scoring, and the is_decision_maker query.
"""

from datetime import datetime, UTC

from searce_scout.shared_kernel.types import AccountId, StakeholderId
from searce_scout.shared_kernel.value_objects import EmailAddress, PersonName

from searce_scout.stakeholder_discovery.domain.entities.contact_info import ContactInfo
from searce_scout.stakeholder_discovery.domain.entities.stakeholder import Stakeholder
from searce_scout.stakeholder_discovery.domain.events.stakeholder_events import (
    ContactValidatedEvent,
    StakeholderScoredEvent,
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stakeholder(
    seniority: Seniority = Seniority.C_SUITE,
) -> Stakeholder:
    return Stakeholder(
        stakeholder_id=StakeholderId("stk-001"),
        account_id=AccountId("acct-001"),
        person_name=PersonName(first_name="Jane", last_name="Doe"),
        job_title=JobTitle(raw_title="CTO", normalized_title="CTO"),
        seniority=seniority,
        department=Department.ENGINEERING,
        contact_info=None,
        relevance_score=None,
        persona_match=None,
        linkedin_url=None,
        domain_events=(),
    )


def _make_contact() -> ContactInfo:
    return ContactInfo(
        email=EmailAddress(value="jane@acme.com"),
        phone=None,
        email_status=ValidationStatus.VALID,
        phone_status=ValidationStatus.UNVALIDATED,
        source="apollo",
        validated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidateContact:
    def test_validate_contact_returns_new_instance_with_contact(self) -> None:
        stakeholder = _make_stakeholder()
        contact = _make_contact()

        updated = stakeholder.validate_contact(contact)

        # Original is untouched
        assert stakeholder.contact_info is None
        assert stakeholder.domain_events == ()

        # New instance has the contact
        assert updated.contact_info is contact
        assert len(updated.domain_events) == 1
        event = updated.domain_events[0]
        assert isinstance(event, ContactValidatedEvent)
        assert event.email_status == ValidationStatus.VALID


class TestScoreRelevance:
    def test_score_relevance_sets_score_and_match(self) -> None:
        stakeholder = _make_stakeholder()
        score = RelevanceScore(score=0.9, factors=("seniority", "department"))
        match = PersonaMatch(
            searce_offering="Cloud Migration",
            target_persona="CTO",
            pain_points=("legacy costs",),
            confidence=0.85,
        )

        updated = stakeholder.score_relevance(score, match)

        assert updated.relevance_score is score
        assert updated.persona_match is match
        assert len(updated.domain_events) == 1
        event = updated.domain_events[0]
        assert isinstance(event, StakeholderScoredEvent)
        assert event.relevance_score == 0.9
        assert event.persona_match == "Cloud Migration"


class TestIsDecisionMaker:
    def test_is_decision_maker_true_for_c_suite(self) -> None:
        for s in (Seniority.C_SUITE, Seniority.VP, Seniority.DIRECTOR, Seniority.HEAD):
            stakeholder = _make_stakeholder(seniority=s)
            assert stakeholder.is_decision_maker() is True, f"Expected True for {s}"

    def test_is_decision_maker_false_for_ic(self) -> None:
        for s in (Seniority.IC, Seniority.MANAGER):
            stakeholder = _make_stakeholder(seniority=s)
            assert stakeholder.is_decision_maker() is False, f"Expected False for {s}"
