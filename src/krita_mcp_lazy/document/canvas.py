"""Canvas geometric transformations and pixel sampling engine."""

import logging
from typing import Any, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobStatus
from krita_mcp_lazy.transport.client import AsyncIPCClient

logger = logging.getLogger(__name__)


class CanvasService:
    """Orchestrates canvas modifications: resize, crop, rotation, bounds, and pixel color sampling."""

    def __init__(self, client: AsyncIPCClient) -> None:
        self.client = client

    def _ensure_success(self, resp: Any, default_message: str) -> dict[str, Any]:
        """Validate response status or raise KritaError with proper taxonomy code."""
        if resp.status != JobStatus.SUCCESS:
            code = ErrorCode.DOCUMENT_ERROR
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

    async def resize_canvas(
        self,
        doc_id: str,
        width: int,
        height: int,
        x_offset: int = 0,
        y_offset: int = 0,
    ) -> dict[str, Any]:
        """Resize the canvas dimensions with optional coordinate offset / anchor."""
        req = JobRequest(
            action="canvas.resize",
            params={
                "doc_id": doc_id,
                "width": width,
                "height": height,
                "x_offset": x_offset,
                "y_offset": y_offset,
            },
        )
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to resize canvas for doc '{doc_id}'")

    async def crop_canvas(
        self,
        doc_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> dict[str, Any]:
        """Crop canvas to the bounding rectangle defined by (x, y, width, height)."""
        req = JobRequest(
            action="canvas.crop",
            params={
                "doc_id": doc_id,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
            },
        )
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to crop canvas for doc '{doc_id}'")

    async def rotate_canvas(self, doc_id: str, angle_degrees: float) -> dict[str, Any]:
        """Rotate the entire canvas by a specified angle in degrees (e.g. 90.0, 180.0, 270.0)."""
        req = JobRequest(
            action="canvas.rotate",
            params={"doc_id": doc_id, "angle_degrees": angle_degrees},
        )
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to rotate canvas for doc '{doc_id}'")

    async def get_canvas_bounds(self, doc_id: Optional[str] = None) -> dict[str, Any]:
        """Retrieve canvas boundaries, resolution, and current dimensions."""
        params = {"doc_id": doc_id} if doc_id else {}
        req = JobRequest(action="canvas.bounds", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, "Failed to retrieve canvas bounds")

    async def sample_pixel(
        self,
        doc_id: str,
        x: int,
        y: int,
        layer_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Sample exact RGBA pixel color at (x, y) from composite canvas or specific layer."""
        req = JobRequest(
            action="canvas.sample_pixel",
            params={"doc_id": doc_id, "x": x, "y": y, "layer_name": layer_name},
        )
        resp = await self.client.send_job(req)
        result = self._ensure_success(resp, f"Failed to sample pixel at ({x}, {y})")
        return result.get("sampled_color", result)
