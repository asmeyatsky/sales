"""
Outreach endpoints.

POST /api/v1/sequences                           -- Start a sequence
POST /api/v1/sequences/{sequence_id}/execute-step -- Execute next step
POST /api/v1/sequences/{sequence_id}/stop         -- Stop sequence
GET  /api/v1/sequences/{sequence_id}              -- Get sequence status
GET  /api/v1/sequences/active                     -- List active sequences
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from searce_scout.outreach.application.commands.execute_next_step import (
    ExecuteNextStepCommand,
)
from searce_scout.outreach.application.commands.start_sequence import (
    StartSequenceCommand,
)
from searce_scout.outreach.application.commands.stop_sequence import (
    StopSequenceCommand,
)
from searce_scout.outreach.application.queries.get_sequence_status import (
    GetSequenceStatusQuery,
)
from searce_scout.outreach.application.queries.list_active_sequences import (
    ListActiveSequencesQuery,
)

from searce_scout.presentation.api.schemas.api_schemas import OutreachRequest, PaginatedResponse

router = APIRouter(prefix="/api/v1/sequences", tags=["outreach"])


@router.post("")
async def start_sequence(body: dict, request: Request) -> dict:
    """Start a new outreach sequence.

    Body keys: account_id, stakeholder_id, message_ids (dict[step_type, message_id]).
    """
    container = request.app.state.container
    cmd = StartSequenceCommand(
        account_id=body["account_id"],
        stakeholder_id=body["stakeholder_id"],
        message_ids=body.get("message_ids", {}),
    )
    result = await container.start_sequence_handler.execute(cmd)
    return result.model_dump()


@router.post("/{sequence_id}/execute-step")
async def execute_next_step(sequence_id: str, request: Request) -> dict:
    """Execute the next step of an outreach sequence."""
    container = request.app.state.container
    cmd = ExecuteNextStepCommand(sequence_id=sequence_id)
    result = await container.execute_next_step_handler.execute(cmd)
    return result.model_dump()


@router.post("/{sequence_id}/stop")
async def stop_sequence(sequence_id: str, body: dict, request: Request) -> dict:
    """Stop an outreach sequence."""
    container = request.app.state.container
    reason = body.get("reason", "Manually stopped via API")
    cmd = StopSequenceCommand(sequence_id=sequence_id, reason=reason)
    result = await container.stop_sequence_handler.execute(cmd)
    return result.model_dump()


@router.get("/active")
async def list_active_sequences(
    request: Request, offset: int = 0, limit: int = 50
) -> PaginatedResponse[dict]:
    """List all active outreach sequences."""
    container = request.app.state.container
    query = ListActiveSequencesQuery()
    results = await container.list_active_sequences_handler.execute(query)
    all_items = [r.model_dump() for r in results]
    total = len(all_items)
    return PaginatedResponse(
        items=all_items[offset : offset + limit],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{sequence_id}")
async def get_sequence_status(sequence_id: str, request: Request) -> dict:
    """Get the current status of an outreach sequence."""
    container = request.app.state.container
    query = GetSequenceStatusQuery(sequence_id=sequence_id)
    result = await container.get_sequence_status_handler.execute(query)
    if result is None:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return result.model_dump()
