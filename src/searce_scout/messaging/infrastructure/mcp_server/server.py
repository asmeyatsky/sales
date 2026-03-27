"""Messaging MCP Server.

Exposes message generation and tone adjustment as MCP tools (writes),
and message detail / preview as MCP resources (reads).  Follows skill2026
Rule 6: tools for writes, resources for reads.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

if TYPE_CHECKING:
    from searce_scout.messaging.application.commands.adjust_tone import (
        AdjustToneHandler,
    )
    from searce_scout.messaging.application.commands.generate_message import (
        GenerateMessageHandler,
    )
    from searce_scout.messaging.application.queries.get_message import (
        GetMessageHandler,
    )
    from searce_scout.messaging.application.queries.preview_message import (
        PreviewMessageHandler,
    )


def create_server(
    generate_handler: GenerateMessageHandler,
    adjust_tone_handler: AdjustToneHandler,
    message_query: GetMessageHandler,
    preview_query: PreviewMessageHandler,
) -> Server:
    """Factory that wires application-layer handlers into an MCP server.

    Args:
        generate_handler: Handler for the ``generate_message`` tool.
        adjust_tone_handler: Handler for the ``adjust_tone`` tool.
        message_query: Handler for the ``message://detail/{message_id}`` resource.
        preview_query: Handler for the ``message://preview/...`` resource.

    Returns:
        A fully-configured :class:`mcp.server.Server` instance.
    """

    server = Server("messaging")

    # ------------------------------------------------------------------
    # Tools (writes)
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="generate_message",
                description=(
                    "Generate a personalised outreach message for a stakeholder "
                    "on a given channel and tone, enriched with account context."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {
                            "type": "string",
                            "description": "Target account identifier.",
                        },
                        "stakeholder_id": {
                            "type": "string",
                            "description": "Target stakeholder identifier.",
                        },
                        "channel": {
                            "type": "string",
                            "description": "Delivery channel (e.g. email, linkedin).",
                        },
                        "tone": {
                            "type": "string",
                            "description": "Message tone (e.g. professional, casual, bold).",
                        },
                        "step_number": {
                            "type": "integer",
                            "description": "Sequence step number for this message.",
                        },
                        "account_context": {
                            "type": "object",
                            "description": (
                                "Cross-BC account data. Expected keys: company_name, "
                                "industry, tech_stack_summary, buying_signals, "
                                "pain_points, searce_offering."
                            ),
                        },
                        "stakeholder_context": {
                            "type": "object",
                            "description": (
                                "Cross-BC stakeholder data. Expected keys: "
                                "stakeholder_name, job_title."
                            ),
                        },
                    },
                    "required": [
                        "account_id",
                        "stakeholder_id",
                        "channel",
                        "tone",
                        "step_number",
                        "account_context",
                        "stakeholder_context",
                    ],
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="adjust_tone",
                description=(
                    "Regenerate an existing message with a different tone "
                    "while preserving the personalisation context."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "The identifier of the message to adjust.",
                        },
                        "new_tone": {
                            "type": "string",
                            "description": "The desired new tone (e.g. professional, casual, bold).",
                        },
                    },
                    "required": ["message_id", "new_tone"],
                    "additionalProperties": False,
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        from searce_scout.messaging.application.commands.adjust_tone import (
            AdjustToneCommand,
        )
        from searce_scout.messaging.application.commands.generate_message import (
            GenerateMessageCommand,
        )

        if name == "generate_message":
            cmd = GenerateMessageCommand(
                account_id=arguments["account_id"],
                stakeholder_id=arguments["stakeholder_id"],
                channel=arguments["channel"],
                tone=arguments["tone"],
                step_number=arguments["step_number"],
            )
            result = await generate_handler.execute(
                cmd,
                account_context=arguments.get("account_context", {}),
                stakeholder_context=arguments.get("stakeholder_context", {}),
            )
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "adjust_tone":
            cmd = AdjustToneCommand(
                message_id=arguments["message_id"],
                new_tone=arguments["new_tone"],
            )
            result = await adjust_tone_handler.execute(cmd)
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        raise ValueError(f"Unknown tool: {name}")

    # ------------------------------------------------------------------
    # Resources (reads)
    # ------------------------------------------------------------------

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="message://detail/{message_id}",
                name="Message Detail",
                description="Returns the full MessageDTO for a single message.",
                mimeType="application/json",
            ),
            Resource(
                uri="message://preview/{account_id}/{stakeholder_id}/{channel}/{tone}",
                name="Message Preview",
                description=(
                    "Generates a message preview without saving it. "
                    "Useful for testing tone and channel combinations."
                ),
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        from searce_scout.messaging.application.queries.get_message import (
            GetMessageQuery,
        )
        from searce_scout.messaging.application.queries.preview_message import (
            PreviewMessageQuery,
        )

        uri_str = str(uri)

        if uri_str.startswith("message://detail/"):
            message_id = uri_str.removeprefix("message://detail/")
            query = GetMessageQuery(message_id=message_id)
            result = await message_query.execute(query)
            if result is None:
                return json.dumps({"error": f"Message not found: {message_id}"})
            return result.model_dump_json(indent=2)

        if uri_str.startswith("message://preview/"):
            # URI format: message://preview/{account_id}/{stakeholder_id}/{channel}/{tone}
            parts = uri_str.removeprefix("message://preview/").split("/")
            if len(parts) != 4:
                raise ValueError(
                    f"Invalid preview URI format. Expected "
                    f"message://preview/{{account_id}}/{{stakeholder_id}}/{{channel}}/{{tone}}, "
                    f"got: {uri_str}"
                )
            account_id, stakeholder_id, channel, tone = parts
            query = PreviewMessageQuery(
                account_id=account_id,
                stakeholder_id=stakeholder_id,
                channel=channel,
                tone=tone,
            )
            # Preview uses empty cross-BC contexts; the orchestrator layer
            # should supply real data when invoking via the full workflow.
            result = await preview_query.execute(
                query,
                account_context={},
                stakeholder_context={},
            )
            return result.model_dump_json(indent=2)

        raise ValueError(f"Unknown resource URI: {uri_str}")

    return server
