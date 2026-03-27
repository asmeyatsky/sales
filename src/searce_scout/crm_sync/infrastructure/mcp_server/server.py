"""CRM Sync MCP Server.

Exposes CRM push, pull, and conflict resolution as MCP tools (writes),
and sync status / conflict listing as MCP resources (reads).  Follows
skill2026 Rule 6: tools for writes, resources for reads.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

if TYPE_CHECKING:
    from searce_scout.crm_sync.application.commands.pull_from_crm import (
        PullFromCRMHandler,
    )
    from searce_scout.crm_sync.application.commands.push_to_crm import (
        PushToCRMHandler,
    )
    from searce_scout.crm_sync.application.commands.resolve_conflict import (
        ResolveConflictHandler,
    )
    from searce_scout.crm_sync.application.queries.get_sync_status import (
        GetSyncStatusHandler,
    )
    from searce_scout.crm_sync.application.queries.list_conflicts import (
        ListConflictsHandler,
    )


def create_server(
    push_handler: PushToCRMHandler,
    pull_handler: PullFromCRMHandler,
    resolve_handler: ResolveConflictHandler,
    sync_status_query: GetSyncStatusHandler,
    conflicts_query: ListConflictsHandler,
) -> Server:
    """Factory that wires application-layer handlers into an MCP server.

    Args:
        push_handler: Handler for the ``push_to_crm`` tool.
        pull_handler: Handler for the ``pull_from_crm`` tool.
        resolve_handler: Handler for the ``resolve_conflict`` tool.
        sync_status_query: Handler for the ``crm://sync-status/{local_id}`` resource.
        conflicts_query: Handler for the ``crm://conflicts`` resource.

    Returns:
        A fully-configured :class:`mcp.server.Server` instance.
    """

    server = Server("crm-sync")

    # ------------------------------------------------------------------
    # Tools (writes)
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="push_to_crm",
                description=(
                    "Push a local record to the external CRM system "
                    "(Salesforce or HubSpot), mapping local fields to "
                    "CRM-specific fields."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "local_id": {
                            "type": "string",
                            "description": "The local identifier of the record to push.",
                        },
                        "record_type": {
                            "type": "string",
                            "description": "The type of CRM record (e.g. lead, contact, opportunity).",
                        },
                        "provider": {
                            "type": "string",
                            "description": "The CRM provider (e.g. salesforce, hubspot).",
                        },
                        "fields": {
                            "type": "object",
                            "description": "Key-value mapping of local field names to their values.",
                            "additionalProperties": {"type": "string"},
                        },
                    },
                    "required": ["local_id", "record_type", "provider", "fields"],
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="pull_from_crm",
                description=(
                    "Pull changes from the external CRM since a given "
                    "timestamp, mapping CRM fields back to local fields."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "description": "The CRM provider (e.g. salesforce, hubspot).",
                        },
                        "record_type": {
                            "type": "string",
                            "description": "The type of CRM record to pull (e.g. lead, contact, opportunity).",
                        },
                        "since": {
                            "type": "string",
                            "description": "ISO 8601 datetime string. Only records changed after this time are returned.",
                        },
                    },
                    "required": ["provider", "record_type", "since"],
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="resolve_conflict",
                description=(
                    "Resolve a field-level sync conflict for a CRM record "
                    "using a chosen resolution strategy, then push the "
                    "resolved data back to the CRM."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "record_id": {
                            "type": "string",
                            "description": "The identifier of the conflicting CRM record.",
                        },
                        "strategy": {
                            "type": "string",
                            "description": (
                                "Resolution strategy (e.g. local_wins, remote_wins, "
                                "merge, manual)."
                            ),
                        },
                    },
                    "required": ["record_id", "strategy"],
                    "additionalProperties": False,
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        from searce_scout.crm_sync.application.commands.pull_from_crm import (
            PullFromCRMCommand,
        )
        from searce_scout.crm_sync.application.commands.push_to_crm import (
            PushToCRMCommand,
        )
        from searce_scout.crm_sync.application.commands.resolve_conflict import (
            ResolveConflictCommand,
        )

        if name == "push_to_crm":
            cmd = PushToCRMCommand(
                local_id=arguments["local_id"],
                record_type=arguments["record_type"],
                provider=arguments["provider"],
                fields=arguments["fields"],
            )
            result = await push_handler.execute(cmd)
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "pull_from_crm":
            cmd = PullFromCRMCommand(
                provider=arguments["provider"],
                record_type=arguments["record_type"],
                since=arguments["since"],
            )
            results = await pull_handler.execute(cmd)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        [r.model_dump(mode="json") for r in results], indent=2
                    ),
                )
            ]

        if name == "resolve_conflict":
            cmd = ResolveConflictCommand(
                record_id=arguments["record_id"],
                strategy=arguments["strategy"],
            )
            result = await resolve_handler.execute(cmd)
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        raise ValueError(f"Unknown tool: {name}")

    # ------------------------------------------------------------------
    # Resources (reads)
    # ------------------------------------------------------------------

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="crm://sync-status/{local_id}",
                name="Sync Status",
                description="Returns the CRMRecordDTO showing sync status for a local record.",
                mimeType="application/json",
            ),
            Resource(
                uri="crm://conflicts",
                name="Sync Conflicts",
                description="Returns all CRM records currently in CONFLICT status.",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        from searce_scout.crm_sync.application.queries.get_sync_status import (
            GetSyncStatusQuery,
        )
        from searce_scout.crm_sync.application.queries.list_conflicts import (
            ListConflictsQuery,
        )

        uri_str = str(uri)

        if uri_str == "crm://conflicts":
            query = ListConflictsQuery()
            results = await conflicts_query.execute(query)
            return json.dumps(
                [r.model_dump(mode="json") for r in results], indent=2
            )

        if uri_str.startswith("crm://sync-status/"):
            local_id = uri_str.removeprefix("crm://sync-status/")
            query = GetSyncStatusQuery(local_id=local_id)
            result = await sync_status_query.execute(query)
            if result is None:
                return json.dumps({"error": f"No sync record found for: {local_id}"})
            return result.model_dump_json(indent=2)

        raise ValueError(f"Unknown resource URI: {uri_str}")

    return server
