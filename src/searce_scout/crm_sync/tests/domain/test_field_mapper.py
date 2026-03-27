"""Pure domain tests for FieldMapperService.

No mocks — verifies bidirectional field translation between local and
CRM schemas using FieldMapping definitions.
"""

from searce_scout.crm_sync.domain.entities.field_mapping import FieldMapping
from searce_scout.crm_sync.domain.services.field_mapper import FieldMapperService
from searce_scout.crm_sync.domain.value_objects.crm_provider import CRMProvider
from searce_scout.crm_sync.domain.value_objects.record_type import RecordType
from searce_scout.crm_sync.domain.value_objects.sync_direction import SyncDirection


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

MAPPINGS: tuple[FieldMapping, ...] = (
    FieldMapping(
        mapping_id="m1",
        provider=CRMProvider.SALESFORCE,
        record_type=RecordType.ACCOUNT,
        local_field="name",
        crm_field="Name",
        direction=SyncDirection.PUSH,
    ),
    FieldMapping(
        mapping_id="m2",
        provider=CRMProvider.SALESFORCE,
        record_type=RecordType.ACCOUNT,
        local_field="industry",
        crm_field="Industry",
        direction=SyncDirection.PULL,
    ),
    FieldMapping(
        mapping_id="m3",
        provider=CRMProvider.SALESFORCE,
        record_type=RecordType.ACCOUNT,
        local_field="website",
        crm_field="Website",
        direction=SyncDirection.BIDIRECTIONAL,
    ),
)

LOCAL_FIELDS: tuple[tuple[str, str], ...] = (
    ("name", "Acme"),
    ("industry", "Tech"),
    ("website", "https://acme.com"),
)

CRM_DATA: dict[str, str] = {
    "Name": "Acme Corp",
    "Industry": "Technology",
    "Website": "https://acme.io",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMapToCrm:
    def test_map_to_crm_respects_push_direction(self) -> None:
        svc = FieldMapperService()
        result = svc.map_to_crm(LOCAL_FIELDS, MAPPINGS)

        # PUSH mapping: name -> Name
        assert result["Name"] == "Acme"

        # BIDIRECTIONAL mapping: website -> Website
        assert result["Website"] == "https://acme.com"

        # PULL-only mapping should NOT appear in to-CRM output
        assert "Industry" not in result


class TestMapFromCrm:
    def test_map_from_crm_respects_pull_direction(self) -> None:
        svc = FieldMapperService()
        result = svc.map_from_crm(CRM_DATA, MAPPINGS)
        result_dict = dict(result)

        # PULL mapping: Industry -> industry
        assert result_dict["industry"] == "Technology"

        # BIDIRECTIONAL mapping: Website -> website
        assert result_dict["website"] == "https://acme.io"

        # PUSH-only mapping should NOT appear in from-CRM output
        assert "name" not in result_dict


class TestBidirectional:
    def test_bidirectional_maps_both_ways(self) -> None:
        svc = FieldMapperService()

        # To CRM
        to_crm = svc.map_to_crm(LOCAL_FIELDS, MAPPINGS)
        assert "Website" in to_crm
        assert to_crm["Website"] == "https://acme.com"

        # From CRM
        from_crm = svc.map_from_crm(CRM_DATA, MAPPINGS)
        from_crm_dict = dict(from_crm)
        assert "website" in from_crm_dict
        assert from_crm_dict["website"] == "https://acme.io"
