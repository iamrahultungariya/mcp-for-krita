"""MCP tools for Tahoma2D puppet asset packaging, pivot metadata, and scene generation."""

from typing import Any, Dict, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.interop_tahoma2d.packager import AssetPackager
from krita_mcp_lazy.transport.client import AsyncIPCClient

_packager: Optional[AssetPackager] = None


def get_asset_packager(config: Optional[KritaConfig] = None) -> AssetPackager:
    """Retrieve or initialize singleton AssetPackager."""
    global _packager
    if _packager is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _packager = AssetPackager(client=client)
    return _packager


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
