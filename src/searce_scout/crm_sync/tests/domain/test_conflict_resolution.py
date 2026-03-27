"""Pure domain tests for ConflictResolutionService.

No mocks — exercises all four resolution strategies with concrete
local and remote field sets.
"""

from searce_scout.crm_sync.domain.services.conflict_resolution import (
    ConflictResolutionService,
    ResolutionStrategy,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

LOCAL_FIELDS: tuple[tuple[str, str], ...] = (
    ("industry", "Tech"),
    ("name", "Acme"),
    ("website", "https://acme.com"),
)

REMOTE_FIELDS: dict[str, str] = {
    "name": "Acme Inc",
    "industry": "Technology",
    "revenue": "10M",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestConflictResolution:
    def test_local_priority_keeps_local_values(self) -> None:
        svc = ConflictResolutionService()
        result = svc.resolve(LOCAL_FIELDS, REMOTE_FIELDS, ResolutionStrategy.LOCAL_PRIORITY)
        result_dict = dict(result)

        # Local values win for overlapping keys
        assert result_dict["name"] == "Acme"
        assert result_dict["industry"] == "Tech"
        assert result_dict["website"] == "https://acme.com"

        # Remote-only keys are added
        assert result_dict["revenue"] == "10M"

    def test_remote_priority_uses_remote_values(self) -> None:
        svc = ConflictResolutionService()
        result = svc.resolve(LOCAL_FIELDS, REMOTE_FIELDS, ResolutionStrategy.REMOTE_PRIORITY)
        result_dict = dict(result)

        # Remote values win for overlapping keys
        assert result_dict["name"] == "Acme Inc"
        assert result_dict["industry"] == "Technology"

        # Local-only keys preserved
        assert result_dict["website"] == "https://acme.com"

        # Remote-only keys added
        assert result_dict["revenue"] == "10M"

    def test_last_write_wins_uses_remote(self) -> None:
        svc = ConflictResolutionService()
        result = svc.resolve(LOCAL_FIELDS, REMOTE_FIELDS, ResolutionStrategy.LAST_WRITE_WINS)
        result_dict = dict(result)

        # Behaves same as REMOTE_PRIORITY
        assert result_dict["name"] == "Acme Inc"
        assert result_dict["industry"] == "Technology"
        assert result_dict["website"] == "https://acme.com"
        assert result_dict["revenue"] == "10M"

    def test_manual_flag_returns_local_unchanged(self) -> None:
        svc = ConflictResolutionService()
        result = svc.resolve(LOCAL_FIELDS, REMOTE_FIELDS, ResolutionStrategy.MANUAL_FLAG)

        # Exactly the original local fields, unchanged
        assert result == LOCAL_FIELDS
