"""DAG-orchestrated workflow for stakeholder discovery."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from searce_scout.shared_kernel.orchestration.dag_orchestrator import (
    DAGOrchestrator,
    WorkflowStep,
)
from searce_scout.shared_kernel.types import AccountId, StakeholderId
from searce_scout.shared_kernel.value_objects import URL

from searce_scout.stakeholder_discovery.domain.entities.stakeholder import Stakeholder
from searce_scout.stakeholder_discovery.domain.events.stakeholder_events import (
    StakeholderIdentifiedEvent,
)
from searce_scout.stakeholder_discovery.domain.ports.contact_enrichment_port import (
    ContactEnrichmentPort,
)
from searce_scout.stakeholder_discovery.domain.ports.linkedin_port import (
    LinkedInPort,
)
from searce_scout.stakeholder_discovery.domain.services.persona_matching import (
    PersonaMatchingService,
)
from searce_scout.stakeholder_discovery.domain.value_objects.job_title import JobTitle
from searce_scout.stakeholder_discovery.domain.value_objects.relevance_score import (
    RelevanceScore,
)
from searce_scout.stakeholder_discovery.domain.value_objects.validation_status import (
    Department,
    Seniority,
)

# Target titles for LinkedIn decision-maker search
_TARGET_TITLES: tuple[str, ...] = (
    "CTO",
    "CIO",
    "VP Engineering",
    "VP Infrastructure",
    "Head of Data",
    "Head of Innovation",
    "Chief Digital Officer",
    "Director of Engineering",
    "Director of IT",
)

# Simple title-to-seniority / department heuristic
_SENIORITY_KEYWORDS: dict[str, Seniority] = {
    "chief": Seniority.C_SUITE,
    "cto": Seniority.C_SUITE,
    "cio": Seniority.C_SUITE,
    "cdo": Seniority.C_SUITE,
    "vp": Seniority.VP,
    "vice president": Seniority.VP,
    "director": Seniority.DIRECTOR,
    "head": Seniority.HEAD,
    "manager": Seniority.MANAGER,
}

_DEPARTMENT_KEYWORDS: dict[str, Department] = {
    "engineering": Department.ENGINEERING,
    "infrastructure": Department.IT_INFRASTRUCTURE,
    "it": Department.IT_INFRASTRUCTURE,
    "data": Department.DATA,
    "analytics": Department.DATA,
    "innovation": Department.INNOVATION,
    "digital": Department.INNOVATION,
    "hr": Department.HR,
    "human": Department.HR,
    "operations": Department.OPERATIONS,
}


def _infer_seniority(title: str) -> Seniority:
    lower = title.lower()
    for keyword, seniority in _SENIORITY_KEYWORDS.items():
        if keyword in lower:
            return seniority
    return Seniority.IC


def _infer_department(title: str) -> Department:
    lower = title.lower()
    for keyword, department in _DEPARTMENT_KEYWORDS.items():
        if keyword in lower:
            return department
    return Department.ENGINEERING


class StakeholderDiscoveryWorkflow:
    """Orchestrates parallel stakeholder discovery, enrichment, and persona matching.

    DAG structure:
        search_linkedin ── validate_contacts ── score_and_match
    """

    def __init__(
        self,
        linkedin_port: LinkedInPort,
        contact_enrichment: ContactEnrichmentPort,
        persona_matching_service: PersonaMatchingService,
    ) -> None:
        self._linkedin_port = linkedin_port
        self._contact_enrichment = contact_enrichment
        self._persona_matching_service = persona_matching_service

    async def execute(
        self,
        account_id: str,
        company_name: str,
    ) -> list[Stakeholder]:
        context: dict[str, Any] = {
            "account_id": account_id,
            "company_name": company_name,
        }

        # ------------------------------------------------------------------
        # Step functions
        # ------------------------------------------------------------------

        async def search_linkedin(ctx: dict[str, Any], _completed: dict[str, Any]) -> Any:
            profiles = await self._linkedin_port.search_decision_makers(
                company_name=ctx["company_name"],
                titles=_TARGET_TITLES,
            )
            # Convert LinkedIn profiles to initial Stakeholder aggregates
            stakeholders: list[Stakeholder] = []
            for profile in profiles:
                sid = StakeholderId(str(uuid4()))
                aid = AccountId(ctx["account_id"])
                title_raw = profile.title
                seniority = _infer_seniority(title_raw)
                department = _infer_department(title_raw)

                stakeholder = Stakeholder(
                    stakeholder_id=sid,
                    account_id=aid,
                    person_name=profile.name,
                    job_title=JobTitle(raw_title=title_raw, normalized_title=title_raw),
                    seniority=seniority,
                    department=department,
                    contact_info=None,
                    relevance_score=None,
                    persona_match=None,
                    linkedin_url=profile.linkedin_url,
                    domain_events=(
                        StakeholderIdentifiedEvent(
                            aggregate_id=str(sid),
                            person_name=profile.name.full_name,
                            job_title=title_raw,
                            account_id=ctx["account_id"],
                        ),
                    ),
                )
                stakeholders.append(stakeholder)
            return stakeholders

        async def validate_contacts(_ctx: dict[str, Any], completed: dict[str, Any]) -> Any:
            stakeholders: list[Stakeholder] = completed["search_linkedin"]
            if not stakeholders:
                return []

            async def _enrich(s: Stakeholder) -> Stakeholder:
                contact = await self._contact_enrichment.enrich_contact(
                    person_name=s.person_name,
                    company_name=context["company_name"],
                )
                return s.validate_contact(contact)

            enriched = await asyncio.gather(*[_enrich(s) for s in stakeholders])
            return list(enriched)

        async def score_and_match(_ctx: dict[str, Any], completed: dict[str, Any]) -> Any:
            stakeholders: list[Stakeholder] = completed["validate_contacts"]
            scored: list[Stakeholder] = []
            for s in stakeholders:
                match = self._persona_matching_service.match_to_persona(
                    job_title=s.job_title,
                    seniority=s.seniority,
                    department=s.department,
                )
                if match is not None:
                    relevance = RelevanceScore(
                        score=match.confidence,
                        factors=(
                            f"seniority:{s.seniority.value}",
                            f"department:{s.department.value}",
                            f"offering:{match.searce_offering}",
                        ),
                    )
                    s = s.score_relevance(relevance, match)
                scored.append(s)
            return scored

        # ------------------------------------------------------------------
        # Build and run the DAG
        # ------------------------------------------------------------------
        dag = DAGOrchestrator(
            steps=[
                WorkflowStep(
                    name="search_linkedin",
                    execute=search_linkedin,
                    timeout_seconds=30.0,
                ),
                WorkflowStep(
                    name="validate_contacts",
                    execute=validate_contacts,
                    depends_on=("search_linkedin",),
                    timeout_seconds=60.0,
                ),
                WorkflowStep(
                    name="score_and_match",
                    execute=score_and_match,
                    depends_on=("validate_contacts",),
                    timeout_seconds=15.0,
                ),
            ]
        )

        results = await dag.execute(context)
        return results["score_and_match"]
