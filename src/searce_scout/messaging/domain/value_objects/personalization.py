"""Personalization context value objects for message generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CaseStudyRef:
    """Reference to a relevant Searce case study."""

    title: str
    industry: str
    outcome_summary: str
    metric: str


@dataclass(frozen=True)
class PersonalizationContext:
    """All personalization data needed to generate a tailored message."""

    company_name: str
    stakeholder_name: str
    job_title: str
    buying_signals: tuple[str, ...]
    tech_stack_summary: str
    pain_points: tuple[str, ...]
    relevant_case_studies: tuple[CaseStudyRef, ...]
    searce_offering: str
