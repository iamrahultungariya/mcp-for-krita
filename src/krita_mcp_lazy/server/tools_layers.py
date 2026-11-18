"""MCP tools for Krita layer hierarchy management, manipulation, and masking."""

from typing import Any, Dict, List, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.layers.masks import MaskService, MaskType
from krita_mcp_lazy.layers.models import BlendingMode, LayerSpec, LayerType, ReorderPosition
from krita_mcp_lazy.layers.semantic import SemanticLayerOrganizer
from krita_mcp_lazy.layers.service import LayerService
from krita_mcp_lazy.transport.client import AsyncIPCClient

_layer_service: Optional[LayerService] = None
_mask_service: Optional[MaskService] = None
_semantic_organizer: Optional[SemanticLayerOrganizer] = None


def get_layer_service(config: Optional[KritaConfig] = None) -> LayerService:
    """Retrieve or initialize singleton LayerService instance."""
    global _layer_service
    if _layer_service is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _layer_service = LayerService(client=client)
    return _layer_service


def get_mask_service(config: Optional[KritaConfig] = None) -> MaskService:
    """Retrieve or initialize singleton MaskService instance."""
    global _mask_service
    if _mask_service is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _mask_service = MaskService(client=client)
    return _mask_service


def get_semantic_organizer(config: Optional[KritaConfig] = None) -> SemanticLayerOrganizer:
    """Retrieve or initialize singleton SemanticLayerOrganizer instance."""
    global _semantic_organizer
    if _semantic_organizer is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _semantic_organizer = SemanticLayerOrganizer(client=client)
    return _semantic_organizer


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

    # --- Masks & Alpha Inheritance ---

    @server.tool(
        name="krita_add_mask",
        description="Add a non-destructive transparency, filter, or transform mask to a target layer",
    )
    async def _tool_add_mask(
        doc_id: str,
        layer_id: str,
        mask_type: str = "transparency",
        name: str = "Mask",
        filter_config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        svc = get_mask_service(cfg)
        return await svc.add_mask(
            doc_id=doc_id,
            layer_id=layer_id,
            mask_type=MaskType(mask_type.lower()),
            name=name,
            filter_config=filter_config,
        )

    @server.tool(
        name="krita_remove_mask",
        description="Remove a mask from its parent layer in Krita",
    )
    async def _tool_remove_mask(doc_id: str, mask_id: str) -> dict[str, Any]:
        svc = get_mask_service(cfg)
        return await svc.remove_mask(doc_id=doc_id, mask_id=mask_id)

    @server.tool(
        name="krita_set_alpha_inheritance",
        description="Enable or disable alpha inheritance (clipping mask behavior) on target layer",
    )
    async def _tool_set_alpha_inheritance(
        doc_id: str,
        layer_id: str,
        inherit_alpha: bool = True,
    ) -> dict[str, Any]:
        svc = get_mask_service(cfg)
        return await svc.set_alpha_inheritance(
            doc_id=doc_id,
            layer_id=layer_id,
            inherit_alpha=inherit_alpha,
        )

    @server.tool(
        name="krita_list_masks",
        description="List all masks attached to a specified layer",
    )
    async def _tool_list_masks(doc_id: str, layer_id: str) -> List[dict[str, Any]]:
        svc = get_mask_service(cfg)
        return await svc.list_masks(doc_id=doc_id, layer_id=layer_id)

    @server.tool(
        name="krita_scaffold_semantic_structure",
        description="Scaffold an organized semantic layer and group hierarchy from an archetype preset or custom schema",
    )
    async def _tool_scaffold_semantic_structure(
        doc_id: str,
        preset: Optional[str] = None,
        custom_schema: Optional[Dict[str, Any]] = None,
    ) -> dict[str, Any]:
        organizer = get_semantic_organizer(cfg)
        return await organizer.scaffold_hierarchy(
            doc_id=doc_id,
            schema=custom_schema,
            preset=preset,
        )
