"""DTOs for the Stakeholder Discovery application layer."""

from __future__ import annotations

from pydantic import BaseModel

from searce_scout.stakeholder_discovery.domain.entities.stakeholder import Stakeholder
from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    ValidationStatus,
)


class StakeholderDTO(BaseModel):
    stakeholder_id: str
    account_id: str
    first_name: str
    last_name: str
    full_name: str
    job_title: str
    seniority: str
    department: str
    email: str | None
    phone: str | None
    email_status: str
    phone_status: str
    relevance_score: float | None
    persona_match_offering: str | None
    persona_match_confidence: float | None
    linkedin_url: str | None
    is_decision_maker: bool

    @classmethod
    def from_domain(cls, stakeholder: Stakeholder) -> StakeholderDTO:
        contact = stakeholder.contact_info
        email: str | None = None
        phone: str | None = None
        email_status = ValidationStatus.UNVALIDATED.value
        phone_status = ValidationStatus.UNVALIDATED.value

        if contact is not None:
            email = str(contact.email) if contact.email else None
            phone = str(contact.phone) if contact.phone else None
            email_status = contact.email_status.value
            phone_status = contact.phone_status.value

        relevance_score: float | None = None
        if stakeholder.relevance_score is not None:
            relevance_score = stakeholder.relevance_score.score

        persona_offering: str | None = None
        persona_confidence: float | None = None
        if stakeholder.persona_match is not None:
            persona_offering = stakeholder.persona_match.searce_offering
            persona_confidence = stakeholder.persona_match.confidence

        return cls(
            stakeholder_id=str(stakeholder.stakeholder_id),
            account_id=str(stakeholder.account_id),
            first_name=stakeholder.person_name.first_name,
            last_name=stakeholder.person_name.last_name,
            full_name=stakeholder.person_name.full_name,
            job_title=stakeholder.job_title.raw_title,
            seniority=stakeholder.seniority.value,
            department=stakeholder.department.value,
            email=email,
            phone=phone,
            email_status=email_status,
            phone_status=phone_status,
            relevance_score=relevance_score,
            persona_match_offering=persona_offering,
            persona_match_confidence=persona_confidence,
            linkedin_url=str(stakeholder.linkedin_url) if stakeholder.linkedin_url else None,
            is_decision_maker=stakeholder.is_decision_maker(),
        )
