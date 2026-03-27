"""Persona matching domain service."""

from __future__ import annotations

from searce_scout.stakeholder_discovery.domain.value_objects.job_title import JobTitle
from searce_scout.stakeholder_discovery.domain.value_objects.relevance_score import (
    PersonaMatch,
)
from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    Department,
    Seniority,
)


class PersonaMatchingService:
    """Stateless domain service that maps stakeholder roles to Searce offerings."""

    @staticmethod
    def match_to_persona(
        job_title: JobTitle,
        seniority: Seniority,
        department: Department,
    ) -> PersonaMatch | None:
        """Match a stakeholder profile to a Searce target persona.

        Pure mapping logic:
        - CTO / VP Infrastructure -> Cloud Migration
        - Head of Innovation / CDO -> Applied AI / GenAI
        - Head of Data -> Data & Analytics
        - Head of HR / CIO -> Future of Work
        Returns None if no match is found.
        """
        title_lower = job_title.normalized_title.lower()

        # CTO or VP Infrastructure -> Cloud Migration
        if "cto" in title_lower or (
            seniority == Seniority.VP
            and department == Department.IT_INFRASTRUCTURE
        ):
            return PersonaMatch(
                searce_offering="Cloud Migration",
                target_persona="CTO / VP Infrastructure",
                pain_points=(
                    "Legacy infrastructure costs",
                    "Scalability constraints",
                    "Cloud skills gap",
                ),
                confidence=0.85,
            )

        # Head of Innovation or CDO -> Applied AI / GenAI
        if "chief digital" in title_lower or "cdo" in title_lower or (
            seniority in {Seniority.HEAD, Seniority.C_SUITE, Seniority.VP, Seniority.DIRECTOR}
            and department == Department.INNOVATION
        ):
            return PersonaMatch(
                searce_offering="Applied AI / GenAI",
                target_persona="Head of Innovation / CDO",
                pain_points=(
                    "AI adoption roadmap",
                    "GenAI use-case identification",
                    "Innovation velocity",
                ),
                confidence=0.80,
            )

        # Head of Data -> Data & Analytics
        if department == Department.DATA and seniority in {
            Seniority.HEAD,
            Seniority.VP,
            Seniority.DIRECTOR,
            Seniority.C_SUITE,
        }:
            return PersonaMatch(
                searce_offering="Data & Analytics",
                target_persona="Head of Data",
                pain_points=(
                    "Data silos",
                    "Real-time analytics gaps",
                    "Data governance",
                ),
                confidence=0.80,
            )

        # Head of HR or CIO -> Future of Work
        if "cio" in title_lower or (
            seniority in {Seniority.HEAD, Seniority.VP, Seniority.DIRECTOR, Seniority.C_SUITE}
            and department == Department.HR
        ):
            return PersonaMatch(
                searce_offering="Future of Work",
                target_persona="Head of HR / CIO",
                pain_points=(
                    "Workspace modernization",
                    "Employee productivity",
                    "Digital collaboration tools",
                ),
                confidence=0.75,
            )

        return None
