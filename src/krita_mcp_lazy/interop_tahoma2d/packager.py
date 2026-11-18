"""Multi-layer asset slicing and JSON manifest packager for Tahoma2D puppet rigging."""

from typing import Any, Dict, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
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
        if resp.status == "error":
            err_dict = resp.error or {}
            err_code = err_dict.get("code", "DOCUMENT_ERROR")
            try:
                code_enum = ErrorCode(err_code)
            except ValueError:
                code_enum = ErrorCode.DOCUMENT_ERROR
            raise KritaError(code_enum, err_dict.get("message", "Cutout packaging failed"))

        return resp.result or {}
