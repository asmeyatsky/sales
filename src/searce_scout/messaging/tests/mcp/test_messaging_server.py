"""MCP Schema Compliance Tests for Messaging Server.

Validates that the MCP server exposes the correct tools, resources,
input schemas, and correctly dispatches to application-layer handlers.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from searce_scout.messaging.infrastructure.mcp_server.server import create_server


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_handlers() -> dict[str, AsyncMock]:
    return {
        "generate_handler": AsyncMock(),
        "adjust_tone_handler": AsyncMock(),
        "message_query": AsyncMock(),
        "preview_query": AsyncMock(),
    }


@pytest.fixture()
def server(mock_handlers: dict[str, AsyncMock]):
    return create_server(**mock_handlers)


# ---------------------------------------------------------------------------
# Tool listing tests
# ---------------------------------------------------------------------------


async def test_list_tools_returns_generate_and_adjust(server):
    """list_tools() must return generate_message and adjust_tone."""
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    assert tool_names == {"generate_message", "adjust_tone"}


async def test_generate_message_schema_has_required_fields(server):
    """generate_message inputSchema must require all seven fields."""
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "generate_message")
    schema = tool.inputSchema

    assert schema["type"] == "object"
    expected_required = {
        "account_id",
        "stakeholder_id",
        "channel",
        "tone",
        "step_number",
        "account_context",
        "stakeholder_context",
    }
    assert set(schema["required"]) == expected_required

    # Verify types
    assert schema["properties"]["account_id"]["type"] == "string"
    assert schema["properties"]["stakeholder_id"]["type"] == "string"
    assert schema["properties"]["channel"]["type"] == "string"
    assert schema["properties"]["tone"]["type"] == "string"
    assert schema["properties"]["step_number"]["type"] == "integer"
    assert schema["properties"]["account_context"]["type"] == "object"
    assert schema["properties"]["stakeholder_context"]["type"] == "object"


async def test_adjust_tone_schema(server):
    """adjust_tone must require message_id and new_tone."""
    tools = await server.list_tools()
    tool = next(t for t in tools if t.name == "adjust_tone")
    schema = tool.inputSchema

    assert schema["type"] == "object"
    assert set(schema["required"]) == {"message_id", "new_tone"}
    assert schema["properties"]["message_id"]["type"] == "string"
    assert schema["properties"]["new_tone"]["type"] == "string"


async def test_tools_have_descriptions(server):
    """Every tool must have a non-empty description."""
    tools = await server.list_tools()
    for tool in tools:
        assert tool.description, f"Tool '{tool.name}' has no description"


# ---------------------------------------------------------------------------
# Resource listing tests
# ---------------------------------------------------------------------------


async def test_list_resources_returns_detail_and_preview(server):
    """list_resources() must return message://detail and message://preview."""
    resources = await server.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "message://detail/{message_id}" in uris
    assert "message://preview/{account_id}/{stakeholder_id}/{channel}/{tone}" in uris


async def test_resources_have_json_mime(server):
    """All resources should declare application/json mimeType."""
    resources = await server.list_resources()
    for resource in resources:
        assert resource.mimeType == "application/json"


# ---------------------------------------------------------------------------
# Round-trip call_tool tests
# ---------------------------------------------------------------------------


async def test_call_generate_message_invokes_handler(
    server, mock_handlers: dict[str, AsyncMock]
):
    """call_tool('generate_message', ...) must invoke the generate handler
    with both the command and context dicts."""
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = json.dumps(
        {"message_id": "msg-1", "body": "Hello!"}
    )
    mock_handlers["generate_handler"].execute.return_value = mock_result

    arguments = {
        "account_id": "acc-1",
        "stakeholder_id": "sh-1",
        "channel": "EMAIL",
        "tone": "PROFESSIONAL_CONSULTANT",
        "step_number": 1,
        "account_context": {"company_name": "TestCo"},
        "stakeholder_context": {"stakeholder_name": "Jane"},
    }
    result = await server.call_tool("generate_message", arguments)

    mock_handlers["generate_handler"].execute.assert_awaited_once()
    call_args = mock_handlers["generate_handler"].execute.call_args
    cmd = call_args[0][0]
    assert cmd.account_id == "acc-1"
    assert cmd.stakeholder_id == "sh-1"
    assert cmd.channel == "EMAIL"
    assert cmd.tone == "PROFESSIONAL_CONSULTANT"
    assert cmd.step_number == 1
    # Verify cross-BC context was passed
    assert call_args.kwargs["account_context"] == {"company_name": "TestCo"}
    assert call_args.kwargs["stakeholder_context"] == {"stakeholder_name": "Jane"}

    assert len(result) == 1
    payload = json.loads(result[0].text)
    assert payload["message_id"] == "msg-1"


async def test_call_adjust_tone_invokes_handler(
    server, mock_handlers: dict[str, AsyncMock]
):
    """call_tool('adjust_tone', ...) must invoke the adjust_tone handler."""
    mock_result = MagicMock()
    mock_result.model_dump_json.return_value = json.dumps({"status": "adjusted"})
    mock_handlers["adjust_tone_handler"].execute.return_value = mock_result

    result = await server.call_tool(
        "adjust_tone",
        {"message_id": "msg-1", "new_tone": "WITTY_TECH_PARTNER"},
    )

    mock_handlers["adjust_tone_handler"].execute.assert_awaited_once()
    cmd = mock_handlers["adjust_tone_handler"].execute.call_args[0][0]
    assert cmd.message_id == "msg-1"
    assert cmd.new_tone == "WITTY_TECH_PARTNER"
    assert len(result) == 1


async def test_call_unknown_tool_raises(server):
    """Calling an unknown tool name must raise ValueError."""
    with pytest.raises(ValueError, match="Unknown tool"):
        await server.call_tool("nonexistent_tool", {})
