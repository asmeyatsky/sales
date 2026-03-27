"""AccountProfile aggregate root for the Account Intelligence bounded context."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from searce_scout.shared_kernel.domain_event import DomainEvent
from searce_scout.shared_kernel.types import AccountId
from searce_scout.shared_kernel.value_objects import CompanyName, URL

from searce_scout.account_intelligence.domain.entities.buying_signal import (
    BuyingSignal,
)
from searce_scout.account_intelligence.domain.events.account_events import (
    BuyingSignalDetectedEvent,
    TechStackAuditedEvent,
)
from searce_scout.account_intelligence.domain.value_objects.filing_data import (
    FilingData,
)
from searce_scout.account_intelligence.domain.value_objects.industry import (
    CompanySize,
    Industry,
)
from searce_scout.account_intelligence.domain.value_objects.signal_type import (
    SignalStrength,
)
from searce_scout.account_intelligence.domain.value_objects.tech_stack import (
    TechStack,
)


_STRENGTH_MULTIPLIER: dict[SignalStrength, float] = {
    SignalStrength.WEAK: 0.25,
    SignalStrength.MODERATE: 0.5,
    SignalStrength.STRONG: 0.75,
    SignalStrength.CRITICAL: 1.0,
}


@dataclass(frozen=True)
class AccountProfile:
    """Aggregate root that consolidates all intelligence gathered for a target account."""

    account_id: AccountId
    company_name: CompanyName
    industry: Industry
    company_size: CompanySize
    tech_stack: TechStack | None
    buying_signals: tuple[BuyingSignal, ...]
    filing_data: FilingData | None
    website: URL | None
    researched_at: datetime | None
    domain_events: tuple[DomainEvent, ...]

    # ------------------------------------------------------------------
    # Command methods -- return new instances (frozen)
    # ------------------------------------------------------------------

    def add_buying_signal(self, signal: BuyingSignal) -> AccountProfile:
        """Append a buying signal and record a domain event."""
        event = BuyingSignalDetectedEvent(
            aggregate_id=str(self.account_id),
            signal_type=signal.signal_type,
            strength=signal.strength,
        )
        return replace(
            self,
            buying_signals=(*self.buying_signals, signal),
            domain_events=(*self.domain_events, event),
        )

    def set_tech_stack(self, tech_stack: TechStack) -> AccountProfile:
        """Replace the tech stack and record an audit event."""
        event = TechStackAuditedEvent(
            aggregate_id=str(self.account_id),
            primary_cloud=tech_stack.primary_cloud,
            is_migration_target=tech_stack.is_migration_target(),
        )
        return replace(
            self,
            tech_stack=tech_stack,
            domain_events=(*self.domain_events, event),
        )

    def set_filing_data(self, data: FilingData) -> AccountProfile:
        """Replace the filing data snapshot."""
        return replace(self, filing_data=data)

    # ------------------------------------------------------------------
    # Query methods -- pure computations
    # ------------------------------------------------------------------

    def migration_opportunity_score(self) -> float:
        """Score the migration opportunity based on tech stack and buying signals.

        The score combines:
        - Whether the tech stack contains competitor-cloud components
        - The weighted strength of detected buying signals
        The result is capped at 1.0.
        """
        score = 0.0

        # Tech-stack contribution
        if self.tech_stack is not None and self.tech_stack.has_competitor_cloud():
            score += 0.3

        # Signal contributions
        from searce_scout.account_intelligence.domain.services.signal_scoring import (
            BuyingSignalScoringService,
        )

        signal_score = BuyingSignalScoringService.score_signals(self.buying_signals)
        score += signal_score * 0.7

        return min(score, 1.0)

    def is_high_intent(self) -> bool:
        """Return True when the migration opportunity score exceeds the 0.7 threshold."""
        return self.migration_opportunity_score() > 0.7
