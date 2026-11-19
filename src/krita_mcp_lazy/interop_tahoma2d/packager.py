"""Multi-layer asset slicing and JSON manifest packager for Tahoma2D puppet rigging."""

from typing import Any, Dict, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError, check_job_response
from krita_mcp_lazy.transport.client import AsyncIPCClient


class AssetPackager:
    """Slices individual layer nodes into transparent PNGs and exports pivot metadata manifests."""

    def __init__(self, client: Optional[AsyncIPCClient] = None) -> None:
        self.client = client or AsyncIPCClient()

    async def package_character_cutout(
        self,
        doc_id: str,
        character_group: str,
        output_dir: str,
    ) -> Dict[str, Any]:
        """Export child layers of a character group as individual cutout PNGs with pivot manifests."""
        payload = {
            "doc_id": doc_id,
            "character_group": character_group,
            "output_dir": output_dir,
        }

        resp = await self.client.send_job("tahoma2d.package_cutout", payload)
        return check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Cutout packaging failed")
