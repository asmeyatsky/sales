"""Stakeholder aggregate root for the Stakeholder Discovery bounded context."""

from __future__ import annotations

from dataclasses import dataclass, replace

from searce_scout.shared_kernel.domain_event import DomainEvent
from searce_scout.shared_kernel.types import AccountId, StakeholderId
from searce_scout.shared_kernel.value_objects import PersonName, URL

from searce_scout.stakeholder_discovery.domain.entities.contact_info import ContactInfo
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
)


@dataclass(frozen=True)
class Stakeholder:
    """Aggregate root representing a discovered stakeholder at a target account."""

    stakeholder_id: StakeholderId
    account_id: AccountId
    person_name: PersonName
    job_title: JobTitle
    seniority: Seniority
    department: Department
    contact_info: ContactInfo | None
    relevance_score: RelevanceScore | None
    persona_match: PersonaMatch | None
    linkedin_url: URL | None
    domain_events: tuple[DomainEvent, ...]

    # ------------------------------------------------------------------
    # Command methods -- return new instances (frozen)
    # ------------------------------------------------------------------

    def validate_contact(self, contact: ContactInfo) -> Stakeholder:
        """Set validated contact information and record a domain event."""
        event = ContactValidatedEvent(
            aggregate_id=str(self.stakeholder_id),
            email_status=contact.email_status,
            phone_status=contact.phone_status,
        )
        return replace(
            self,
            contact_info=contact,
            domain_events=(*self.domain_events, event),
        )

    def score_relevance(
        self, score: RelevanceScore, match: PersonaMatch
    ) -> Stakeholder:
        """Assign relevance score and persona match, recording a domain event."""
        event = StakeholderScoredEvent(
            aggregate_id=str(self.stakeholder_id),
            relevance_score=score.score,
            persona_match=match.searce_offering,
        )
        return replace(
            self,
            relevance_score=score,
            persona_match=match,
            domain_events=(*self.domain_events, event),
        )

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def is_decision_maker(self) -> bool:
        """Return True if the stakeholder's seniority indicates decision-making authority."""
        return self.seniority in {
            Seniority.C_SUITE,
            Seniority.VP,
            Seniority.DIRECTOR,
            Seniority.HEAD,
        }
