"""Pure domain tests for TechStackAnalysisService.

No mocks — verifies migration-potential levels for various tech-stack
configurations.
"""

from searce_scout.account_intelligence.domain.services.tech_stack_analysis import (
    TechStackAnalysisService,
)
from searce_scout.account_intelligence.domain.value_objects.tech_stack import (
    CloudProvider,
    TechComponent,
    TechStack,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stack(
    components: tuple[TechComponent, ...],
    primary: CloudProvider | None,
) -> TechStack:
    return TechStack(components=components, primary_cloud=primary)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAnalyzeMigrationPotential:
    def test_analyze_aws_primary_returns_high_migration_potential(self) -> None:
        ts = _stack(
            components=(
                TechComponent(name="EC2", category="compute", provider=CloudProvider.AWS),
                TechComponent(name="RDS", category="database", provider=CloudProvider.AWS),
            ),
            primary=CloudProvider.AWS,
        )
        result = TechStackAnalysisService.analyze_migration_potential(ts)
        assert result.level == "HIGH"

    def test_analyze_gcp_primary_returns_none(self) -> None:
        ts = _stack(
            components=(
                TechComponent(name="GCE", category="compute", provider=CloudProvider.GCP),
            ),
            primary=CloudProvider.GCP,
        )
        result = TechStackAnalysisService.analyze_migration_potential(ts)
        assert result.level == "NONE"

    def test_analyze_on_prem_heavy_returns_high(self) -> None:
        ts = _stack(
            components=(
                TechComponent(name="VMWare", category="compute", provider=CloudProvider.ON_PREM),
                TechComponent(name="Oracle DB", category="database", provider=CloudProvider.ON_PREM),
                TechComponent(name="NAS", category="storage", provider=CloudProvider.ON_PREM),
            ),
            primary=CloudProvider.ON_PREM,
        )
        result = TechStackAnalysisService.analyze_migration_potential(ts)
        assert result.level == "HIGH"
        assert "on-prem" in result.rationale.lower() or "On-prem" in result.rationale

    def test_analyze_empty_tech_stack(self) -> None:
        ts = _stack(components=(), primary=CloudProvider.UNKNOWN)
        result = TechStackAnalysisService.analyze_migration_potential(ts)
        # No competitor, no on-prem, not GCP => LOW (insufficient data)
        assert result.level == "LOW"
