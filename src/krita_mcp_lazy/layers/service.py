"""Layer management service for tree navigation, layer creation, reordering, and attributes."""

import logging
from typing import Any, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobStatus
from krita_mcp_lazy.layers.models import LayerSpec, ReorderPosition
from krita_mcp_lazy.transport.client import AsyncIPCClient

logger = logging.getLogger(__name__)


class LayerService:
    """Orchestrates layer creation, hierarchy inspection, reordering, and blending properties."""

    def __init__(self, client: AsyncIPCClient) -> None:
        self.client = client

    def _ensure_success(self, resp: Any, default_message: str) -> dict[str, Any]:
        """Validate response status or raise KritaError with proper taxonomy code."""
        if resp.status != JobStatus.SUCCESS:
            code = ErrorCode.LAYER_ERROR
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

    async def inspect_layer_tree(self, doc_id: Optional[str] = None) -> dict[str, Any]:
        """Retrieve the full hierarchical layer tree of the active or specified document."""
        params = {"doc_id": doc_id} if doc_id else {}
        req = JobRequest(action="layer.tree", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, "Failed to inspect layer tree")

    async def create_layer(self, doc_id: str, spec: LayerSpec) -> dict[str, Any]:
        """Create a new layer or group layer according to LayerSpec."""
        params = {"doc_id": doc_id, **spec.model_dump()}
        req = JobRequest(action="layer.create", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to create layer '{spec.name}' in doc '{doc_id}'")

    async def delete_layer(self, doc_id: str, layer_name: str) -> dict[str, Any]:
        """Delete specified layer from document."""
        params = {"doc_id": doc_id, "layer_name": layer_name}
        req = JobRequest(action="layer.delete", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to delete layer '{layer_name}' in doc '{doc_id}'")

    async def reorder_layer(
        self,
        doc_id: str,
        target_layer: str,
        reference_layer: str,
        position: ReorderPosition | str = ReorderPosition.ABOVE,
    ) -> dict[str, Any]:
        """Move target_layer relative to reference_layer (above, below, inside)."""
        pos_str = position.value if isinstance(position, ReorderPosition) else position
        params = {
            "doc_id": doc_id,
            "target": target_layer,
            "reference": reference_layer,
            "position": pos_str,
        }
        req = JobRequest(action="layer.reorder", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to reorder layer '{target_layer}' {pos_str} '{reference_layer}'")

    async def set_layer_properties(
        self,
        doc_id: str,
        layer_name: str,
        opacity: Optional[int] = None,
        visible: Optional[bool] = None,
        locked: Optional[bool] = None,
        blending_mode: Optional[str] = None,
    ) -> dict[str, Any]:
        """Modify opacity (0-255), visibility, locked state, or blending mode of a layer."""
        params: dict[str, Any] = {"doc_id": doc_id, "layer_name": layer_name}
        if opacity is not None:
            params["opacity"] = opacity
        if visible is not None:
            params["visible"] = visible
        if locked is not None:
            params["locked"] = locked
        if blending_mode is not None:
            params["blending_mode"] = blending_mode

        req = JobRequest(action="layer.set_properties", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to set properties for layer '{layer_name}'")

    async def set_active_layer(self, doc_id: str, layer_name: str) -> dict[str, Any]:
        """Set the designated layer as the active painting node in Krita."""
        params = {"doc_id": doc_id, "layer_name": layer_name}
        req = JobRequest(action="layer.set_active", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to set active layer '{layer_name}'")
