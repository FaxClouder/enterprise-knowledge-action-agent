from __future__ import annotations

import json
from pathlib import Path

from app.config import Settings, get_settings


class MCPResourceService:
    """Resource reader that simulates external MCP resource consumption with fallback data."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._ensure_stub()

    def _ensure_stub(self) -> None:
        if self.settings.mcp_stub_file.exists():
            return
        payload = {
            "mcp://enterprise/sales_schema": {
                "title": "Sales Schema",
                "content": "Table sales_orders(order_id, order_date, amount, region, channel)."
            },
            "mcp://enterprise/ops_calendar": {
                "title": "Ops Calendar",
                "content": "Q2 release freeze starts at 2026-06-20 and ends at 2026-06-25."
            }
        }
        self.settings.mcp_stub_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def read_resource(self, uri: str) -> dict[str, str]:
        """Read resource content from local fallback store."""
        raw = self.settings.mcp_stub_file.read_text(encoding="utf-8")
        data = json.loads(raw)
        content = data.get(uri)
        if content:
            return {
                "status": "ok",
                "uri": uri,
                "title": content.get("title", "resource"),
                "content": content.get("content", ""),
            }
        return {
            "status": "not_found",
            "uri": uri,
            "title": "resource_not_found",
            "content": "No MCP resource available for the uri.",
        }


_SERVICE: MCPResourceService | None = None


def get_resource_service(settings: Settings | None = None) -> MCPResourceService:
    """Return singleton MCP resource service."""
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = MCPResourceService(settings or get_settings())
    return _SERVICE
