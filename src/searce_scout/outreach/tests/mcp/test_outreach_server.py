"""MCP Schema Compliance Tests for Outreach Server.

Validates that the MCP server exposes the correct tools, resources,
input schemas, and correctly dispatches to application-layer handlers.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from searce_scout.outreach.infrastructure.mcp_server.server import create_server


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_handlers() -> dict[str, AsyncMock]:
    return {
        "start_handler": AsyncMock(),
        "execute_next_handler": AsyncMock(),
        "process_reply_handler": AsyncMock(),
        "stop_handler": AsyncMock(),
        "sequence_status_query": AsyncMock(),
        "active_sequences_query": AsyncMock(),
    }


@pytest.fixture()
def server(mock_handlers: dict[str, AsyncMock]):
    return create_server(**mock_handlers)


# ---------------------------------------------------------------------------
# Tool listing tests
# ---------------------------------------------------------------------------


async def test_list_tools_returns_four_tools(server):
    """list_tools() must return start, execute, process_reply, and stop."""
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    assert tool_names == {
        "start_sequence",
        "execute_next_step",
        "process_reply",
        "stop_sequence",
    }
    assert len(tools) == 4


async def test_start_sequence_schema(server):
    """start_sequence must require account_id, stakeholder_id, and message_ids."""
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "start_sequence")
    schema = tool.inputSchema

    assert schema["type"] == "object"
    assert set(schema["required"]) == {"account_id", "stakeholder_id", "message_ids"}
    assert schema["properties"]["account_id"]["type"] == "string"
    assert schema["properties"]["stakeholder_id"]["type"] == "string"
    assert schema["properties"]["message_ids"]["type"] == "object"


async def test_execute_next_step_schema(server):
    """execute_next_step must require sequence_id."""
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "execute_next_step")
    schema = tool.inputSchema

    assert schema["required"] == ["sequence_id"]
    assert schema["properties"]["sequence_id"]["type"] == "string"


async def test_process_reply_schema(server):
    """process_reply must require sequence_id and raw_content."""
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "process_reply")
    schema = tool.inputSchema

    assert set(schema["required"]) == {"sequence_id", "raw_content"}
    assert schema["properties"]["raw_content"]["type"] == "string"


async def test_stop_sequence_schema(server):
    """stop_sequence must require sequence_id and reason."""
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "stop_sequence")
    schema = tool.inputSchema

    assert set(schema["required"]) == {"sequence_id", "reason"}
    assert schema["properties"]["reason"]["type"] == "string"


async def test_tools_have_descriptions(server):
    """Every tool must have a non-empty description."""
    tools = await server.list_tools()
    for tool in tools:
        assert tool.description, f"Tool '{tool.name}' has no description"


# ---------------------------------------------------------------------------
# Resource listing tests
# ---------------------------------------------------------------------------


async def test_list_resources_returns_sequence_and_active(server):
    """list_resources() must return sequence status and active-sequences."""
    resources = await server.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "outreach://sequence/{sequence_id}" in uris
    assert "outreach://active-sequences" in uris


async def test_resources_have_json_mime(server):
    """All resources should declare application/json mimeType."""
    resources = await server.list_resources()
    for resource in resources:
        assert resource.mimeType == "application/json"


# ---------------------------------------------------------------------------
# Round-trip call_tool tests
# ---------------------------------------------------------------------------


async def test_call_start_sequence_invokes_handler(
    server, mock_handlers: dict[str, AsyncMock]
):
    """call_tool('start_sequence', ...) must invoke the start handler."""
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = json.dumps(
        {"sequence_id": "seq-1", "status": "ACTIVE"}
    )
    mock_handlers["start_handler"].execute.return_value = mock_result

    result = await server.call_tool(
        "start_sequence",
        {
            "account_id": "acc-1",
            "stakeholder_id": "sh-1",
            "message_ids": {"EMAIL_1": "msg-1", "LINKEDIN_REQUEST": "msg-2"},
        },
    )

    mock_handlers["start_handler"].execute.assert_awaited_once()
    cmd = mock_handlers["start_handler"].execute.call_args[0][0]
    assert cmd.account_id == "acc-1"
    assert cmd.stakeholder_id == "sh-1"
    assert cmd.message_ids == {"EMAIL_1": "msg-1", "LINKEDIN_REQUEST": "msg-2"}
    assert len(result) == 1


async def test_call_stop_sequence_invokes_handler(
    server, mock_handlers: dict[str, AsyncMock]
):
    """call_tool('stop_sequence', ...) must invoke the stop handler."""
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = json.dumps({"status": "STOPPED"})
    mock_handlers["stop_handler"].execute.return_value = mock_result

    result = await server.call_tool(
        "stop_sequence",
        {"sequence_id": "seq-1", "reason": "Customer replied positively"},
    )

    mock_handlers["stop_handler"].execute.assert_awaited_once()
    cmd = mock_handlers["stop_handler"].execute.call_args[0][0]
    assert cmd.sequence_id == "seq-1"
    assert cmd.reason == "Customer replied positively"
    assert len(result) == 1


async def test_call_process_reply_invokes_handler(
    server, mock_handlers: dict[str, AsyncMock]
):
    """call_tool('process_reply', ...) must invoke the process_reply handler."""
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = json.dumps({"action": "stop"})
    mock_handlers["process_reply_handler"].execute.return_value = mock_result

    result = await server.call_tool(
        "process_reply",
        {"sequence_id": "seq-1", "raw_content": "Thanks for reaching out!"},
    )

    mock_handlers["process_reply_handler"].execute.assert_awaited_once()
    cmd = mock_handlers["process_reply_handler"].execute.call_args[0][0]
    assert cmd.sequence_id == "seq-1"
    assert cmd.raw_content == "Thanks for reaching out!"
    assert len(result) == 1


async def test_call_unknown_tool_raises(server):
    """Calling an unknown tool name must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown tool"):
        await server.call_tool("nonexistent_tool", {})
