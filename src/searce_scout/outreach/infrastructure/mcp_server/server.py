"""Outreach MCP Server.

Exposes outreach sequence lifecycle operations as MCP tools (writes),
and sequence status queries as MCP resources (reads).  Follows skill2026
Rule 6: tools for writes, resources for reads.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

if TYPE_CHECKING:
    from searce_scout.outreach.application.commands.execute_next_step import (
        ExecuteNextStepHandler,
    )
    from searce_scout.outreach.application.commands.process_reply import (
        ProcessReplyHandler,
    )
    from searce_scout.outreach.application.commands.start_sequence import (
        StartSequenceHandler,
    )
    from searce_scout.outreach.application.commands.stop_sequence import (
        StopSequenceHandler,
    )
    from searce_scout.outreach.application.queries.get_sequence_status import (
        GetSequenceStatusHandler,
    )
    from searce_scout.outreach.application.queries.list_active_sequences import (
        ListActiveSequencesHandler,
    )


def create_server(
    start_handler: StartSequenceHandler,
    execute_next_handler: ExecuteNextStepHandler,
    process_reply_handler: ProcessReplyHandler,
    stop_handler: StopSequenceHandler,
    sequence_status_query: GetSequenceStatusHandler,
    active_sequences_query: ListActiveSequencesHandler,
) -> Server:
    """Factory that wires application-layer handlers into an MCP server.

    Args:
        start_handler: Handler for the ``start_sequence`` tool.
        execute_next_handler: Handler for the ``execute_next_step`` tool.
        process_reply_handler: Handler for the ``process_reply`` tool.
        stop_handler: Handler for the ``stop_sequence`` tool.
        sequence_status_query: Handler for the ``outreach://sequence/{id}`` resource.
        active_sequences_query: Handler for the ``outreach://active-sequences`` resource.

    Returns:
        A fully-configured :class:`mcp.server.Server` instance.
    """

    server = Server("outreach")

    # ------------------------------------------------------------------
    # Tools (writes)
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="start_sequence",
                description=(
                    "Build and start a multi-step outreach sequence for a "
                    "stakeholder, mapping step types to pre-generated message IDs."
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
                        "message_ids": {
                            "type": "object",
                            "description": (
                                "Mapping from step type names (e.g. email_1, "
                                "linkedin_request) to pre-generated message IDs."
                            ),
                            "additionalProperties": {"type": "string"},
                        },
                    },
                    "required": ["account_id", "stakeholder_id", "message_ids"],
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="execute_next_step",
                description=(
                    "Execute the current step of an outreach sequence by "
                    "dispatching to the appropriate channel (email, LinkedIn, phone)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sequence_id": {
                            "type": "string",
                            "description": "The identifier of the sequence to advance.",
                        },
                    },
                    "required": ["sequence_id"],
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="process_reply",
                description=(
                    "Classify an incoming reply using AI and apply the "
                    "appropriate action (stop, pause, continue) to the sequence."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sequence_id": {
                            "type": "string",
                            "description": "The identifier of the sequence that received a reply.",
                        },
                        "raw_content": {
                            "type": "string",
                            "description": "The raw text content of the reply.",
                        },
                    },
                    "required": ["sequence_id", "raw_content"],
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="stop_sequence",
                description=(
                    "Manually stop an outreach sequence with a given reason."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sequence_id": {
                            "type": "string",
                            "description": "The identifier of the sequence to stop.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "The reason for stopping the sequence.",
                        },
                    },
                    "required": ["sequence_id", "reason"],
                    "additionalProperties": False,
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        from searce_scout.outreach.application.commands.execute_next_step import (
            ExecuteNextStepCommand,
        )
        from searce_scout.outreach.application.commands.process_reply import (
            ProcessReplyCommand,
        )
        from searce_scout.outreach.application.commands.start_sequence import (
            StartSequenceCommand,
        )
        from searce_scout.outreach.application.commands.stop_sequence import (
            StopSequenceCommand,
        )

        if name == "start_sequence":
            cmd = StartSequenceCommand(
                account_id=arguments["account_id"],
                stakeholder_id=arguments["stakeholder_id"],
                message_ids=arguments["message_ids"],
            )
            result = await start_handler.execute(cmd)
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "execute_next_step":
            cmd = ExecuteNextStepCommand(
                sequence_id=arguments["sequence_id"],
            )
            result = await execute_next_handler.execute(cmd)
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "process_reply":
            cmd = ProcessReplyCommand(
                sequence_id=arguments["sequence_id"],
                raw_content=arguments["raw_content"],
            )
            result = await process_reply_handler.execute(cmd)
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "stop_sequence":
            cmd = StopSequenceCommand(
                sequence_id=arguments["sequence_id"],
                reason=arguments["reason"],
            )
            result = await stop_handler.execute(cmd)
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        raise ValueError(f"Unknown tool: {name}")

    # ------------------------------------------------------------------
    # Resources (reads)
    # ------------------------------------------------------------------

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="outreach://sequence/{sequence_id}",
                name="Sequence Status",
                description="Returns the full OutreachSequenceDTO for a single sequence.",
                mimeType="application/json",
            ),
            Resource(
                uri="outreach://active-sequences",
                name="Active Sequences",
                description="Returns all outreach sequences currently in ACTIVE status.",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        from searce_scout.outreach.application.queries.get_sequence_status import (
            GetSequenceStatusQuery,
        )
        from searce_scout.outreach.application.queries.list_active_sequences import (
            ListActiveSequencesQuery,
        )

        uri_str = str(uri)

        if uri_str == "outreach://active-sequences":
            query = ListActiveSequencesQuery()
            results = await active_sequences_query.execute(query)
            return json.dumps(
                [r.model_dump(mode="json") for r in results], indent=2
            )

        if uri_str.startswith("outreach://sequence/"):
            sequence_id = uri_str.removeprefix("outreach://sequence/")
            query = GetSequenceStatusQuery(sequence_id=sequence_id)
            result = await sequence_status_query.execute(query)
            if result is None:
                return json.dumps({"error": f"Sequence not found: {sequence_id}"})
            return result.model_dump_json(indent=2)

        raise ValueError(f"Unknown resource URI: {uri_str}")

    return server
