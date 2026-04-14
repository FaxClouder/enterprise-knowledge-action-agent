from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.config import Settings, get_settings

LOGGER = logging.getLogger(__name__)


class MCPClientManager:
    """MCP client wrapper with safe fallback behavior."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._adapter_client = None

    def is_external_configured(self) -> bool:
        """Check whether external MCP server command is configured."""
        return bool(self.settings.mcp_server_command)

    async def _create_adapter_client(self):
        if self._adapter_client is not None:
            return self._adapter_client

        if not self.is_external_configured():
            return None

        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient

            args = [arg for arg in self.settings.mcp_server_args.split(" ") if arg]
            self._adapter_client = MultiServerMCPClient(
                {
                    self.settings.mcp_server_name: {
                        "transport": "stdio",
                        "command": self.settings.mcp_server_command,
                        "args": args,
                    }
                }
            )
            return self._adapter_client
        except Exception as exc:
            LOGGER.warning("MCP adapter unavailable, fallback enabled: %s", exc)
            return None

    async def _get_tools_async(self) -> list[Any]:
        client = await self._create_adapter_client()
        if client is None:
            return []

        try:
            tools = await client.get_tools()
            return tools
        except Exception as exc:
            LOGGER.warning("Failed to load MCP tools: %s", exc)
            return []

    def get_langchain_tools(self) -> list[Any]:
        """Expose MCP tools in LangChain tool format when available."""
        try:
            return asyncio.run(self._get_tools_async())
        except RuntimeError:
            return []

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call MCP tool in fallback-safe mode."""
        return {
            "status": "fallback",
            "tool": tool_name,
            "arguments": arguments,
            "message": "External MCP call not executed in current runtime; fallback path used.",
        }


_MANAGER: MCPClientManager | None = None


def get_mcp_manager(settings: Settings | None = None) -> MCPClientManager:
    """Return singleton MCP manager."""
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = MCPClientManager(settings or get_settings())
    return _MANAGER
