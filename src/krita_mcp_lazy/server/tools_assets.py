"""MCP tools for modular prop creation, material shading layers, and asset kits."""

from typing import Any, Dict, List, Optional

from krita_mcp_lazy.assets.models import MaterialType
from krita_mcp_lazy.assets.prop_engine import PropEngine
from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.transport.client import AsyncIPCClient

_prop_engine: Optional[PropEngine] = None


def get_prop_engine(config: Optional[KritaConfig] = None) -> PropEngine:
    """Retrieve or initialize singleton PropEngine."""
    global _prop_engine
    if _prop_engine is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _prop_engine = PropEngine(client=client)
    return _prop_engine


def register_assets_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all modular prop and material shading tools on the MCP server."""
    cfg = config or KritaConfig()

    @server.tool(
        name="krita_create_prop_asset",
        description="Scaffold a modular prop group with line art and material-specific shading layers (wood, metal, fabric, glass, stone, skin, water)",
    )
    async def _tool_create_prop_asset(
        doc_id: str,
        prop_name: str,
        material: str = "wood",
        category: str = "General",
        bounding_box: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        engine = get_prop_engine(cfg)
        try:
            mat_enum = MaterialType(material.lower())
        except ValueError:
            mat_enum = MaterialType.WOOD

        return await engine.create_prop_asset(
            doc_id=doc_id,
            prop_name=prop_name,
            material=mat_enum,
            category=category,
            bounding_box=bounding_box,
        )

    @server.tool(
        name="krita_apply_material_shading",
        description="Apply material shading layer structure (Base, Shading, Highlights, Reflection) to an existing prop group",
    )
    async def _tool_apply_material_shading(
        doc_id: str,
        prop_group_id: str,
        material: str = "wood",
    ) -> Dict[str, Any]:
        engine = get_prop_engine(cfg)
        try:
            mat_enum = MaterialType(material.lower())
        except ValueError:
            mat_enum = MaterialType.WOOD

        return await engine.setup_material_layers(
            doc_id=doc_id,
            prop_group_id=prop_group_id,
            material=mat_enum,
        )
