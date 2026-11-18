"""MCP tools for character turnaround sheets, anatomical proportions, and consistency verification."""

from typing import Any, Dict, List, Optional

from krita_mcp_lazy.character.models import CharacterSheetSpec, ViewAngle
from krita_mcp_lazy.character.turnaround import CharacterTurnaroundEngine
from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.transport.client import AsyncIPCClient

_character_engine: Optional[CharacterTurnaroundEngine] = None


def get_character_engine(config: Optional[KritaConfig] = None) -> CharacterTurnaroundEngine:
    """Retrieve or initialize singleton CharacterTurnaroundEngine."""
    global _character_engine
    if _character_engine is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _character_engine = CharacterTurnaroundEngine(client=client)
    return _character_engine


def register_character_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all character production tools on the MCP server."""
    cfg = config or KritaConfig()

    @server.tool(
        name="krita_create_character_turnaround",
        description="Scaffold a multi-view character turnaround sheet with anatomical head-height guides and view groups",
    )
    async def _tool_create_character_turnaround(
        doc_id: str,
        character_name: str,
        head_height_ratio: float = 7.5,
        views: Optional[List[str]] = None,
        clothing_tokens: Optional[List[str]] = None,
        color_tokens: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        engine = get_character_engine(cfg)
        view_enums: List[ViewAngle] = []
        if views:
            for v in views:
                try:
                    view_enums.append(ViewAngle(v.lower()))
                except ValueError:
                    pass
        if not view_enums:
            view_enums = [ViewAngle.FRONT, ViewAngle.THREE_QUARTER, ViewAngle.SIDE, ViewAngle.BACK]

        spec = CharacterSheetSpec(
            character_name=character_name,
            head_height_ratio=head_height_ratio,
            views=view_enums,
            clothing_tokens=clothing_tokens or [],
            color_tokens=color_tokens or {},
        )
        return await engine.setup_turnaround_canvases(doc_id=doc_id, spec=spec)

    @server.tool(
        name="krita_verify_character_consistency",
        description="Verify anatomical alignment, eye lines, height ratio, and landmark consistency across turnaround views",
    )
    async def _tool_verify_character_consistency(
        doc_id: str,
        character_name: str,
        views: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        engine = get_character_engine(cfg)
        view_enums: List[ViewAngle] = []
        if views:
            for v in views:
                try:
                    view_enums.append(ViewAngle(v.lower()))
                except ValueError:
                    pass
        if not view_enums:
            view_enums = [ViewAngle.FRONT, ViewAngle.SIDE]

        return await engine.verify_character_consistency(
            doc_id=doc_id,
            character_name=character_name,
            views=view_enums,
        )
