from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from app.config import get_settings
from app.mcp.clients import get_mcp_manager
from app.mcp.resources import get_resource_service
from app.memory.long_term import get_long_term_store


@tool
def summarize_text(text: str, max_sentences: int = 4) -> str:
    """Summarize long text into a compact paragraph."""
    if not text.strip():
        return "No text provided."
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    selected = sentences[: max(1, min(max_sentences, 8))]
    return ". ".join(selected) + ("." if selected else "")


@tool
def search_kb_metadata(keyword: str) -> str:
    """Search only metadata (file names) from local knowledge base."""
    settings = get_settings()
    if not keyword.strip():
        return "keyword is empty"
    matches = []
    for path in settings.kb_dir.rglob("*"):
        if path.is_file() and keyword.lower() in path.name.lower():
            matches.append(path.name)
    if not matches:
        return "No metadata matched."
    return "Matched files: " + ", ".join(sorted(matches)[:20])


@tool
def read_user_preferences(user_id: str) -> str:
    """Read structured user preferences from long-term memory store."""
    memory = get_long_term_store().get_user_memory(user_id)
    return json.dumps(memory.preferences.model_dump(), ensure_ascii=False)


@tool
def read_mcp_resource(uri: str) -> str:
    """Read an external MCP resource in read-only mode."""
    result = get_resource_service().read_resource(uri)
    return json.dumps(result, ensure_ascii=False)


@tool
def call_mcp_tool(tool_name: str, arguments_json: str = "{}") -> str:
    """Call an MCP tool through safe wrapper with fallback behavior."""
    try:
        arguments: dict[str, Any] = json.loads(arguments_json)
    except json.JSONDecodeError:
        arguments = {}
    result = get_mcp_manager().call_tool(tool_name, arguments)
    return json.dumps(result, ensure_ascii=False)


def get_local_tools() -> list:
    """Return built-in tool list."""
    return [
        summarize_text,
        search_kb_metadata,
        read_user_preferences,
        read_mcp_resource,
        call_mcp_tool,
    ]


def get_all_tools() -> list:
    """Return local tools plus externally imported MCP tools (if available)."""
    tools = list(get_local_tools())
    tools.extend(get_mcp_manager().get_langchain_tools())
    return tools
