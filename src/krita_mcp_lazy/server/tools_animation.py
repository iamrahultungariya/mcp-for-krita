"""MCP tools for raster keyframing, timeline configuration, and onion skinning."""

from typing import Any, Dict, Optional

from krita_mcp_lazy.animation.keyframe_service import KeyframeService
from krita_mcp_lazy.animation.models import KeyframeType, OnionSkinConfig
from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.transport.client import AsyncIPCClient

_keyframe_service: Optional[KeyframeService] = None


def get_keyframe_service(config: Optional[KritaConfig] = None) -> KeyframeService:
    """Retrieve or initialize singleton KeyframeService."""
    global _keyframe_service
    if _keyframe_service is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _keyframe_service = KeyframeService(client=client)
    return _keyframe_service


def register_animation_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all animation, keyframing, and timeline tools on the MCP server."""
    cfg = config or KritaConfig()

    @server.tool(
        name="krita_create_keyframe",
        description="Insert a blank or duplicate raster keyframe on the active layer timeline",
    )
    async def _tool_create_keyframe(
        doc_id: str,
        layer_id: str,
        frame_index: int,
        keyframe_type: str = "blank",
    ) -> Dict[str, Any]:
        svc = get_keyframe_service(cfg)
        try:
            kt_enum = KeyframeType(keyframe_type.lower())
        except ValueError:
            kt_enum = KeyframeType.BLANK

        return await svc.create_keyframe(
            doc_id=doc_id,
            layer_id=layer_id,
            frame_index=frame_index,
            keyframe_type=kt_enum,
        )

    @server.tool(
        name="krita_configure_onion_skin",
        description="Configure onion skin overlays (red for previous frames, green for future frames) on active animation layer",
    )
    async def _tool_configure_onion_skin(
        doc_id: str,
        layer_id: str,
        tint_previous: str = "#ff0000",
        tint_future: str = "#00ff00",
        prev_frames: int = 2,
        next_frames: int = 2,
        opacity: float = 0.5,
    ) -> Dict[str, Any]:
        svc = get_keyframe_service(cfg)
        config_obj = OnionSkinConfig(
            tint_previous=tint_previous,
            tint_future=tint_future,
            prev_frames=prev_frames,
            next_frames=next_frames,
            opacity=opacity,
        )
        return await svc.configure_onion_skin(
            doc_id=doc_id,
            layer_id=layer_id,
            config=config_obj,
        )

    @server.tool(
        name="krita_set_frame_timing",
        description="Set animation timeline frame rate (e.g. 24 fps) and total playback frame count",
    )
    async def _tool_set_frame_timing(
        doc_id: str,
        fps: int = 24,
        total_frames: int = 24,
    ) -> Dict[str, Any]:
        svc = get_keyframe_service(cfg)
        return await svc.set_frame_timing(
            doc_id=doc_id,
            fps=fps,
            total_frames=total_frames,
        )
