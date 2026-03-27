"""MCP Schema Compliance Tests for Account Intelligence Server.

Validates that the MCP server exposes the correct tools, resources,
input schemas, and correctly dispatches to application-layer handlers.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from searce_scout.account_intelligence.infrastructure.mcp_server.server import (
    create_server,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_handlers() -> dict[str, AsyncMock]:
    """Create AsyncMock handlers for all create_server parameters."""
    research = AsyncMock()
    audit = AsyncMock()
    profile_query = AsyncMock()
    signals_query = AsyncMock()
    targets_query = AsyncMock()
    return {
        "research_handler": research,
        "audit_handler": audit,
        "profile_query": profile_query,
        "signals_query": signals_query,
        "targets_query": targets_query,
    }


@pytest.fixture()
def server(mock_handlers: dict[str, AsyncMock]):
    return create_server(**mock_handlers)


# ---------------------------------------------------------------------------
# Tool listing tests
# ---------------------------------------------------------------------------


async def test_list_tools_returns_research_and_audit(server):
    """list_tools() must return exactly research_account and audit_tech_stack."""
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    assert tool_names == {"research_account", "audit_tech_stack"}


async def test_research_account_tool_schema_has_company_name(server):
    """research_account inputSchema must require company_name as a string."""
    tools = await server.list_tools()
    research_tool = next(t for t in tools if t.name == "research_account")
    schema = research_tool.inputSchema

    assert schema["type"] == "object"
    assert "company_name" in schema["properties"]
    assert schema["properties"]["company_name"]["type"] == "string"
    assert "company_name" in schema["required"]
    # Optional fields should also be present
    assert "website" in schema["properties"]
    assert "ticker" in schema["properties"]


async def test_audit_tech_stack_tool_schema(server):
    """audit_tech_stack inputSchema must require account_id and domain."""
    tools = await server.list_tools()
    audit_tool = next(t for t in tools if t.name == "audit_tech_stack")
    schema = audit_tool.inputSchema

    assert schema["type"] == "object"
    assert set(schema["required"]) == {"account_id", "domain"}
    assert schema["properties"]["account_id"]["type"] == "string"
    assert schema["properties"]["domain"]["type"] == "string"


async def test_tools_have_descriptions(server):
    """Every tool must have a non-empty description."""
    tools = await server.list_tools()
    for tool in tools:
        assert tool.description, f"Tool '{tool.name}' has no description"
        assert len(tool.description) > 10


# ---------------------------------------------------------------------------
# Resource listing tests
# ---------------------------------------------------------------------------


async def test_list_resources_returns_profiles_and_signals(server):
    """list_resources() must return profiles, signals, and migration-targets."""
    resources = await server.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "account://profiles/{account_id}" in uris
    assert "account://signals/{account_id}" in uris
    assert "account://migration-targets" in uris


async def test_resources_have_mime_type(server):
    """All resources should declare application/json mimeType."""
    resources = await server.list_resources()
    for resource in resources:
        assert resource.mimeType == "application/json"


# ---------------------------------------------------------------------------
# Round-trip call_tool tests
# ---------------------------------------------------------------------------


async def test_call_research_account_invokes_handler(
    server, mock_handlers: dict[str, AsyncMock]
):
    """call_tool('research_account', ...) must invoke the research handler
    with a ResearchAccountCommand matching the provided arguments."""
    # Arrange: configure mock to return a DTO-like object
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = json.dumps(
        {"account_id": "acc-1", "company_name": "TestCo"}
    )
    mock_handlers["research_handler"].execute.return_value = mock_result

    # Act
    result = await server.call_tool(
        "research_account",
        {"company_name": "TestCo", "website": "https://testco.com"},
    )

    # Assert handler was called
    mock_handlers["research_handler"].execute.assert_awaited_once()
    cmd = mock_handlers["research_handler"].execute.call_args[0][0]
    assert cmd.company_name == "TestCo"
    assert cmd.website == "https://testco.com"

    # Assert result is a list of TextContent
    assert len(result) == 1
    assert result[0].type == "text"
    payload = json.loads(result[0].text)
    assert payload["account_id"] == "acc-1"


async def test_call_audit_tech_stack_invokes_handler(
    server, mock_handlers: dict[str, AsyncMock]
):
    """call_tool('audit_tech_stack', ...) must invoke the audit handler."""
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = json.dumps({"status": "ok"})
    mock_handlers["audit_handler"].execute.return_value = mock_result

    result = await server.call_tool(
        "audit_tech_stack",
        {"account_id": "acc-1", "domain": "testco.com"},
    )

    mock_handlers["audit_handler"].execute.assert_awaited_once()
    cmd = mock_handlers["audit_handler"].execute.call_args[0][0]
    assert cmd.account_id == "acc-1"
    assert cmd.domain == "testco.com"
    assert len(result) == 1


async def test_call_unknown_tool_raises(server):
    """Calling an unknown tool name must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown tool"):
        await server.call_tool("nonexistent_tool", {})
