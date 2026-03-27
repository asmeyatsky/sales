"""BuiltWith technology detector adapter — implements TechDetectorPort.

Uses the BuiltWith API to discover what technologies a company's website
runs on, then maps each detected technology to a domain TechComponent
with an appropriate CloudProvider and category.
"""

from __future__ import annotations

import httpx

from searce_scout.account_intelligence.domain.ports.tech_detector_port import (
    TechDetectorPort,
)
from searce_scout.account_intelligence.domain.value_objects.tech_stack import (
    CloudProvider,
    TechComponent,
    TechStack,
)

_BUILTWITH_API_URL = "https://api.builtwith.com/v21/api.json"

# ------------------------------------------------------------------
# Technology -> (CloudProvider, category) mapping
# ------------------------------------------------------------------

_TECH_MAPPING: dict[str, tuple[CloudProvider, str]] = {
    # AWS
    "Amazon S3": (CloudProvider.AWS, "storage"),
    "Amazon EC2": (CloudProvider.AWS, "compute"),
    "Amazon CloudFront": (CloudProvider.AWS, "cdn"),
    "Amazon RDS": (CloudProvider.AWS, "database"),
    "AWS Lambda": (CloudProvider.AWS, "compute"),
    "Amazon DynamoDB": (CloudProvider.AWS, "database"),
    "Amazon Redshift": (CloudProvider.AWS, "analytics"),
    "Amazon SQS": (CloudProvider.AWS, "messaging"),
    "Amazon ECS": (CloudProvider.AWS, "compute"),
    "Amazon EKS": (CloudProvider.AWS, "compute"),
    "AWS Elastic Beanstalk": (CloudProvider.AWS, "compute"),
    "Amazon SageMaker": (CloudProvider.AWS, "ml"),
    # Azure
    "Azure Blob": (CloudProvider.AZURE, "storage"),
    "Azure Blob Storage": (CloudProvider.AZURE, "storage"),
    "Azure CDN": (CloudProvider.AZURE, "cdn"),
    "Azure SQL": (CloudProvider.AZURE, "database"),
    "Azure App Service": (CloudProvider.AZURE, "compute"),
    "Azure Functions": (CloudProvider.AZURE, "compute"),
    "Azure Kubernetes Service": (CloudProvider.AZURE, "compute"),
    "Azure Cosmos DB": (CloudProvider.AZURE, "database"),
    "Azure DevOps": (CloudProvider.AZURE, "devops"),
    "Azure Machine Learning": (CloudProvider.AZURE, "ml"),
    "Microsoft Azure": (CloudProvider.AZURE, "compute"),
    # GCP
    "BigQuery": (CloudProvider.GCP, "analytics"),
    "Google Cloud Storage": (CloudProvider.GCP, "storage"),
    "Google Cloud Functions": (CloudProvider.GCP, "compute"),
    "Google Compute Engine": (CloudProvider.GCP, "compute"),
    "Google App Engine": (CloudProvider.GCP, "compute"),
    "Google Kubernetes Engine": (CloudProvider.GCP, "compute"),
    "Cloud Spanner": (CloudProvider.GCP, "database"),
    "Cloud SQL": (CloudProvider.GCP, "database"),
    "Vertex AI": (CloudProvider.GCP, "ml"),
    "Firebase": (CloudProvider.GCP, "compute"),
    "Google Cloud CDN": (CloudProvider.GCP, "cdn"),
    # On-prem / traditional
    "Apache": (CloudProvider.ON_PREM, "compute"),
    "Nginx": (CloudProvider.ON_PREM, "compute"),
    "IIS": (CloudProvider.ON_PREM, "compute"),
    "Oracle Database": (CloudProvider.ON_PREM, "database"),
    "Microsoft SQL Server": (CloudProvider.ON_PREM, "database"),
    "MySQL": (CloudProvider.ON_PREM, "database"),
    "PostgreSQL": (CloudProvider.ON_PREM, "database"),
    "MongoDB": (CloudProvider.ON_PREM, "database"),
    "VMware": (CloudProvider.ON_PREM, "compute"),
    "Hadoop": (CloudProvider.ON_PREM, "analytics"),
}


class BuiltWithDetector:
    """Detects a website's technology stack via the BuiltWith API.

    Implements :class:`TechDetectorPort`.
    """

    def __init__(
        self,
        *,
        api_key: str,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout

    # ------------------------------------------------------------------
    # TechDetectorPort implementation
    # ------------------------------------------------------------------

    async def detect_tech_stack(self, domain: str) -> TechStack:
        """Query BuiltWith for *domain* and return a mapped TechStack."""
        raw_technologies = await self._fetch_technologies(domain)
        components = self._map_technologies(raw_technologies)
        primary_cloud = self._determine_primary_cloud(components)
        return TechStack(components=tuple(components), primary_cloud=primary_cloud)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_technologies(self, domain: str) -> list[str]:
        """Call the BuiltWith API and return a flat list of technology names."""
        params = {"KEY": self._api_key, "LOOKUP": domain}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(_BUILTWITH_API_URL, params=params)
            response.raise_for_status()

        data = response.json()
        tech_names: list[str] = []

        results = data.get("Results", [])
        for result in results:
            paths = result.get("Result", {}).get("Paths", [])
            for path in paths:
                technologies = path.get("Technologies", [])
                for tech in technologies:
                    name = tech.get("Name", "")
                    if name:
                        tech_names.append(name)

        return tech_names

    @staticmethod
    def _map_technologies(tech_names: list[str]) -> list[TechComponent]:
        """Map raw technology names to domain TechComponent objects."""
        components: list[TechComponent] = []
        seen: set[str] = set()

        for name in tech_names:
            if name in seen:
                continue
            seen.add(name)

            if name in _TECH_MAPPING:
                provider, category = _TECH_MAPPING[name]
            else:
                provider = CloudProvider.UNKNOWN
                category = "other"

            components.append(
                TechComponent(name=name, category=category, provider=provider)
            )

        return components

    @staticmethod
    def _determine_primary_cloud(
        components: list[TechComponent],
    ) -> CloudProvider | None:
        """Determine which cloud provider has the most detected components."""
        cloud_providers = {CloudProvider.AWS, CloudProvider.AZURE, CloudProvider.GCP}
        counts: dict[CloudProvider, int] = {p: 0 for p in cloud_providers}

        for comp in components:
            if comp.provider in cloud_providers:
                counts[comp.provider] += 1

        max_count = max(counts.values()) if counts else 0
        if max_count == 0:
            return None

        # Return the provider with the highest count
        return max(counts, key=lambda p: counts[p])


# Structural compatibility assertion
def _check_port_compliance() -> None:
    _: TechDetectorPort = BuiltWithDetector(api_key="test")  # type: ignore[assignment]
