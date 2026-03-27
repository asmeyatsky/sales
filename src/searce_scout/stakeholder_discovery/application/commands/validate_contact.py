"""Command and handler for validating a stakeholder's contact information."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.errors import DomainError
from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import StakeholderId

from searce_scout.stakeholder_discovery.application.dtos.stakeholder_dtos import (
    StakeholderDTO,
)
from searce_scout.stakeholder_discovery.domain.ports.contact_enrichment_port import (
    ContactEnrichmentPort,
)
from searce_scout.stakeholder_discovery.domain.ports.stakeholder_repository_port import (
    StakeholderRepositoryPort,
)


@dataclass(frozen=True)
class ValidateContactCommand:
    stakeholder_id: str


class ValidateContactHandler:
    """Enriches and validates contact info for a single stakeholder."""

    def __init__(
        self,
        contact_enrichment: ContactEnrichmentPort,
        stakeholder_repository: StakeholderRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._contact_enrichment = contact_enrichment
        self._stakeholder_repository = stakeholder_repository
        self._event_bus = event_bus

    async def execute(self, cmd: ValidateContactCommand) -> StakeholderDTO:
        stakeholder = await self._stakeholder_repository.get_by_id(
            StakeholderId(cmd.stakeholder_id)
        )
        if stakeholder is None:
            raise DomainError(f"Stakeholder not found: {cmd.stakeholder_id}")

        # Enrich contact information via the external port
        contact_info = await self._contact_enrichment.enrich_contact(
            person_name=stakeholder.person_name,
            company_name="",  # company_name not stored on stakeholder; enrichment uses name
        )

        # Update aggregate -- produces a ContactValidatedEvent internally
        stakeholder = stakeholder.validate_contact(contact_info)

        await self._stakeholder_repository.save(stakeholder)

        if stakeholder.domain_events:
            await self._event_bus.publish(stakeholder.domain_events)

        return StakeholderDTO.from_domain(stakeholder)
