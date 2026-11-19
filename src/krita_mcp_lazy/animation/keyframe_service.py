"""Raster keyframe management, timeline controls, onion skinning, and memory cache guard."""

from typing import Any, Dict, Optional

from krita_mcp_lazy.animation.models import KeyframeType, OnionSkinConfig
from krita_mcp_lazy.core.errors import ErrorCode, KritaError, check_job_response
from krita_mcp_lazy.transport.client import AsyncIPCClient


class KeyframeService:
    """Manages frame-by-frame animation keyframes, timeline fps, and RAM cache budgets."""

    def __init__(self, client: Optional[AsyncIPCClient] = None, max_cache_mb: float = 500.0) -> None:
        self.client = client or AsyncIPCClient()
        self.max_cache_mb = max_cache_mb

    async def create_keyframe(
        self,
        doc_id: str,
        layer_id: str,
        frame_index: int,
        keyframe_type: KeyframeType = KeyframeType.BLANK,
    ) -> Dict[str, Any]:
        """Create a blank or duplicated raster keyframe at the target timeline frame index."""
        payload = {
            "doc_id": doc_id,
            "layer_id": layer_id,
            "frame_index": frame_index,
            "keyframe_type": keyframe_type.value,
            "max_cache_mb": self.max_cache_mb,
        }

        resp = await self.client.send_job("animation.create_keyframe", payload)
        return check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Keyframe creation failed")

    async def configure_onion_skin(
        self,
        doc_id: str,
        layer_id: str,
        config: OnionSkinConfig,
    ) -> Dict[str, Any]:
        """Enable and configure colored onion skinning overlays on the active layer."""
        payload = {
            "doc_id": doc_id,
            "layer_id": layer_id,
            "tint_previous": config.tint_previous,
            "tint_future": config.tint_future,
            "prev_frames": config.prev_frames,
            "next_frames": config.next_frames,
            "opacity": config.opacity,
        }

        resp = await self.client.send_job("animation.configure_onion_skin", payload)
        return check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Onion skin configuration failed")

    async def set_frame_timing(
        self,
        doc_id: str,
        fps: int = 24,
        total_frames: int = 24,
    ) -> Dict[str, Any]:
        """Set the playback frame rate and timeline duration in frames."""
        payload = {
            "doc_id": doc_id,
            "fps": fps,
            "total_frames": total_frames,
        }

        resp = await self.client.send_job("animation.set_timing", payload)
        return check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Timeline timing setup failed")

        return resp.result or {}
