"""MCP tools for perspective grid generation, vanishing point calculation, and depth planes."""

from typing import Any, Dict, List, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.environment.models import PerspectiveType
from krita_mcp_lazy.environment.perspective import PerspectiveGridEngine
from krita_mcp_lazy.transport.client import AsyncIPCClient

_environment_engine: Optional[PerspectiveGridEngine] = None


def get_environment_engine(config: Optional[KritaConfig] = None) -> PerspectiveGridEngine:
    """Retrieve or initialize singleton PerspectiveGridEngine."""
    global _environment_engine
    if _environment_engine is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _environment_engine = PerspectiveGridEngine(client=client)
    return _environment_engine


def register_environment_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all environment and perspective tools on the MCP server."""
    cfg = config or KritaConfig()

    @server.tool(
        name="krita_create_perspective_grid",
        description="Generate 1-point, 2-point, or 3-point perspective grid guides with vanishing points on horizon",
    )
    async def _tool_create_perspective_grid(
        doc_id: str,
        perspective_type: str = "two_point",
        horizon_y: float = 1080.0,
        vp1_x: Optional[float] = None,
        vp2_x: Optional[float] = None,
        vp3_y: Optional[float] = None,
        line_density: int = 12,
        opacity: float = 0.4,
        color: str = "#00aaff",
    ) -> Dict[str, Any]:
        engine = get_environment_engine(cfg)
        try:
            p_enum = PerspectiveType(perspective_type.lower())
        except ValueError:
            p_enum = PerspectiveType.TWO_POINT

        return await engine.create_grid(
            doc_id=doc_id,
            p_type=p_enum,
            horizon_y=horizon_y,
            vp1_x=vp1_x,
            vp2_x=vp2_x,
            vp3_y=vp3_y,
            line_density=line_density,
            opacity=opacity,
            color=color,
        )

    @server.tool(
        name="krita_setup_environment_depth_planes",
        description="Scaffold multi-plane environment depth groups (Sky, Far BG, Mid BG, Play Area, Near FG) with atmospheric hazing",
    )
    async def _tool_setup_environment_depth_planes(
        doc_id: str,
        planes: Optional[List[str]] = None,
        atmospheric_haze: bool = True,
    ) -> Dict[str, Any]:
        engine = get_environment_engine(cfg)
        return await engine.setup_environment_depth_planes(
            doc_id=doc_id,
            planes=planes,
            atmospheric_haze=atmospheric_haze,
        )
