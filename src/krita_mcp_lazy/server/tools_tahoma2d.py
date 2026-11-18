"""MCP tools for Tahoma2D puppet asset packaging, pivot metadata, and scene generation."""

import json
import os
from typing import Any, Dict, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.interop_tahoma2d.packager import AssetPackager
from krita_mcp_lazy.interop_tahoma2d.scene_builder import Tahoma2DSceneBuilder
from krita_mcp_lazy.transport.client import AsyncIPCClient

_packager: Optional[AssetPackager] = None
_scene_builder: Optional[Tahoma2DSceneBuilder] = None


def get_asset_packager(config: Optional[KritaConfig] = None) -> AssetPackager:
    """Retrieve or initialize singleton AssetPackager."""
    global _packager
    if _packager is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _packager = AssetPackager(client=client)
    return _packager


def get_scene_builder() -> Tahoma2DSceneBuilder:
    """Retrieve singleton Tahoma2DSceneBuilder."""
    global _scene_builder
    if _scene_builder is None:
        _scene_builder = Tahoma2DSceneBuilder()
    return _scene_builder


def register_tahoma2d_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all Tahoma2D interop tools on the MCP server."""
    cfg = config or KritaConfig()

    @server.tool(
        name="krita_package_tahoma2d_assets",
        description="Slice character layer parts into transparent PNGs with pivot coordinates and JSON manifest for Tahoma2D rigging",
    )
    async def _tool_package_tahoma2d_assets(
        doc_id: str,
        character_group: str,
        output_dir: str,
    ) -> Dict[str, Any]:
        packager = get_asset_packager(cfg)
        return await packager.package_character_cutout(
            doc_id=doc_id,
            character_group=character_group,
            output_dir=output_dir,
        )

    @server.tool(
        name="krita_build_tahoma2d_scene",
        description="Generate a complete Tahoma2D .tnz scene project XML mapping cutout parts to columns and pegbars",
    )
    async def _tool_build_tahoma2d_scene(
        manifest: Dict[str, Any],
        output_dir: str,
        scene_name: str = "scene",
    ) -> Dict[str, Any]:
        builder = get_scene_builder()
        tnz_path = builder.generate_scene_xml(
            manifest=manifest,
            output_dir=output_dir,
            scene_name=scene_name,
        )
        return {"scene_path": tnz_path, "status": "created"}

    @server.tool(
        name="krita_verify_tahoma2d_roundtrip",
        description="Verify Tahoma2D .tnz scene XML integrity, part alignments, and column structures",
    )
    async def _tool_verify_tahoma2d_roundtrip(
        manifest: Dict[str, Any],
        tnz_path: str,
    ) -> Dict[str, Any]:
        builder = get_scene_builder()
        return builder.verify_roundtrip(manifest=manifest, tnz_path=tnz_path)
