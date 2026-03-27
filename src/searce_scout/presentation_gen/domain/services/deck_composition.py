"""
DeckCompositionService — pure domain service.

Composes an ordered tuple of Slides from structured content blocks.
No side effects, no I/O, no framework dependencies.
"""

from __future__ import annotations

from searce_scout.presentation_gen.domain.value_objects.deck_content import (
    CaseStudyReference,
    GapAnalysis,
    HookContent,
)
from searce_scout.presentation_gen.domain.value_objects.slide import Slide, SlideType

_MAX_CASE_STUDIES = 3


class DeckCompositionService:
    """Assembles a canonical slide sequence from content building blocks."""

    def compose(
        self,
        hook: HookContent,
        gap: GapAnalysis,
        case_studies: tuple[CaseStudyReference, ...],
        offering: str,
        company_name: str,
    ) -> tuple[Slide, ...]:
        """Return an ordered tuple of slides for a complete sales deck.

        Slide order:
        TITLE -> HOOK -> GAP_CURRENT_STATE -> GAP_FUTURE_STATE ->
        SOCIAL_PROOF (one per case study, max 3) -> SEARCE_OFFERING ->
        CALL_TO_ACTION
        """
        slides: list[Slide] = []
        order = 0

        # --- TITLE ---
        slides.append(
            Slide(
                slide_type=SlideType.TITLE,
                title=f"Partnering with {company_name}",
                body=f"How Searce can accelerate {company_name}'s transformation",
                speaker_notes=(
                    f"Open with a warm greeting. Mention {company_name} by name "
                    "and set the context for the presentation."
                ),
                order=order,
            )
        )
        order += 1

        # --- HOOK ---
        slides.append(
            Slide(
                slide_type=SlideType.HOOK,
                title=hook.headline,
                body=f"{hook.key_insight}\n\n{hook.supporting_data}",
                speaker_notes=(
                    "Lead with the key insight to capture attention. "
                    "Use the supporting data to build credibility."
                ),
                order=order,
            )
        )
        order += 1

        # --- GAP_CURRENT_STATE ---
        slides.append(
            Slide(
                slide_type=SlideType.GAP_CURRENT_STATE,
                title="Where You Are Today",
                body=gap.current_state,
                speaker_notes=(
                    "Acknowledge their current state objectively. "
                    "Show that you understand their environment."
                ),
                order=order,
            )
        )
        order += 1

        # --- GAP_FUTURE_STATE ---
        slides.append(
            Slide(
                slide_type=SlideType.GAP_FUTURE_STATE,
                title="Where You Could Be",
                body=f"{gap.future_state}\n\nCost of inaction: {gap.cost_of_inaction}",
                speaker_notes=(
                    "Paint the future-state vision. Emphasise the cost of inaction "
                    "to create urgency without being pushy."
                ),
                order=order,
            )
        )
        order += 1

        # --- SOCIAL_PROOF (one per case study, max 3) ---
        for cs in case_studies[:_MAX_CASE_STUDIES]:
            slides.append(
                Slide(
                    slide_type=SlideType.SOCIAL_PROOF,
                    title=cs.title,
                    body=(
                        f"Industry: {cs.industry}\n"
                        f"Outcome: {cs.outcome_summary}\n"
                        f"Key metric: {cs.metric}"
                    ),
                    speaker_notes=(
                        f"Walk through the {cs.industry} case study. "
                        f"Highlight the measurable outcome: {cs.metric}."
                    ),
                    order=order,
                )
            )
            order += 1

        # --- SEARCE_OFFERING ---
        slides.append(
            Slide(
                slide_type=SlideType.SEARCE_OFFERING,
                title="Our Offering",
                body=offering,
                speaker_notes=(
                    "Connect Searce's offering back to the gap analysis. "
                    "Keep it concise and outcome-focused."
                ),
                order=order,
            )
        )
        order += 1

        # --- CALL_TO_ACTION ---
        slides.append(
            Slide(
                slide_type=SlideType.CALL_TO_ACTION,
                title="Next Steps",
                body=(
                    f"Let's explore how Searce can help {company_name} "
                    "achieve these outcomes. We propose a focused discovery "
                    "workshop as the next step."
                ),
                speaker_notes=(
                    "Close with a clear, low-commitment ask. Suggest a "
                    "discovery workshop and confirm next steps."
                ),
                order=order,
            )
        )

        return tuple(slides)
