"""
CRM sync endpoints.

POST /api/v1/crm/push                          -- Push to CRM
POST /api/v1/crm/pull                          -- Pull from CRM
POST /api/v1/crm/conflicts/{record_id}/resolve -- Resolve conflict
GET  /api/v1/crm/conflicts                     -- List conflicts
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from searce_scout.crm_sync.application.commands.pull_from_crm import PullFromCRMCommand
from searce_scout.crm_sync.application.commands.push_to_crm import PushToCRMCommand
from searce_scout.crm_sync.application.commands.resolve_conflict import (
    ResolveConflictCommand,
)
from searce_scout.crm_sync.application.queries.list_conflicts import ListConflictsQuery

from searce_scout.presentation.api.schemas.api_schemas import (
    CRMPullRequest,
    CRMPushRequest,
    CRMResolveConflictRequest,
)

router = APIRouter(prefix="/api/v1/crm", tags=["crm"])


@router.post("/push")
async def push_to_crm(body: CRMPushRequest, request: Request) -> dict:
    """Push a local record to the external CRM."""
    container = request.app.state.container
    cmd = PushToCRMCommand(
        local_id=body.local_id,
        record_type=body.record_type,
        provider=body.provider,
        fields=body.fields,
    )
    result = await container.push_to_crm_handler.execute(cmd)
    return result.model_dump()


@router.post("/pull")
async def pull_from_crm(body: CRMPullRequest, request: Request) -> list[dict]:
    """Pull changes from the external CRM since a given timestamp."""
    container = request.app.state.container
    cmd = PullFromCRMCommand(
        provider=body.provider,
        record_type=body.record_type,
        since=body.since,
    )
    results = await container.pull_from_crm_handler.execute(cmd)
    return [r.model_dump() for r in results]


@router.post("/conflicts/{record_id}/resolve")
async def resolve_conflict(
    record_id: str, body: CRMResolveConflictRequest, request: Request
) -> dict:
    """Resolve a sync conflict for a CRM record."""
    container = request.app.state.container
    cmd = ResolveConflictCommand(record_id=record_id, strategy=body.strategy)
    result = await container.resolve_conflict_handler.execute(cmd)
    return result.model_dump()


@router.get("/conflicts")
async def list_conflicts(request: Request) -> list[dict]:
    """List all CRM records with CONFLICT status."""
    container = request.app.state.container
    query = ListConflictsQuery()
    results = await container.list_conflicts_handler.execute(query)
    return [r.model_dump() for r in results]
