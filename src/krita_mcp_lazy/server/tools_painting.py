"""MCP tools for Krita brush discovery, preset selection, parameter configuration, and native stroke drawing."""

from typing import Any, List, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.painting.brush_service import BrushService
from krita_mcp_lazy.painting.models import BrushConfig
from krita_mcp_lazy.painting.stroke_engine import StrokeEngine, StrokePoint
from krita_mcp_lazy.transport.client import AsyncIPCClient

_brush_service: Optional[BrushService] = None
_stroke_engine: Optional[StrokeEngine] = None


def get_brush_service(config: Optional[KritaConfig] = None) -> BrushService:
    """Retrieve or initialize singleton BrushService instance."""
    global _brush_service
    if _brush_service is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _brush_service = BrushService(client=client)
    return _brush_service


def get_stroke_engine(config: Optional[KritaConfig] = None) -> StrokeEngine:
    """Retrieve or initialize singleton StrokeEngine instance."""
    global _stroke_engine
    if _stroke_engine is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _stroke_engine = StrokeEngine(client=client)
    return _stroke_engine


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

    @server.tool(
        name="krita_paint_stroke",
        description="Paint a native pressure-sensitive stroke using a sequence of points with coordinates and pressure",
    )
    async def _tool_paint_stroke(
        doc_id: str,
        layer_id: str,
        points: List[dict[str, Any]],
        brush_preset: Optional[str] = None,
        color: Optional[str] = None,
        opacity: Optional[float] = None,
        size: Optional[float] = None,
    ) -> dict[str, Any]:
        engine = get_stroke_engine(cfg)
        stroke_points = [
            StrokePoint(
                x=float(p["x"]),
                y=float(p["y"]),
                pressure=float(p.get("pressure", 0.5)),
                tilt_x=float(p.get("tilt_x", 0.0)),
                tilt_y=float(p.get("tilt_y", 0.0)),
                time_offset_ms=p.get("time_offset_ms"),
            )
            for p in points
        ]
        return await engine.draw_stroke(
            doc_id=doc_id,
            layer_id=layer_id,
            points=stroke_points,
            brush_preset=brush_preset,
            color=color,
            opacity=opacity,
            size=size,
        )

    @server.tool(
        name="krita_paint_bezier_curve",
        description="Paint a smooth cubic Bézier curve with pressure taper and dynamic inking profile",
    )
    async def _tool_paint_bezier_curve(
        doc_id: str,
        layer_id: str,
        start_x: float,
        start_y: float,
        control1_x: float,
        control1_y: float,
        control2_x: float,
        control2_y: float,
        end_x: float,
        end_y: float,
        start_pressure: float = 0.2,
        end_pressure: float = 0.2,
        steps: int = 20,
        taper: bool = True,
        brush_preset: Optional[str] = None,
        color: Optional[str] = None,
        opacity: Optional[float] = None,
        size: Optional[float] = None,
    ) -> dict[str, Any]:
        engine = get_stroke_engine(cfg)
        start = StrokePoint(x=start_x, y=start_y, pressure=start_pressure)
        end = StrokePoint(x=end_x, y=end_y, pressure=end_pressure)
        return await engine.draw_bezier_curve(
            doc_id=doc_id,
            layer_id=layer_id,
            start=start,
            control1=(control1_x, control1_y),
            control2=(control2_x, control2_y),
            end=end,
            steps=steps,
            taper=taper,
            brush_preset=brush_preset,
            color=color,
            opacity=opacity,
            size=size,
        )
