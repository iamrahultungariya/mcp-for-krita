"""Canvas preview capture, thumbnail rendering, and visual region extraction."""

from typing import Any, Dict, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
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
        if resp.status == "error":
            err_dict = resp.error or {}
            err_code = err_dict.get("code", "DOCUMENT_ERROR")
            try:
                code_enum = ErrorCode(err_code)
            except ValueError:
                code_enum = ErrorCode.DOCUMENT_ERROR
            raise KritaError(code_enum, err_dict.get("message", "Canvas capture failed"))

        return resp.result or {}

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
        if resp.status == "error":
            err_dict = resp.error or {}
            err_code = err_dict.get("code", "DOCUMENT_ERROR")
            try:
                code_enum = ErrorCode(err_code)
            except ValueError:
                code_enum = ErrorCode.DOCUMENT_ERROR
            raise KritaError(code_enum, err_dict.get("message", "Region extraction failed"))

        return resp.result or {}
