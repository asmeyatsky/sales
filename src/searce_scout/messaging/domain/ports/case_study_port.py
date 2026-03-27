"""Port for accessing Searce case study data."""

from __future__ import annotations

from typing import Protocol

from searce_scout.messaging.domain.value_objects.personalization import CaseStudyRef


class CaseStudyPort(Protocol):
    """Driven port for retrieving relevant case studies.

    Infrastructure adapters implement this to query a case study
    repository or knowledge base.
    """

    async def find_by_industry(self, industry: str) -> tuple[CaseStudyRef, ...]:
        """Find case studies matching a given industry.

        Args:
            industry: The industry vertical to search for.

        Returns:
            Matching case study references, possibly empty.
        """
        ...

    async def find_by_offering(self, offering: str) -> tuple[CaseStudyRef, ...]:
        """Find case studies showcasing a specific Searce offering.

        Args:
            offering: The Searce service or product offering.

        Returns:
            Matching case study references, possibly empty.
        """
        ...
