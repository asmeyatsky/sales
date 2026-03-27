"""
Messaging endpoints.

POST /api/v1/messages/generate            -- Generate a message
POST /api/v1/messages/{message_id}/adjust-tone -- Adjust tone
GET  /api/v1/messages/{message_id}        -- Get message
POST /api/v1/messages/preview             -- Preview without saving
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from searce_scout.messaging.application.commands.adjust_tone import AdjustToneCommand
from searce_scout.messaging.application.commands.generate_message import (
    GenerateMessageCommand,
)
from searce_scout.messaging.application.queries.get_message import GetMessageQuery
from searce_scout.messaging.application.queries.preview_message import (
    PreviewMessageQuery,
)

from searce_scout.presentation.api.schemas.api_schemas import (
    AdjustToneRequest,
    MessagePreviewRequest,
    MessagePreviewResponse,
)

router = APIRouter(prefix="/api/v1/messages", tags=["messaging"])


@router.post("/generate")
async def generate_message(body: dict, request: Request) -> dict:
    """Generate a personalized outreach message.

    Body keys: account_id, stakeholder_id, channel, tone, step_number,
    account_context, stakeholder_context.
    """
    container = request.app.state.container
    cmd = GenerateMessageCommand(
        account_id=body["account_id"],
        stakeholder_id=body["stakeholder_id"],
        channel=body.get("channel", "EMAIL"),
        tone=body.get("tone", "PROFESSIONAL_CONSULTANT"),
        step_number=body.get("step_number", 1),
    )
    account_context = body.get("account_context", {})
    stakeholder_context = body.get("stakeholder_context", {})
    result = await container.generate_message_handler.execute(
        cmd, account_context, stakeholder_context,
    )
    return result.model_dump()


@router.post("/{message_id}/adjust-tone")
async def adjust_tone(
    message_id: str, body: AdjustToneRequest, request: Request
) -> dict:
    """Adjust the tone of an existing message."""
    container = request.app.state.container
    cmd = AdjustToneCommand(message_id=message_id, new_tone=body.new_tone)
    result = await container.adjust_tone_handler.execute(cmd)
    return result.model_dump()


@router.get("/{message_id}")
async def get_message(message_id: str, request: Request) -> dict:
    """Get a message by ID."""
    container = request.app.state.container
    query = GetMessageQuery(message_id=message_id)
    result = await container.get_message_handler.execute(query)
    if result is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return result.model_dump()


@router.post("/preview", response_model=MessagePreviewResponse)
async def preview_message(
    body: MessagePreviewRequest, request: Request
) -> MessagePreviewResponse:
    """Preview a message without saving it."""
    container = request.app.state.container
    query = PreviewMessageQuery(
        account_id=body.account_id,
        stakeholder_id=body.stakeholder_id,
        channel=body.channel,
        tone=body.tone,
    )
    # Preview requires cross-BC context; use empty defaults for the API
    account_context: dict = {
        "company_name": "",
        "industry": "",
        "tech_stack_summary": "",
        "buying_signals": [],
        "pain_points": [],
        "searce_offering": "",
    }
    stakeholder_context: dict = {
        "stakeholder_name": "",
        "job_title": "",
    }
    result = await container.preview_message_handler.execute(
        query, account_context, stakeholder_context,
    )
    return MessagePreviewResponse(
        message_id=result.message_id,
        channel=result.channel,
        tone=result.tone,
        subject=result.subject,
        body=result.body,
        call_to_action=result.call_to_action,
        quality_score=result.quality_score,
    )
