"""Brush service discovering presets and configuring parameters over loopback IPC."""

import logging
from typing import Any, List, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobStatus
from krita_mcp_lazy.painting.models import BrushConfig
from krita_mcp_lazy.transport.client import AsyncIPCClient

logger = logging.getLogger(__name__)


class BrushService:
    """Orchestrates brush preset discovery, selection, size, opacity, and color configuration."""

    def __init__(self, client: AsyncIPCClient) -> None:
        self.client = client

    def _ensure_success(self, resp: Any, default_message: str) -> dict[str, Any]:
        """Validate response status or raise KritaError with proper taxonomy code."""
        if resp.status != JobStatus.SUCCESS:
            code = ErrorCode.PAINT_ERROR
            if resp.error_code:
                for member in ErrorCode:
                    if member.value == resp.error_code:
                        code = member
                        break
            raise KritaError(
                code=code,
                message=resp.error or default_message,
                job_id=resp.job_id,
            )
        return resp.result or {}

    async def list_presets(self, category: Optional[str] = None) -> List[dict[str, Any]]:
        """List available Krita brush presets filtered by optional category tag."""
        params = {"category": category} if category else {}
        req = JobRequest(action="brush.list_presets", params=params)
        resp = await self.client.send_job(req)
        result = self._ensure_success(resp, "Failed to list brush presets")
        return result.get("presets", [])

    async def select_preset(self, preset_name: str) -> dict[str, Any]:
        """Activate the specified brush preset in Krita."""
        params = {"preset_name": preset_name}
        req = JobRequest(action="brush.select_preset", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to select brush preset '{preset_name}'")

    async def configure_brush(self, config: BrushConfig) -> dict[str, Any]:
        """Apply size, opacity, flow, and color settings to the active brush."""
        params = config.model_dump()
        req = JobRequest(action="brush.configure", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, "Failed to configure active brush")

    async def get_current_brush(self) -> dict[str, Any]:
        """Query currently active brush preset and runtime parameters."""
        req = JobRequest(action="brush.current", params={})
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, "Failed to retrieve active brush configuration")
