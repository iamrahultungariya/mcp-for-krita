"""Advanced masking engine: transparency masks, filter masks, and non-destructive alpha inheritance."""

import logging
from enum import Enum
from typing import Any, List, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobStatus
from krita_mcp_lazy.transport.client import AsyncIPCClient

logger = logging.getLogger(__name__)


class MaskType(str, Enum):
    """Supported mask types in Krita."""

    TRANSPARENCY = "transparency"
    FILTER = "filter"
    SELECTION = "selection"
    TRANSFORM = "transform"
    COLORIZE = "colorize"


class MaskService:
    """Orchestrates non-destructive masking, clipping masks, and alpha inheritance."""

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

    async def add_mask(
        self,
        doc_id: str,
        layer_id: str,
        mask_type: MaskType | str,
        name: str = "Mask",
        filter_config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Attach a non-destructive mask (transparency, filter, transform) to a target layer."""
        m_type = mask_type.value if isinstance(mask_type, MaskType) else mask_type
        params = {
            "doc_id": doc_id,
            "layer_id": layer_id,
            "mask_type": m_type,
            "name": name,
            "filter_config": filter_config or {},
        }
        req = JobRequest(action="mask.add", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to add mask to layer '{layer_id}' in doc '{doc_id}'")

    async def remove_mask(self, doc_id: str, mask_id: str) -> dict[str, Any]:
        """Remove a mask from its parent layer."""
        params = {"doc_id": doc_id, "mask_id": mask_id}
        req = JobRequest(action="mask.remove", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to remove mask '{mask_id}' in doc '{doc_id}'")

    async def set_alpha_inheritance(
        self,
        doc_id: str,
        layer_id: str,
        inherit_alpha: bool = True,
    ) -> dict[str, Any]:
        """Enable or disable alpha inheritance (clipping mask behavior) on target layer."""
        params = {
            "doc_id": doc_id,
            "layer_id": layer_id,
            "inherit_alpha": inherit_alpha,
        }
        req = JobRequest(action="layer.alpha_inheritance", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to set alpha inheritance for layer '{layer_id}'")

    async def list_masks(self, doc_id: str, layer_id: str) -> List[dict[str, Any]]:
        """List all masks attached to the specified layer."""
        params = {"doc_id": doc_id, "layer_id": layer_id}
        req = JobRequest(action="mask.list", params=params)
        resp = await self.client.send_job(req)
        result = self._ensure_success(resp, f"Failed to list masks for layer '{layer_id}'")
        return result.get("masks", [])
