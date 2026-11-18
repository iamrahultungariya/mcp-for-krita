"""MCP tools for Krita brush discovery, preset selection, and parameter configuration."""

from typing import Any, List, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.painting.brush_service import BrushService
from krita_mcp_lazy.painting.models import BrushConfig
from krita_mcp_lazy.transport.client import AsyncIPCClient

_brush_service: Optional[BrushService] = None


def get_brush_service(config: Optional[KritaConfig] = None) -> BrushService:
    """Retrieve or initialize singleton BrushService instance."""
    global _brush_service
    if _brush_service is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _brush_service = BrushService(client=client)
    return _brush_service


def register_painting_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all brush preset and parameter configuration tools on the MCP server."""
    cfg = config or KritaConfig()

    @server.tool(
        name="krita_list_brush_presets",
        description="List installed Krita brush presets filtered by optional category (e.g. Basic, Pencil, Ink, Airbrush)",
    )
    async def _tool_list_brush_presets(category: Optional[str] = None) -> List[dict[str, Any]]:
        svc = get_brush_service(cfg)
        return await svc.list_presets(category=category)

    @server.tool(
        name="krita_select_brush_preset",
        description="Select and activate a specific brush preset by name in Krita",
    )
    async def _tool_select_brush_preset(preset_name: str) -> dict[str, Any]:
        svc = get_brush_service(cfg)
        return await svc.select_preset(preset_name=preset_name)

    @server.tool(
        name="krita_configure_brush",
        description="Configure diameter size (px), opacity, flow rate, and foreground/background colors",
    )
    async def _tool_configure_brush(
        size: Optional[float] = None,
        opacity: Optional[float] = None,
        flow: Optional[float] = None,
        color: Optional[str] = None,
        background_color: Optional[str] = None,
    ) -> dict[str, Any]:
        svc = get_brush_service(cfg)
        # Fetch current brush values to fill in defaults
        curr = await svc.get_current_brush()
        b_config = BrushConfig(
            size=size if size is not None else curr.get("size", 10.0),
            opacity=opacity if opacity is not None else curr.get("opacity", 1.0),
            flow=flow if flow is not None else curr.get("flow", 1.0),
            color=color if color is not None else curr.get("color", "#000000"),
            background_color=background_color if background_color is not None else curr.get("background_color", "#ffffff"),
        )
        return await svc.configure_brush(b_config)

    @server.tool(
        name="krita_get_current_brush",
        description="Query the active brush preset, size, opacity, and color parameters",
    )
    async def _tool_get_current_brush() -> dict[str, Any]:
        svc = get_brush_service(cfg)
        return await svc.get_current_brush()
