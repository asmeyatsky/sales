"""Pure domain tests for the AccountProfile aggregate root.

No mocks — tests exercise frozen-dataclass behaviour, domain event
emission, and score/intent computations with real value objects.
"""

from datetime import datetime, UTC

from searce_scout.shared_kernel.types import AccountId
from searce_scout.shared_kernel.value_objects import CompanyName

from searce_scout.account_intelligence.domain.entities.account_profile import (
    AccountProfile,
)
from searce_scout.account_intelligence.domain.entities.buying_signal import (
    BuyingSignal,
)
from searce_scout.account_intelligence.domain.events.account_events import (
    BuyingSignalDetectedEvent,
    TechStackAuditedEvent,
)
from searce_scout.account_intelligence.domain.value_objects.industry import (
    CompanySize,
    Industry,
)
from searce_scout.account_intelligence.domain.value_objects.signal_type import (
    SignalStrength,
    SignalType,
)
from searce_scout.account_intelligence.domain.value_objects.tech_stack import (
    CloudProvider,
    TechComponent,
    TechStack,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_profile(
    tech_stack: TechStack | None = None,
    buying_signals: tuple[BuyingSignal, ...] = (),
) -> AccountProfile:
    return AccountProfile(
        account_id=AccountId("acct-001"),
        company_name=CompanyName(canonical="Acme Corp"),
        industry=Industry(name="Technology", vertical="SaaS"),
        company_size=CompanySize.ENTERPRISE,
        tech_stack=tech_stack,
        buying_signals=buying_signals,
        filing_data=None,
        website=None,
        researched_at=None,
        domain_events=(),
    )


def _make_signal(
    signal_type: SignalType = SignalType.NEW_EXECUTIVE,
    strength: SignalStrength = SignalStrength.CRITICAL,
) -> BuyingSignal:
    return BuyingSignal(
        signal_id="sig-001",
        signal_type=signal_type,
        strength=strength,
        description="test signal",
        source_url=None,
        detected_at=datetime.now(UTC),
    )


def _aws_tech_stack() -> TechStack:
    return TechStack(
        components=(
            TechComponent(name="EC2", category="compute", provider=CloudProvider.AWS),
            TechComponent(name="S3", category="storage", provider=CloudProvider.AWS),
        ),
        primary_cloud=CloudProvider.AWS,
    )


def _gcp_tech_stack() -> TechStack:
    return TechStack(
        components=(
            TechComponent(name="GCE", category="compute", provider=CloudProvider.GCP),
            TechComponent(name="GCS", category="storage", provider=CloudProvider.GCP),
        ),
        primary_cloud=CloudProvider.GCP,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAddBuyingSignal:
    def test_add_buying_signal_returns_new_instance(self) -> None:
        profile = _make_profile()
        signal = _make_signal()

        updated = profile.add_buying_signal(signal)

        # Original unchanged
        assert profile.buying_signals == ()
        assert profile.domain_events == ()

        # New instance has the signal
        assert len(updated.buying_signals) == 1
        assert updated.buying_signals[0] is signal

        # Domain event appended
        assert len(updated.domain_events) == 1
        assert isinstance(updated.domain_events[0], BuyingSignalDetectedEvent)


class TestSetTechStack:
    def test_set_tech_stack_returns_new_instance(self) -> None:
        profile = _make_profile()
        ts = _aws_tech_stack()

        updated = profile.set_tech_stack(ts)

        # Original unchanged
        assert profile.tech_stack is None
        assert profile.domain_events == ()

        # New instance carries the tech stack
        assert updated.tech_stack is ts
        assert len(updated.domain_events) == 1
        event = updated.domain_events[0]
        assert isinstance(event, TechStackAuditedEvent)
        assert event.primary_cloud == CloudProvider.AWS
        assert event.is_migration_target is True


class TestMigrationOpportunityScore:
    def test_migration_opportunity_score_high_for_aws_with_strong_signals(
        self,
    ) -> None:
        """AWS tech stack (competitor cloud => +0.3) plus a CRITICAL
        NEW_EXECUTIVE signal (weight 0.3 * multiplier 1.0 = 0.3,
        then *0.7 = 0.21) should produce a meaningful score."""
        signal = _make_signal(
            signal_type=SignalType.NEW_EXECUTIVE,
            strength=SignalStrength.CRITICAL,
        )
        profile = _make_profile(
            tech_stack=_aws_tech_stack(),
            buying_signals=(signal,),
        )

        score = profile.migration_opportunity_score()
        # 0.3 (competitor cloud) + 0.3 * 1.0 * 0.7 (signal) = 0.51
        assert score > 0.5

    def test_migration_opportunity_score_zero_for_gcp_native(self) -> None:
        """A pure GCP stack with no buying signals should score 0.0."""
        profile = _make_profile(tech_stack=_gcp_tech_stack())

        score = profile.migration_opportunity_score()
        assert score == 0.0


class TestIsHighIntent:
    def test_is_high_intent_true_when_score_above_threshold(self) -> None:
        """Stack multiple strong signals so the total exceeds 0.7."""
        signals = (
            _make_signal(SignalType.NEW_EXECUTIVE, SignalStrength.CRITICAL),
            _make_signal(SignalType.DIGITAL_TRANSFORMATION_GOAL, SignalStrength.CRITICAL),
            _make_signal(SignalType.VENDOR_CONTRACT_EXPIRY, SignalStrength.CRITICAL),
        )
        profile = _make_profile(
            tech_stack=_aws_tech_stack(),
            buying_signals=signals,
        )
        assert profile.is_high_intent() is True

    def test_is_high_intent_false_when_no_signals(self) -> None:
        profile = _make_profile()
        assert profile.is_high_intent() is False
