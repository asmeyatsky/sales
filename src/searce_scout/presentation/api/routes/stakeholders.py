"""
Stakeholder endpoints.

POST /api/v1/stakeholders/discover                   -- Discover stakeholders
GET  /api/v1/stakeholders/{account_id}               -- List stakeholders
POST /api/v1/stakeholders/{stakeholder_id}/validate   -- Validate contact
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from searce_scout.stakeholder_discovery.application.commands.discover_stakeholders import (
    DiscoverStakeholdersCommand,
)
from searce_scout.stakeholder_discovery.application.commands.validate_contact import (
    ValidateContactCommand,
)
from searce_scout.stakeholder_discovery.application.queries.get_stakeholders_for_account import (
    GetStakeholdersForAccountQuery,
)

from searce_scout.presentation.api.schemas.api_schemas import (
    DiscoverStakeholdersRequest,
    PaginatedResponse,
)

router = APIRouter(prefix="/api/v1/stakeholders", tags=["stakeholders"])


@router.post("/discover")
async def discover_stakeholders(
    body: DiscoverStakeholdersRequest, request: Request
) -> list[dict]:
    """Discover stakeholders for an account."""
    container = request.app.state.container
    cmd = DiscoverStakeholdersCommand(
        account_id=body.account_id,
        company_name=body.company_name,
    )
    results = await container.discover_stakeholders_handler.execute(cmd)
    return [r.model_dump() for r in results]


@router.get("/{account_id}")
async def list_stakeholders(
    account_id: str, request: Request, offset: int = 0, limit: int = 50
) -> PaginatedResponse[dict]:
    """List stakeholders for an account."""
    container = request.app.state.container
    query = GetStakeholdersForAccountQuery(account_id=account_id)
    results = await container.get_stakeholders_for_account_handler.execute(query)
    all_items = [r.model_dump() for r in results]
    total = len(all_items)
    return PaginatedResponse(
        items=all_items[offset : offset + limit],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/{stakeholder_id}/validate")
async def validate_contact(stakeholder_id: str, request: Request) -> dict:
    """Validate a stakeholder's contact information."""
    container = request.app.state.container
    cmd = ValidateContactCommand(stakeholder_id=stakeholder_id)
    result = await container.validate_contact_handler.execute(cmd)
    return result.model_dump()
