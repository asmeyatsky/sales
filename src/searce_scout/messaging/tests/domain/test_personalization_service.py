"""Pure domain tests for PersonalizationService.

No mocks — verifies that build_context assembles a correct
PersonalizationContext from raw inputs.
"""

from searce_scout.messaging.domain.services.personalization_service import (
    PersonalizationService,
)
from searce_scout.messaging.domain.value_objects.personalization import (
    CaseStudyRef,
    PersonalizationContext,
)


class TestBuildContext:
    def test_build_context_returns_correct_fields(self) -> None:
        service = PersonalizationService()

        case_study = CaseStudyRef(
            title="Retail Cloud Migration",
            industry="Retail",
            outcome_summary="50% cost reduction",
            metric="$2M annual savings",
        )

        ctx = service.build_context(
            company_name="BigCo",
            stakeholder_name="John Smith",
            job_title="CTO",
            buying_signals=("New CTO", "Cloud RFP"),
            tech_stack_summary="AWS EC2, RDS",
            pain_points=("scalability", "cost"),
            case_studies=(case_study,),
            offering="Cloud Migration",
        )

        assert isinstance(ctx, PersonalizationContext)
        assert ctx.company_name == "BigCo"
        assert ctx.stakeholder_name == "John Smith"
        assert ctx.job_title == "CTO"
        assert ctx.buying_signals == ("New CTO", "Cloud RFP")
        assert ctx.tech_stack_summary == "AWS EC2, RDS"
        assert ctx.pain_points == ("scalability", "cost")
        assert ctx.relevant_case_studies == (case_study,)
        assert ctx.searce_offering == "Cloud Migration"
