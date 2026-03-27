"""Pure domain tests for PersonaMatchingService.

No mocks — verifies the deterministic title/seniority/department
to Searce-offering mapping logic.
"""

from searce_scout.stakeholder_discovery.domain.services.persona_matching import (
    PersonaMatchingService,
)
from searce_scout.stakeholder_discovery.domain.value_objects.job_title import JobTitle
from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    Department,
    Seniority,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPersonaMatching:
    def test_cto_matches_cloud_migration(self) -> None:
        result = PersonaMatchingService.match_to_persona(
            job_title=JobTitle(raw_title="Chief Technology Officer", normalized_title="CTO"),
            seniority=Seniority.C_SUITE,
            department=Department.ENGINEERING,
        )
        assert result is not None
        assert result.searce_offering == "Cloud Migration"
        assert result.confidence > 0

    def test_head_of_data_matches_data_analytics(self) -> None:
        result = PersonaMatchingService.match_to_persona(
            job_title=JobTitle(raw_title="Head of Data", normalized_title="Head of Data"),
            seniority=Seniority.HEAD,
            department=Department.DATA,
        )
        assert result is not None
        assert result.searce_offering == "Data & Analytics"

    def test_cdo_matches_applied_ai(self) -> None:
        result = PersonaMatchingService.match_to_persona(
            job_title=JobTitle(
                raw_title="Chief Digital Officer",
                normalized_title="CDO",
            ),
            seniority=Seniority.C_SUITE,
            department=Department.INNOVATION,
        )
        assert result is not None
        assert result.searce_offering == "Applied AI / GenAI"

    def test_head_of_hr_matches_future_of_work(self) -> None:
        result = PersonaMatchingService.match_to_persona(
            job_title=JobTitle(
                raw_title="Head of Human Resources",
                normalized_title="Head of HR",
            ),
            seniority=Seniority.HEAD,
            department=Department.HR,
        )
        assert result is not None
        assert result.searce_offering == "Future of Work"

    def test_unknown_title_returns_none(self) -> None:
        result = PersonaMatchingService.match_to_persona(
            job_title=JobTitle(
                raw_title="Marketing Manager",
                normalized_title="Marketing Manager",
            ),
            seniority=Seniority.MANAGER,
            department=Department.OPERATIONS,
        )
        assert result is None
