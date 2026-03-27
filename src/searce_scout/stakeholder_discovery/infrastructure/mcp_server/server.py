"""Stakeholder Discovery MCP Server.

Exposes stakeholder discovery and contact validation as MCP tools (writes),
and stakeholder listings as MCP resources (reads).  Follows skill2026
Rule 6: tools for writes, resources for reads.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

if TYPE_CHECKING:
    from searce_scout.stakeholder_discovery.application.commands.discover_stakeholders import (
        DiscoverStakeholdersHandler,
    )
    from searce_scout.stakeholder_discovery.application.commands.validate_contact import (
        ValidateContactHandler,
    )
    from searce_scout.stakeholder_discovery.application.queries.get_stakeholders_for_account import (
        GetStakeholdersForAccountHandler,
    )
    from searce_scout.stakeholder_discovery.application.queries.get_validated_contacts import (
        GetValidatedContactsHandler,
    )


def create_server(
    discover_handler: DiscoverStakeholdersHandler,
    validate_handler: ValidateContactHandler,
    stakeholders_query: GetStakeholdersForAccountHandler,
    validated_query: GetValidatedContactsHandler,
) -> Server:
    """Factory that wires application-layer handlers into an MCP server.

    Args:
        discover_handler: Handler for the ``discover_stakeholders`` tool.
        validate_handler: Handler for the ``validate_contact`` tool.
        stakeholders_query: Handler for the ``stakeholder://account/{account_id}`` resource.
        validated_query: Handler for the ``stakeholder://validated/{account_id}`` resource.

    Returns:
        A fully-configured :class:`mcp.server.Server` instance.
    """

    server = Server("stakeholder-discovery")

    # ------------------------------------------------------------------
    # Tools (writes)
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="discover_stakeholders",
                description=(
                    "Discover key stakeholders at a target account by searching "
                    "LinkedIn and enrichment sources, then score persona relevance."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {
                            "type": "string",
                            "description": "The unique identifier of the target account.",
                        },
                        "company_name": {
                            "type": "string",
                            "description": "The company name used for LinkedIn and enrichment lookups.",
                        },
                    },
                    "required": ["account_id", "company_name"],
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="validate_contact",
                description=(
                    "Validate and enrich a stakeholder's contact information "
                    "(email, phone) via external enrichment providers."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stakeholder_id": {
                            "type": "string",
                            "description": "The unique identifier of the stakeholder to validate.",
                        },
                    },
                    "required": ["stakeholder_id"],
                    "additionalProperties": False,
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        from searce_scout.stakeholder_discovery.application.commands.discover_stakeholders import (
            DiscoverStakeholdersCommand,
        )
        from searce_scout.stakeholder_discovery.application.commands.validate_contact import (
            ValidateContactCommand,
        )

        if name == "discover_stakeholders":
            cmd = DiscoverStakeholdersCommand(
                account_id=arguments["account_id"],
                company_name=arguments["company_name"],
            )
            results = await discover_handler.execute(cmd)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        [r.model_dump(mode="json") for r in results], indent=2
                    ),
                )
            ]

        if name == "validate_contact":
            cmd = ValidateContactCommand(
                stakeholder_id=arguments["stakeholder_id"],
            )
            result = await validate_handler.execute(cmd)
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        raise ValueError(f"Unknown tool: {name}")

    # ------------------------------------------------------------------
    # Resources (reads)
    # ------------------------------------------------------------------

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="stakeholder://account/{account_id}",
                name="Stakeholders for Account",
                description="Returns all discovered stakeholders for the given account.",
                mimeType="application/json",
            ),
            Resource(
                uri="stakeholder://validated/{account_id}",
                name="Validated Contacts",
                description="Returns only stakeholders with validated email addresses for the given account.",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        from searce_scout.stakeholder_discovery.application.queries.get_stakeholders_for_account import (
            GetStakeholdersForAccountQuery,
        )
        from searce_scout.stakeholder_discovery.application.queries.get_validated_contacts import (
            GetValidatedContactsQuery,
        )

        uri_str = str(uri)

        if uri_str.startswith("stakeholder://account/"):
            account_id = uri_str.removeprefix("stakeholder://account/")
            query = GetStakeholdersForAccountQuery(account_id=account_id)
            results = await stakeholders_query.execute(query)
            return json.dumps(
                [r.model_dump(mode="json") for r in results], indent=2
            )

        if uri_str.startswith("stakeholder://validated/"):
            account_id = uri_str.removeprefix("stakeholder://validated/")
            query = GetValidatedContactsQuery(account_id=account_id)
            results = await validated_query.execute(query)
            return json.dumps(
                [r.model_dump(mode="json") for r in results], indent=2
            )

        raise ValueError(f"Unknown resource URI: {uri_str}")

    return server
