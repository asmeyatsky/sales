"""Tech stack value objects for cloud provider and technology component modelling."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CloudProvider(Enum):
    AWS = "AWS"
    AZURE = "AZURE"
    GCP = "GCP"
    ON_PREM = "ON_PREM"
    HYBRID = "HYBRID"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TechComponent:
    name: str
    category: str  # compute / storage / database / ml / analytics
    provider: CloudProvider


@dataclass(frozen=True)
class TechStack:
    components: tuple[TechComponent, ...]
    primary_cloud: CloudProvider | None

    def has_competitor_cloud(self) -> bool:
        """Return True if any component runs on a non-GCP cloud provider."""
        competitor_providers = {CloudProvider.AWS, CloudProvider.AZURE}
        return any(c.provider in competitor_providers for c in self.components)

    def on_prem_ratio(self) -> float:
        """Return the fraction of components that are on-prem."""
        if not self.components:
            return 0.0
        on_prem_count = sum(
            1 for c in self.components if c.provider == CloudProvider.ON_PREM
        )
        return on_prem_count / len(self.components)

    def is_migration_target(self) -> bool:
        """Return True if this stack is a good candidate for GCP migration."""
        return self.has_competitor_cloud() or self.on_prem_ratio() > 0.3
