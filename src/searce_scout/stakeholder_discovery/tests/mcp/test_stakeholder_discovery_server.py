"""MCP Schema Compliance Tests for Stakeholder Discovery Server.

Validates that the MCP server exposes the correct tools, resources,
input schemas, and correctly dispatches to application-layer handlers.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from searce_scout.stakeholder_discovery.infrastructure.mcp_server.server import (
    create_server,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_handlers() -> dict[str, AsyncMock]:
    return {
        "discover_handler": AsyncMock(),
        "validate_handler": AsyncMock(),
        "stakeholders_query": AsyncMock(),
        "validated_query": AsyncMock(),
    }


@pytest.fixture()
def server(mock_handlers: dict[str, AsyncMock]):
    return create_server(**mock_handlers)


# ---------------------------------------------------------------------------
# Tool listing tests
# ---------------------------------------------------------------------------


async def test_list_tools_returns_discover_and_validate(server):
    """list_tools() must return discover_stakeholders and validate_contact."""
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    assert tool_names == {"discover_stakeholders", "validate_contact"}


async def test_discover_stakeholders_schema(server):
    """discover_stakeholders must require account_id and company_name."""
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "discover_stakeholders")
    schema = tool.inputSchema

    assert schema["type"] == "object"
    assert set(schema["required"]) == {"account_id", "company_name"}
    assert schema["properties"]["account_id"]["type"] == "string"
    assert schema["properties"]["company_name"]["type"] == "string"


async def test_validate_contact_schema(server):
    """validate_contact must require stakeholder_id."""
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "validate_contact")
    schema = tool.inputSchema

    assert schema["type"] == "object"
    assert schema["required"] == ["stakeholder_id"]
    assert schema["properties"]["stakeholder_id"]["type"] == "string"


async def test_tools_have_descriptions(server):
    """Every tool must have a non-empty description."""
    tools = await server.list_tools()
    for tool in tools:
        assert tool.description, f"Tool '{tool.name}' has no description"


# ---------------------------------------------------------------------------
# Resource listing tests
# ---------------------------------------------------------------------------


async def test_list_resources_returns_account_and_validated(server):
    """list_resources() must return stakeholder://account and stakeholder://validated."""
    resources = await server.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "stakeholder://account/{account_id}" in uris
    assert "stakeholder://validated/{account_id}" in uris


async def test_resources_have_json_mime(server):
    """All resources should declare application/json mimeType."""
    resources = await server.list_resources()
    for resource in resources:
        assert resource.mimeType == "application/json"


# ---------------------------------------------------------------------------
# Round-trip call_tool tests
# ---------------------------------------------------------------------------


async def test_call_discover_stakeholders_invokes_handler(
    server, mock_handlers: dict[str, AsyncMock]
):
    """call_tool('discover_stakeholders', ...) must invoke the discover handler."""
    mock_result = [MagicMock()]
    mock_result[0].model_dump.return_value = {"stakeholder_id": "sh-1", "full_name": "Jane Doe"}
    mock_handlers["discover_handler"].execute.return_value = mock_result

    result = await server.call_tool(
        "discover_stakeholders",
        {"account_id": "acc-1", "company_name": "TestCo"},
    )

    mock_handlers["discover_handler"].execute.assert_awaited_once()
    cmd = mock_handlers["discover_handler"].execute.call_args[0][0]
    assert cmd.account_id == "acc-1"
    assert cmd.company_name == "TestCo"
    assert len(result) == 1
    payload = json.loads(result[0].text)
    assert isinstance(payload, list)
    assert payload[0]["stakeholder_id"] == "sh-1"


async def test_call_validate_contact_invokes_handler(
    server, mock_handlers: dict[str, AsyncMock]
):
    """call_tool('validate_contact', ...) must invoke the validate handler."""
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = json.dumps({"status": "validated"})
    mock_handlers["validate_handler"].execute.return_value = mock_result

    result = await server.call_tool(
        "validate_contact",
        {"stakeholder_id": "sh-1"},
    )

    mock_handlers["validate_handler"].execute.assert_awaited_once()
    cmd = mock_handlers["validate_handler"].execute.call_args[0][0]
    assert cmd.stakeholder_id == "sh-1"
    assert len(result) == 1


async def test_call_unknown_tool_raises(server):
    """Calling an unknown tool name must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown tool"):
        await server.call_tool("nonexistent_tool", {})
