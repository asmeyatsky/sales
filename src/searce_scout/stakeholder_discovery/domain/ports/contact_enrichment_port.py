"""Port (driven adapter interface) for contact enrichment and email validation."""

from __future__ import annotations

from typing import Protocol

from searce_scout.shared_kernel.value_objects import EmailAddress, PersonName

from searce_scout.stakeholder_discovery.domain.entities.contact_info import ContactInfo
from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    ValidationStatus,
)


class ContactEnrichmentPort(Protocol):
    async def enrich_contact(
        self, person_name: PersonName, company_name: str
    ) -> ContactInfo: ...

    async def validate_email(
        self, email: EmailAddress
    ) -> ValidationStatus: ...
