"""MCP tools for character turnaround sheets, anatomical proportions, expressions, and visemes."""

from typing import Any, Dict, List, Optional

from krita_mcp_lazy.character.expressions import (
    EmotionType,
    FacialExpressionEngine,
    VisemeType,
)
from krita_mcp_lazy.character.models import CharacterSheetSpec, ViewAngle
from krita_mcp_lazy.character.turnaround import CharacterTurnaroundEngine
from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.transport.client import AsyncIPCClient

_character_engine: Optional[CharacterTurnaroundEngine] = None
_expression_engine: Optional[FacialExpressionEngine] = None


def get_character_engine(config: Optional[KritaConfig] = None) -> CharacterTurnaroundEngine:
    """Retrieve or initialize singleton CharacterTurnaroundEngine."""
    global _character_engine
    if _character_engine is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _character_engine = CharacterTurnaroundEngine(client=client)
    return _character_engine


def get_expression_engine(config: Optional[KritaConfig] = None) -> FacialExpressionEngine:
    """Retrieve or initialize singleton FacialExpressionEngine."""
    global _expression_engine
    if _expression_engine is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _expression_engine = FacialExpressionEngine(client=client)
    return _expression_engine


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

    @server.tool(
        name="krita_create_expression_sheet",
        description="Scaffold an emotional variation matrix with dedicated Eyes, Brows, and Mouth sub-layers",
    )
    async def _tool_create_expression_sheet(
        doc_id: str,
        character_name: str = "Character",
        emotions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        engine = get_expression_engine(cfg)
        emotion_enums: List[EmotionType] = []
        if emotions:
            for e in emotions:
                try:
                    emotion_enums.append(EmotionType(e.lower()))
                except ValueError:
                    pass
        if not emotion_enums:
            emotion_enums = [
                EmotionType.NEUTRAL,
                EmotionType.HAPPY,
                EmotionType.ANGRY,
                EmotionType.SAD,
                EmotionType.SHOCKED,
                EmotionType.SCARED,
            ]
        return await engine.create_expression_matrix(
            doc_id=doc_id,
            character_name=character_name,
            emotions=emotion_enums,
        )

    @server.tool(
        name="krita_generate_viseme_set",
        description="Generate lip-sync mouth shape layers (REST, AI, E, O, U, MBP, FV, LNTD) for animation",
    )
    async def _tool_generate_viseme_set(
        doc_id: str,
        character_name: str = "Character",
        visemes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        engine = get_expression_engine(cfg)
        viseme_enums: List[VisemeType] = []
        if visemes:
            for v in visemes:
                try:
                    viseme_enums.append(VisemeType(v.lower()))
                except ValueError:
                    pass
        if not viseme_enums:
            viseme_enums = [
                VisemeType.REST,
                VisemeType.AI,
                VisemeType.E,
                VisemeType.O,
                VisemeType.U,
                VisemeType.MBP,
                VisemeType.FV,
                VisemeType.LNTD,
            ]
        return await engine.generate_viseme_set(
            doc_id=doc_id,
            character_name=character_name,
            visemes=viseme_enums,
        )
