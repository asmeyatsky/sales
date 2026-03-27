"""Case study repository adapter — implements CaseStudyPort.

Loads Searce case studies from a local JSON file and provides
case-insensitive lookup by industry and offering.
"""

from __future__ import annotations

import json
from pathlib import Path

from searce_scout.messaging.domain.ports.case_study_port import CaseStudyPort
from searce_scout.messaging.domain.value_objects.personalization import CaseStudyRef

_DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parents[4]  # src/searce_scout
    / "data"
    / "case_studies"
    / "searce_case_studies.json"
)


class CaseStudyRepository:
    """File-backed case study repository.

    Implements :class:`CaseStudyPort`.

    Reads ``data/case_studies/searce_case_studies.json`` on first access and
    caches the parsed entries for subsequent look-ups.

    Expected JSON structure::

        [
            {
                "title": "...",
                "industry": "...",
                "outcome_summary": "...",
                "metric": "...",
                "offerings": ["Data Engineering", "Cloud Migration", ...]
            },
            ...
        ]
    """

    def __init__(self, *, data_path: Path | None = None) -> None:
        self._data_path = data_path or _DEFAULT_DATA_PATH
        self._entries: list[dict[str, object]] | None = None

    # ------------------------------------------------------------------
    # CaseStudyPort implementation
    # ------------------------------------------------------------------

    async def find_by_industry(self, industry: str) -> tuple[CaseStudyRef, ...]:
        """Return case studies whose industry matches (case-insensitive)."""
        entries = self._load()
        industry_lower = industry.lower()
        results: list[CaseStudyRef] = []
        for entry in entries:
            entry_industry = str(entry.get("industry", ""))
            if entry_industry.lower() == industry_lower:
                results.append(self._to_ref(entry))
        return tuple(results)

    async def find_by_offering(self, offering: str) -> tuple[CaseStudyRef, ...]:
        """Return case studies that reference the given offering (case-insensitive)."""
        entries = self._load()
        offering_lower = offering.lower()
        results: list[CaseStudyRef] = []
        for entry in entries:
            offerings = entry.get("offerings", [])
            if not isinstance(offerings, list):
                offerings = []
            if any(str(o).lower() == offering_lower for o in offerings):
                results.append(self._to_ref(entry))
        return tuple(results)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> list[dict[str, object]]:
        """Load and cache the JSON data from disk."""
        if self._entries is not None:
            return self._entries

        if not self._data_path.exists():
            self._entries = []
            return self._entries

        with open(self._data_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)

        if not isinstance(raw, list):
            self._entries = []
            return self._entries

        self._entries = raw
        return self._entries

    @staticmethod
    def _to_ref(entry: dict[str, object]) -> CaseStudyRef:
        """Map a raw JSON dict to a CaseStudyRef value object."""
        return CaseStudyRef(
            title=str(entry.get("title", "")),
            industry=str(entry.get("industry", "")),
            outcome_summary=str(entry.get("outcome_summary", "")),
            metric=str(entry.get("metric", "")),
        )


# Structural compatibility assertion
def _check_port_compliance() -> None:
    _: CaseStudyPort = CaseStudyRepository()  # type: ignore[assignment]
