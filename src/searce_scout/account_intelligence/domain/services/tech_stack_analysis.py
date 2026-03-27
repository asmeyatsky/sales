"""Tech stack analysis domain service."""

from __future__ import annotations

from dataclasses import dataclass

from searce_scout.account_intelligence.domain.value_objects.tech_stack import (
    CloudProvider,
    TechStack,
)


@dataclass(frozen=True)
class MigrationPotential:
    level: str  # HIGH / MEDIUM / LOW / NONE
    recommended_offering: str
    rationale: str


class TechStackAnalysisService:
    """Stateless domain service that evaluates a tech stack for migration potential."""

    @staticmethod
    def analyze_migration_potential(tech_stack: TechStack) -> MigrationPotential:
        """Determine migration potential based on cloud provider mix and on-prem ratio."""
        on_prem_ratio = tech_stack.on_prem_ratio()
        has_competitor = tech_stack.has_competitor_cloud()

        # Determine primary cloud for recommendation context
        primary = tech_stack.primary_cloud

        if on_prem_ratio > 0.5:
            return MigrationPotential(
                level="HIGH",
                recommended_offering="Cloud Foundation & Migration",
                rationale=(
                    f"High on-prem ratio ({on_prem_ratio:.0%}) indicates significant "
                    "migration opportunity to GCP."
                ),
            )

        if has_competitor and primary in {CloudProvider.AWS, CloudProvider.AZURE}:
            return MigrationPotential(
                level="HIGH",
                recommended_offering="Multi-Cloud Optimization / GCP Migration",
                rationale=(
                    f"Primary cloud is {primary.value}; competitor workloads "
                    "can be migrated or optimised on GCP."
                ),
            )

        if has_competitor:
            return MigrationPotential(
                level="MEDIUM",
                recommended_offering="Cloud Modernization",
                rationale="Competitor cloud components detected; partial migration viable.",
            )

        if on_prem_ratio > 0.0:
            return MigrationPotential(
                level="LOW",
                recommended_offering="Hybrid Cloud Strategy",
                rationale="Some on-prem components remain but limited migration surface.",
            )

        if primary == CloudProvider.GCP:
            return MigrationPotential(
                level="NONE",
                recommended_offering="GCP Optimization & Managed Services",
                rationale="Already on GCP; focus on optimization and advanced services.",
            )

        return MigrationPotential(
            level="LOW",
            recommended_offering="Cloud Assessment",
            rationale="Insufficient data to determine strong migration potential.",
        )
