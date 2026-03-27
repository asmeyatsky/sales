"""Pure domain tests for DeckCompositionService.

No mocks — verifies the canonical slide ordering, case-study capping,
and graceful handling of empty case studies.
"""

from searce_scout.presentation_gen.domain.services.deck_composition import (
    DeckCompositionService,
)
from searce_scout.presentation_gen.domain.value_objects.deck_content import (
    CaseStudyReference,
    GapAnalysis,
    HookContent,
)
from searce_scout.presentation_gen.domain.value_objects.slide import SlideType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hook() -> HookContent:
    return HookContent(
        headline="Cloud costs rising 40% YoY",
        key_insight="Most enterprises overspend on AWS.",
        supporting_data="Gartner 2025 Cloud Spend Report",
    )


def _gap() -> GapAnalysis:
    return GapAnalysis(
        current_state="Legacy on-prem data centers with rising OpEx.",
        future_state="Fully managed GCP infrastructure with 30% lower TCO.",
        cost_of_inaction="$5M/year in wasted infrastructure spend.",
    )


def _case_studies(n: int = 2) -> tuple[CaseStudyReference, ...]:
    return tuple(
        CaseStudyReference(
            title=f"Case Study {i + 1}",
            industry=f"Industry {i + 1}",
            outcome_summary=f"Outcome {i + 1}",
            metric=f"Metric {i + 1}",
        )
        for i in range(n)
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCompose:
    def test_compose_creates_correct_slide_order(self) -> None:
        service = DeckCompositionService()
        slides = service.compose(
            hook=_hook(),
            gap=_gap(),
            case_studies=_case_studies(2),
            offering="Cloud Migration",
            company_name="Acme Corp",
        )

        expected_types = [
            SlideType.TITLE,
            SlideType.HOOK,
            SlideType.GAP_CURRENT_STATE,
            SlideType.GAP_FUTURE_STATE,
            SlideType.SOCIAL_PROOF,   # case study 1
            SlideType.SOCIAL_PROOF,   # case study 2
            SlideType.SEARCE_OFFERING,
            SlideType.CALL_TO_ACTION,
        ]
        actual_types = [s.slide_type for s in slides]
        assert actual_types == expected_types

        # Verify ordering indices are sequential
        orders = [s.order for s in slides]
        assert orders == list(range(len(slides)))

    def test_compose_limits_case_studies_to_three(self) -> None:
        service = DeckCompositionService()
        slides = service.compose(
            hook=_hook(),
            gap=_gap(),
            case_studies=_case_studies(5),  # 5 provided, only 3 should appear
            offering="Data & Analytics",
            company_name="BigCo",
        )

        social_proof_slides = [
            s for s in slides if s.slide_type is SlideType.SOCIAL_PROOF
        ]
        assert len(social_proof_slides) == 3

    def test_compose_with_no_case_studies_skips_social_proof(self) -> None:
        service = DeckCompositionService()
        slides = service.compose(
            hook=_hook(),
            gap=_gap(),
            case_studies=(),
            offering="Applied AI",
            company_name="TinyCo",
        )

        social_proof_slides = [
            s for s in slides if s.slide_type is SlideType.SOCIAL_PROOF
        ]
        assert len(social_proof_slides) == 0

        # Should still have the 6 non-social-proof slides
        expected_types = [
            SlideType.TITLE,
            SlideType.HOOK,
            SlideType.GAP_CURRENT_STATE,
            SlideType.GAP_FUTURE_STATE,
            SlideType.SEARCE_OFFERING,
            SlideType.CALL_TO_ACTION,
        ]
        actual_types = [s.slide_type for s in slides]
        assert actual_types == expected_types
