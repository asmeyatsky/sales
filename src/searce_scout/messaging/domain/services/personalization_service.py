"""Domain service for building personalization contexts."""

from __future__ import annotations

from searce_scout.messaging.domain.value_objects.personalization import (
    CaseStudyRef,
    PersonalizationContext,
)


class PersonalizationService:
    """Assembles a PersonalizationContext from raw inputs.

    This is a pure domain service with no infrastructure dependencies.
    """

    def build_context(
        self,
        company_name: str,
        stakeholder_name: str,
        job_title: str,
        buying_signals: tuple[str, ...],
        tech_stack_summary: str,
        pain_points: tuple[str, ...],
        case_studies: tuple[CaseStudyRef, ...],
        offering: str,
    ) -> PersonalizationContext:
        """Construct a validated PersonalizationContext.

        Args:
            company_name: Target company name.
            stakeholder_name: Target stakeholder's full name.
            job_title: Stakeholder's job title.
            buying_signals: Detected buying signals for the company.
            tech_stack_summary: Summary of the company's technology stack.
            pain_points: Identified pain points or challenges.
            case_studies: Relevant Searce case study references.
            offering: The Searce offering to position.

        Returns:
            A fully populated PersonalizationContext.
        """
        return PersonalizationContext(
            company_name=company_name,
            stakeholder_name=stakeholder_name,
            job_title=job_title,
            buying_signals=buying_signals,
            tech_stack_summary=tech_stack_summary,
            pain_points=pain_points,
            relevant_case_studies=case_studies,
            searce_offering=offering,
        )
