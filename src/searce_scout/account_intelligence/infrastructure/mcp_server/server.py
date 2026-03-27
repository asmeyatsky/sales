"""Account Intelligence MCP Server.

Exposes account research and tech-stack auditing as MCP tools (writes),
and account profiles, buying signals, and migration targets as MCP
resources (reads).  Follows skill2026 Rule 6: tools for writes, resources
for reads.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

if TYPE_CHECKING:
    from searce_scout.account_intelligence.application.commands.audit_tech_stack import (
        AuditTechStackHandler,
    )
    from searce_scout.account_intelligence.application.commands.research_account import (
        ResearchAccountHandler,
    )
    from searce_scout.account_intelligence.application.queries.find_migration_targets import (
        FindMigrationTargetsHandler,
    )
    from searce_scout.account_intelligence.application.queries.get_account_profile import (
        GetAccountProfileHandler,
    )
    from searce_scout.account_intelligence.application.queries.list_buying_signals import (
        ListBuyingSignalsHandler,
    )


def create_server(
    research_handler: ResearchAccountHandler,
    audit_handler: AuditTechStackHandler,
    profile_query: GetAccountProfileHandler,
    signals_query: ListBuyingSignalsHandler,
    targets_query: FindMigrationTargetsHandler,
) -> Server:
    """Factory that wires application-layer handlers into an MCP server.

    Args:
        research_handler: Handler for the ``research_account`` tool.
        audit_handler: Handler for the ``audit_tech_stack`` tool.
        profile_query: Handler for the ``account://profiles/{account_id}`` resource.
        signals_query: Handler for the ``account://signals/{account_id}`` resource.
        targets_query: Handler for the ``account://migration-targets`` resource.

    Returns:
        A fully-configured :class:`mcp.server.Server` instance.
    """

    server = Server("account-intelligence")

    # ------------------------------------------------------------------
    # Tools (writes)
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="research_account",
                description=(
                    "Research a company to build an account profile with "
                    "buying signals, tech stack, and migration opportunity score."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "The name of the company to research.",
                        },
                        "website": {
                            "type": "string",
                            "description": "Optional company website URL.",
                        },
                        "ticker": {
                            "type": "string",
                            "description": "Optional stock ticker symbol for SEC filing lookup.",
                        },
                    },
                    "required": ["company_name"],
                    "additionalProperties": False,
                },
            ),
            Tool(
                name="audit_tech_stack",
                description=(
                    "Detect the technology stack for an existing account by "
                    "scanning its domain, then analyse migration potential."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {
                            "type": "string",
                            "description": "The unique identifier of the account to audit.",
                        },
                        "domain": {
                            "type": "string",
                            "description": "The web domain to scan for technology detection.",
                        },
                    },
                    "required": ["account_id", "domain"],
                    "additionalProperties": False,
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        from searce_scout.account_intelligence.application.commands.audit_tech_stack import (
            AuditTechStackCommand,
        )
        from searce_scout.account_intelligence.application.commands.research_account import (
            ResearchAccountCommand,
        )

        if name == "research_account":
            cmd = ResearchAccountCommand(
                company_name=arguments["company_name"],
                website=arguments.get("website"),
                ticker=arguments.get("ticker"),
            )
            result = await research_handler.execute(cmd)
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        if name == "audit_tech_stack":
            cmd = AuditTechStackCommand(
                account_id=arguments["account_id"],
                domain=arguments["domain"],
            )
            result = await audit_handler.execute(cmd)
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        raise ValueError(f"Unknown tool: {name}")

    # ------------------------------------------------------------------
    # Resources (reads)
    # ------------------------------------------------------------------

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="account://profiles/{account_id}",
                name="Account Profile",
                description="Returns the full AccountProfileDTO for a given account.",
                mimeType="application/json",
            ),
            Resource(
                uri="account://signals/{account_id}",
                name="Buying Signals",
                description="Returns all buying signals detected for an account.",
                mimeType="application/json",
            ),
            Resource(
                uri="account://migration-targets",
                name="Migration Targets",
                description="Returns all high-intent accounts that are migration targets.",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        from searce_scout.account_intelligence.application.queries.find_migration_targets import (
            FindMigrationTargetsQuery,
        )
        from searce_scout.account_intelligence.application.queries.get_account_profile import (
            GetAccountProfileQuery,
        )
        from searce_scout.account_intelligence.application.queries.list_buying_signals import (
            ListBuyingSignalsQuery,
        )

        uri_str = str(uri)

        if uri_str == "account://migration-targets":
            query = FindMigrationTargetsQuery()
            results = await targets_query.execute(query)
            return json.dumps(
                [r.model_dump(mode="json") for r in results], indent=2
            )

        if uri_str.startswith("account://profiles/"):
            account_id = uri_str.removeprefix("account://profiles/")
            query = GetAccountProfileQuery(account_id=account_id)
            result = await profile_query.execute(query)
            if result is None:
                return json.dumps({"error": f"Account not found: {account_id}"})
            return result.model_dump_json(indent=2)

        if uri_str.startswith("account://signals/"):
            account_id = uri_str.removeprefix("account://signals/")
            query = ListBuyingSignalsQuery(account_id=account_id)
            results = await signals_query.execute(query)
            return json.dumps(
                [r.model_dump(mode="json") for r in results], indent=2
            )

        raise ValueError(f"Unknown resource URI: {uri_str}")

    return server
