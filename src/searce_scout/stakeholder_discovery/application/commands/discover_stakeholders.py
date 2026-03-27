"""Command and handler for discovering stakeholders at a target account."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort

from searce_scout.stakeholder_discovery.application.dtos.stakeholder_dtos import (
    StakeholderDTO,
)
from searce_scout.stakeholder_discovery.application.orchestration.stakeholder_discovery_workflow import (
    StakeholderDiscoveryWorkflow,
)
from searce_scout.stakeholder_discovery.domain.ports.contact_enrichment_port import (
    ContactEnrichmentPort,
)
from searce_scout.stakeholder_discovery.domain.ports.linkedin_port import (
    LinkedInPort,
)
from searce_scout.stakeholder_discovery.domain.ports.stakeholder_repository_port import (
    StakeholderRepositoryPort,
)
from searce_scout.stakeholder_discovery.domain.services.persona_matching import (
    PersonaMatchingService,
)


@dataclass(frozen=True)
class DiscoverStakeholdersCommand:
    account_id: str
    company_name: str


class DiscoverStakeholdersHandler:
    """Orchestrates stakeholder discovery by delegating to the workflow."""

    def __init__(
        self,
        linkedin_port: LinkedInPort,
        contact_enrichment: ContactEnrichmentPort,
        stakeholder_repository: StakeholderRepositoryPort,
        event_bus: EventBusPort,
        persona_matching_service: PersonaMatchingService,
    ) -> None:
        self._linkedin_port = linkedin_port
        self._contact_enrichment = contact_enrichment
        self._stakeholder_repository = stakeholder_repository
        self._event_bus = event_bus
        self._persona_matching_service = persona_matching_service

    async def execute(self, cmd: DiscoverStakeholdersCommand) -> list[StakeholderDTO]:
        workflow = StakeholderDiscoveryWorkflow(
            linkedin_port=self._linkedin_port,
            contact_enrichment=self._contact_enrichment,
            persona_matching_service=self._persona_matching_service,
        )

        stakeholders = await workflow.execute(
            account_id=cmd.account_id,
            company_name=cmd.company_name,
        )

        # Persist each stakeholder and collect events
        for stakeholder in stakeholders:
            await self._stakeholder_repository.save(stakeholder)
            if stakeholder.domain_events:
                await self._event_bus.publish(stakeholder.domain_events)

        return [StakeholderDTO.from_domain(s) for s in stakeholders]
