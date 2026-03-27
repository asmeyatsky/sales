"""Command and handler for auditing an account's tech stack."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.shared_kernel.errors import DomainError
from searce_scout.shared_kernel.ports.event_bus_port import EventBusPort
from searce_scout.shared_kernel.types import AccountId

from searce_scout.account_intelligence.application.dtos.account_dtos import (
    AccountProfileDTO,
)
from searce_scout.account_intelligence.domain.ports.account_repository_port import (
    AccountRepositoryPort,
)
from searce_scout.account_intelligence.domain.ports.tech_detector_port import (
    TechDetectorPort,
)
from searce_scout.account_intelligence.domain.services.tech_stack_analysis import (
    TechStackAnalysisService,
)


@dataclass(frozen=True)
class AuditTechStackCommand:
    account_id: str
    domain: str


class AuditTechStackHandler:
    """Detects an account's tech stack, analyses migration potential, and persists the update."""

    def __init__(
        self,
        tech_detector: TechDetectorPort,
        account_repository: AccountRepositoryPort,
        event_bus: EventBusPort,
        tech_stack_analysis_service: TechStackAnalysisService,
    ) -> None:
        self._tech_detector = tech_detector
        self._account_repository = account_repository
        self._event_bus = event_bus
        self._tech_stack_analysis_service = tech_stack_analysis_service

    async def execute(self, cmd: AuditTechStackCommand) -> AccountProfileDTO:
        account = await self._account_repository.get_by_id(
            AccountId(cmd.account_id)
        )
        if account is None:
            raise DomainError(f"Account not found: {cmd.account_id}")

        tech_stack = await self._tech_detector.detect_tech_stack(cmd.domain)

        # Run domain analysis (pure logic, no side effects)
        _migration_potential = self._tech_stack_analysis_service.analyze_migration_potential(
            tech_stack
        )

        # Update aggregate -- produces a TechStackAuditedEvent internally
        account = account.set_tech_stack(tech_stack)

        await self._account_repository.save(account)

        if account.domain_events:
            await self._event_bus.publish(account.domain_events)

        return AccountProfileDTO.from_domain(account)
