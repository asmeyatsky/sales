"""MCP Schema Compliance Tests for CRM Sync Server.

Validates that the MCP server exposes the correct tools, resources,
input schemas, and correctly dispatches to application-layer handlers.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from searce_scout.crm_sync.infrastructure.mcp_server.server import create_server


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_handlers() -> dict[str, AsyncMock]:
    return {
        "push_handler": AsyncMock(),
        "pull_handler": AsyncMock(),
        "resolve_handler": AsyncMock(),
        "sync_status_query": AsyncMock(),
        "conflicts_query": AsyncMock(),
    }


@pytest.fixture()
def server(mock_handlers: dict[str, AsyncMock]):
    return create_server(**mock_handlers)


# ---------------------------------------------------------------------------
# Tool listing tests
# ---------------------------------------------------------------------------


async def test_list_tools_returns_push_pull_resolve(server):
    """list_tools() must return push_to_crm, pull_from_crm, and resolve_conflict."""
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    assert tool_names == {"push_to_crm", "pull_from_crm", "resolve_conflict"}
    assert len(tools) == 3


async def test_push_to_crm_schema(server):
    """push_to_crm must require local_id, record_type, provider, and fields."""
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "push_to_crm")
    schema = tool.inputSchema

    assert schema["type"] == "object"
    assert set(schema["required"]) == {"local_id", "record_type", "provider", "fields"}
    assert schema["properties"]["local_id"]["type"] == "string"
    assert schema["properties"]["record_type"]["type"] == "string"
    assert schema["properties"]["provider"]["type"] == "string"
    assert schema["properties"]["fields"]["type"] == "object"


async def test_pull_from_crm_schema(server):
    """pull_from_crm must require provider, record_type, and since."""
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "pull_from_crm")
    schema = tool.inputSchema

    assert schema["type"] == "object"
    assert set(schema["required"]) == {"provider", "record_type", "since"}
    assert schema["properties"]["since"]["type"] == "string"


async def test_resolve_conflict_schema(server):
    """resolve_conflict must require record_id and strategy."""
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "resolve_conflict")
    schema = tool.inputSchema

    assert schema["type"] == "object"
    assert set(schema["required"]) == {"record_id", "strategy"}
    assert schema["properties"]["record_id"]["type"] == "string"
    assert schema["properties"]["strategy"]["type"] == "string"


async def test_tools_have_descriptions(server):
    """Every tool must have a non-empty description."""
    tools = await server.list_tools()
    for tool in tools:
        assert tool.description, f"Tool '{tool.name}' has no description"


# ---------------------------------------------------------------------------
# Resource listing tests
# ---------------------------------------------------------------------------


async def test_list_resources_returns_status_and_conflicts(server):
    """list_resources() must return sync-status and conflicts."""
    resources = await server.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "crm://sync-status/{local_id}" in uris
    assert "crm://conflicts" in uris


async def test_resources_have_json_mime(server):
    """All resources should declare application/json mimeType."""
    resources = await server.list_resources()
    for resource in resources:
        assert resource.mimeType == "application/json"


# ---------------------------------------------------------------------------
# Round-trip call_tool tests
# ---------------------------------------------------------------------------


async def test_call_push_to_crm_invokes_handler(
    server, mock_handlers: dict[str, AsyncMock]
):
    """call_tool('push_to_crm', ...) must invoke the push handler."""
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = json.dumps(
        {"record_id": "rec-1", "sync_status": "SYNCED"}
    )
    mock_handlers["push_handler"].execute.return_value = mock_result

    result = await server.call_tool(
        "push_to_crm",
        {
            "local_id": "acc-1",
            "record_type": "ACCOUNT",
            "provider": "salesforce",
            "fields": {"Name": "TestCo", "Industry": "Technology"},
        },
    )

    mock_handlers["push_handler"].execute.assert_awaited_once()
    cmd = mock_handlers["push_handler"].execute.call_args[0][0]
    assert cmd.local_id == "acc-1"
    assert cmd.record_type == "ACCOUNT"
    assert cmd.provider == "salesforce"
    assert cmd.fields == {"Name": "TestCo", "Industry": "Technology"}
    assert len(result) == 1
    payload = json.loads(result[0].text)
    assert payload["sync_status"] == "SYNCED"


async def test_call_pull_from_crm_invokes_handler(
    server, mock_handlers: dict[str, AsyncMock]
):
    """call_tool('pull_from_crm', ...) must invoke the pull handler."""
    mock_dto = MagicMock()
    mock_dto.model_dump.return_value = {"record_id": "rec-1", "fields": {}}
    mock_handlers["pull_handler"].execute.return_value = [mock_dto]

    result = await server.call_tool(
        "pull_from_crm",
        {
            "provider": "salesforce",
            "record_type": "LEAD",
            "since": "2026-01-01T00:00:00Z",
        },
    )

    mock_handlers["pull_handler"].execute.assert_awaited_once()
    cmd = mock_handlers["pull_handler"].execute.call_args[0][0]
    assert cmd.provider == "salesforce"
    assert cmd.record_type == "LEAD"
    assert cmd.since == "2026-01-01T00:00:00Z"
    assert len(result) == 1
    payload = json.loads(result[0].text)
    assert isinstance(payload, list)


async def test_call_resolve_conflict_invokes_handler(
    server, mock_handlers: dict[str, AsyncMock]
):
    """call_tool('resolve_conflict', ...) must invoke the resolve handler."""
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = json.dumps({"status": "resolved"})
    mock_handlers["resolve_handler"].execute.return_value = mock_result

    result = await server.call_tool(
        "resolve_conflict",
        {"record_id": "rec-1", "strategy": "local_wins"},
    )

    mock_handlers["resolve_handler"].execute.assert_awaited_once()
    cmd = mock_handlers["resolve_handler"].execute.call_args[0][0]
    assert cmd.record_id == "rec-1"
    assert cmd.strategy == "local_wins"
    assert len(result) == 1


async def test_call_unknown_tool_raises(server):
    """Calling an unknown tool name must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown tool"):
        await server.call_tool("nonexistent_tool", {})
