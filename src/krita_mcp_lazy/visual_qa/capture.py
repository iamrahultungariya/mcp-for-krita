"""Canvas preview capture, thumbnail rendering, and visual region extraction."""

from typing import Any, Dict, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError, check_job_response
from krita_mcp_lazy.transport.client import AsyncIPCClient


class VisualCaptureService:
    """Manages full canvas previews, thumbnail exports, and localized region extraction."""

    def __init__(self, client: Optional[AsyncIPCClient] = None) -> None:
        self.client = client or AsyncIPCClient()

    async def capture_canvas(
        self,
        doc_id: str,
        max_dimension: int = 1920,
        format: str = "PNG",
    ) -> Dict[str, Any]:
        """Capture the current composite projection of the canvas as base64 encoded image data."""
        payload = {
            "doc_id": doc_id,
            "max_dimension": max_dimension,
            "format": format.upper(),
        }

        resp = await self.client.send_job("visual.capture_canvas", payload)
        return check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Canvas capture failed")

    async def extract_region(
        self,
        doc_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
        layer_id: Optional[str] = None,
        format: str = "PNG",
    ) -> Dict[str, Any]:
        """Extract a bounding-box crop of the canvas or a specific layer for detailed inspection."""
        payload = {
            "doc_id": doc_id,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "layer_id": layer_id,
            "format": format.upper(),
        }

        resp = await self.client.send_job("visual.extract_region", payload)
        return check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Region extraction failed")
