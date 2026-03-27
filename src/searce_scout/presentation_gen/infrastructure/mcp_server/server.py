"""Presentation Gen MCP Server.

Exposes deck generation as an MCP tool (write), and deck retrieval as
MCP resources (reads).  Follows skill2026 Rule 6: tools for writes,
resources for reads.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from mcp.server import Server
from mcp.types import Resource, TextContent, Tool

if TYPE_CHECKING:
    from searce_scout.presentation_gen.application.commands.generate_deck import (
        GenerateDeckHandler,
    )
    from searce_scout.presentation_gen.application.queries.get_deck import (
        GetDeckHandler,
    )
    from searce_scout.presentation_gen.application.queries.list_decks_for_account import (
        ListDecksForAccountHandler,
    )


def create_server(
    generate_handler: GenerateDeckHandler,
    deck_query: GetDeckHandler,
    decks_for_account_query: ListDecksForAccountHandler,
) -> Server:
    """Factory that wires application-layer handlers into an MCP server.

    Args:
        generate_handler: Handler for the ``generate_deck`` tool.
        deck_query: Handler for the ``deck://detail/{deck_id}`` resource.
        decks_for_account_query: Handler for the ``deck://account/{account_id}`` resource.

    Returns:
        A fully-configured :class:`mcp.server.Server` instance.
    """

    server = Server("presentation-gen")

    # ------------------------------------------------------------------
    # Tools (writes)
    # ------------------------------------------------------------------

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="generate_deck",
                description=(
                    "Generate a personalised sales deck for an account, "
                    "using AI to create slide content and rendering to "
                    "Google Slides."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {
                            "type": "string",
                            "description": "Target account identifier.",
                        },
                        "offering": {
                            "type": "string",
                            "description": "Optional Searce offering to focus the deck on.",
                        },
                        "template_id": {
                            "type": "string",
                            "description": "Optional slide template identifier to use.",
                        },
                        "account_context": {
                            "type": "object",
                            "description": (
                                "Cross-BC account research data. Expected keys: "
                                "company_name, industry, tech_stack_summary, "
                                "buying_signals, pain_points, searce_offering."
                            ),
                        },
                    },
                    "required": ["account_id", "account_context"],
                    "additionalProperties": False,
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        from searce_scout.presentation_gen.application.commands.generate_deck import (
            GenerateDeckCommand,
        )

        if name == "generate_deck":
            cmd = GenerateDeckCommand(
                account_id=arguments["account_id"],
                offering=arguments.get("offering"),
                template_id=arguments.get("template_id", ""),
            )
            result = await generate_handler.execute(
                cmd,
                account_context=arguments.get("account_context", {}),
            )
            return [TextContent(type="text", text=result.model_dump_json(indent=2))]

        raise ValueError(f"Unknown tool: {name}")

    # ------------------------------------------------------------------
    # Resources (reads)
    # ------------------------------------------------------------------

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="deck://detail/{deck_id}",
                name="Deck Detail",
                description="Returns the full DeckDTO for a single slide deck.",
                mimeType="application/json",
            ),
            Resource(
                uri="deck://account/{account_id}",
                name="Decks for Account",
                description="Returns all DeckDTOs generated for the given account.",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        from searce_scout.presentation_gen.application.queries.get_deck import (
            GetDeckQuery,
        )
        from searce_scout.presentation_gen.application.queries.list_decks_for_account import (
            ListDecksForAccountQuery,
        )

        uri_str = str(uri)

        if uri_str.startswith("deck://detail/"):
            deck_id = uri_str.removeprefix("deck://detail/")
            query = GetDeckQuery(deck_id=deck_id)
            result = await deck_query.execute(query)
            if result is None:
                return json.dumps({"error": f"Deck not found: {deck_id}"})
            return result.model_dump_json(indent=2)

        if uri_str.startswith("deck://account/"):
            account_id = uri_str.removeprefix("deck://account/")
            query = ListDecksForAccountQuery(account_id=account_id)
            results = await decks_for_account_query.execute(query)
            return json.dumps(
                [r.model_dump(mode="json") for r in results], indent=2
            )

        raise ValueError(f"Unknown resource URI: {uri_str}")

    return server
