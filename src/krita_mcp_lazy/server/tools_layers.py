"""MCP tools for Krita layer hierarchy management and manipulation."""

from typing import Any, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.layers.models import BlendingMode, LayerSpec, LayerType, ReorderPosition
from krita_mcp_lazy.layers.service import LayerService
from krita_mcp_lazy.transport.client import AsyncIPCClient

_layer_service: Optional[LayerService] = None


def get_layer_service(config: Optional[KritaConfig] = None) -> LayerService:
    """Retrieve or initialize singleton LayerService instance."""
    global _layer_service
    if _layer_service is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _layer_service = LayerService(client=client)
    return _layer_service


def register_layer_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all layer hierarchy, grouping, and styling tools on the MCP server."""
    cfg = config or KritaConfig()

    @server.tool(
        name="krita_create_layer",
        description="Create a new paint, group, vector, or adjustment layer with specified opacity and blending mode",
    )
    async def _tool_create_layer(
        doc_id: str,
        name: str,
        type: str = "paint",
        opacity: int = 255,
        blending_mode: str = "normal",
        visible: bool = True,
        locked: bool = False,
        parent_group: Optional[str] = None,
    ) -> dict[str, Any]:
        svc = get_layer_service(cfg)
        spec = LayerSpec(
            name=name,
            type=LayerType(type.lower()),
            opacity=opacity,
            blending_mode=BlendingMode(blending_mode.lower()),
            visible=visible,
            locked=locked,
            parent_group=parent_group,
        )
        return await svc.create_layer(doc_id=doc_id, spec=spec)

    @server.tool(
        name="krita_delete_layer",
        description="Delete a layer or group from the specified document",
    )
    async def _tool_delete_layer(doc_id: str, layer_name: str) -> dict[str, Any]:
        svc = get_layer_service(cfg)
        return await svc.delete_layer(doc_id=doc_id, layer_name=layer_name)

    @server.tool(
        name="krita_reorder_layer",
        description="Reorder a target layer relative to a reference layer (above, below, inside)",
    )
    async def _tool_reorder_layer(
        doc_id: str,
        target_layer: str,
        reference_layer: str,
        position: str = "above",
    ) -> dict[str, Any]:
        svc = get_layer_service(cfg)
        return await svc.reorder_layer(
            doc_id=doc_id,
            target_layer=target_layer,
            reference_layer=reference_layer,
            position=ReorderPosition(position.lower()),
        )

    @server.tool(
        name="krita_inspect_layer_tree",
        description="Inspect the full layer tree hierarchy, groups, visibility, opacity, and blending modes",
    )
    async def _tool_inspect_layer_tree(doc_id: Optional[str] = None) -> dict[str, Any]:
        svc = get_layer_service(cfg)
        return await svc.inspect_layer_tree(doc_id=doc_id)

    @server.tool(
        name="krita_set_layer_properties",
        description="Update opacity (0-255), visibility, lock status, or blending mode of an existing layer",
    )
    async def _tool_set_layer_properties(
        doc_id: str,
        layer_name: str,
        opacity: Optional[int] = None,
        visible: Optional[bool] = None,
        locked: Optional[bool] = None,
        blending_mode: Optional[str] = None,
    ) -> dict[str, Any]:
        svc = get_layer_service(cfg)
        return await svc.set_layer_properties(
            doc_id=doc_id,
            layer_name=layer_name,
            opacity=opacity,
            visible=visible,
            locked=locked,
            blending_mode=blending_mode,
        )

    @server.tool(
        name="krita_set_active_layer",
        description="Set a layer as the active painting node in Krita",
    )
    async def _tool_set_active_layer(doc_id: str, layer_name: str) -> dict[str, Any]:
        svc = get_layer_service(cfg)
        return await svc.set_active_layer(doc_id=doc_id, layer_name=layer_name)
