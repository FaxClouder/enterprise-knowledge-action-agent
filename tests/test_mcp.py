from __future__ import annotations

from app.mcp.resources import get_resource_service


def test_mcp_stub_resource_read() -> None:
    service = get_resource_service()
    payload = service.read_resource("mcp://enterprise/sales_schema")
    assert payload["status"] == "ok"
    assert "sales_orders" in payload["content"]
