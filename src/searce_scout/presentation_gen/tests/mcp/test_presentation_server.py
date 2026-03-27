"""MCP Schema Compliance Tests for Presentation Gen Server.

Validates that the MCP server exposes the correct tools, resources,
input schemas, and correctly dispatches to application-layer handlers.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from searce_scout.presentation_gen.infrastructure.mcp_server.server import create_server


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_handlers() -> dict[str, AsyncMock]:
    return {
        "generate_handler": AsyncMock(),
        "deck_query": AsyncMock(),
        "decks_for_account_query": AsyncMock(),
    }


@pytest.fixture()
def server(mock_handlers: dict[str, AsyncMock]):
    return create_server(**mock_handlers)


# ---------------------------------------------------------------------------
# Tool listing tests
# ---------------------------------------------------------------------------


async def test_list_tools_returns_generate_deck(server):
    """list_tools() must return exactly one tool: generate_deck."""
    tools = await server.list_tools()
    assert len(tools) == 1
    assert tools[0].name == "generate_deck"


async def test_generate_deck_schema(server):
    """generate_deck must require account_id and account_context."""
    tools = await server.list_tools()
    tool = tools[0]
    schema = tool.inputSchema

    assert schema["type"] == "object"
    assert set(schema["required"]) == {"account_id", "account_context"}
    assert schema["properties"]["account_id"]["type"] == "string"
    assert schema["properties"]["account_context"]["type"] == "object"
    # Optional fields
    assert "offering" in schema["properties"]
    assert "template_id" in schema["properties"]


async def test_tool_has_description(server):
    """The generate_deck tool must have a non-empty description."""
    tools = await server.list_tools()
    assert tools[0].description
    assert len(tools[0].description) > 10


# ---------------------------------------------------------------------------
# Resource listing tests
# ---------------------------------------------------------------------------


async def test_list_resources_returns_detail_and_account(server):
    """list_resources() must return deck://detail and deck://account."""
    resources = await server.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "deck://detail/{deck_id}" in uris
    assert "deck://account/{account_id}" in uris


async def test_resources_have_json_mime(server):
    """All resources should declare application/json mimeType."""
    resources = await server.list_resources()
    for resource in resources:
        assert resource.mimeType == "application/json"


# ---------------------------------------------------------------------------
# Round-trip call_tool tests
# ---------------------------------------------------------------------------


async def test_call_generate_deck_invokes_handler(
    server, mock_handlers: dict[str, AsyncMock]
):
    """call_tool('generate_deck', ...) must invoke the generate handler
    with the command and account_context."""
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = json.dumps(
        {"deck_id": "deck-1", "slide_count": 5}
    )
    mock_handlers["generate_handler"].execute.return_value = mock_result

    result = await server.call_tool(
        "generate_deck",
        {
            "account_id": "acc-1",
            "offering": "Cloud Migration",
            "account_context": {"company_name": "TestCo", "industry": "Tech"},
        },
    )

    mock_handlers["generate_handler"].execute.assert_awaited_once()
    call_args = mock_handlers["generate_handler"].execute.call_args
    cmd = call_args[0][0]
    assert cmd.account_id == "acc-1"
    assert cmd.offering == "Cloud Migration"
    assert call_args.kwargs["account_context"] == {"company_name": "TestCo", "industry": "Tech"}

    assert len(result) == 1
    payload = json.loads(result[0].text)
    assert payload["deck_id"] == "deck-1"


async def test_call_generate_deck_without_optional_fields(
    server, mock_handlers: dict[str, AsyncMock]
):
    """generate_deck should work with only required fields."""
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = json.dumps({"deck_id": "deck-2"})
    mock_handlers["generate_handler"].execute.return_value = mock_result

    result = await server.call_tool(
        "generate_deck",
        {
            "account_id": "acc-2",
            "account_context": {"company_name": "TestCo"},
        },
    )

    mock_handlers["generate_handler"].execute.assert_awaited()
    cmd = mock_handlers["generate_handler"].execute.call_args[0][0]
    assert cmd.account_id == "acc-2"
    assert cmd.offering is None
    assert len(result) == 1


async def test_call_unknown_tool_raises(server):
    """Calling an unknown tool name must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown tool"):
        await server.call_tool("nonexistent_tool", {})
