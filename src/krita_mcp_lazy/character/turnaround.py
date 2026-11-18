"""Character turnaround generator, anatomical guide line calculator, and consistency verifier."""

from typing import Any, Dict, List, Optional

from krita_mcp_lazy.character.models import CharacterSheetSpec, ViewAngle
from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.transport.client import AsyncIPCClient


class CharacterTurnaroundEngine:
    """Manages character model sheets, multi-view alignment guides, and proportion rules."""

    def __init__(self, client: Optional[AsyncIPCClient] = None) -> None:
        self.client = client or AsyncIPCClient()

    def calculate_guide_lines(self, spec: CharacterSheetSpec) -> Dict[str, float]:
        """Compute exact pixel heights for anatomical guide lines based on head height ratio."""
        h_ratio = spec.head_height_ratio
        total_h = spec.total_height_px
        top = spec.top_offset_px
        head_h = total_h / h_ratio

        return {
            "top_of_head": round(float(top), 1),
            "hair_volume": round(float(top - head_h * 0.15), 1),
            "eye_line": round(float(top + head_h * 0.5), 1),
            "nose_line": round(float(top + head_h * 0.75), 1),
            "chin_line": round(float(top + head_h), 1),
            "shoulder_line": round(float(top + head_h * 1.4), 1),
            "chest_line": round(float(top + head_h * 2.0), 1),
            "waist_line": round(float(top + head_h * 3.0), 1),
            "hips_line": round(float(top + head_h * 4.0), 1),
            "knee_line": round(float(top + head_h * 5.5), 1),
            "ankle_line": round(float(top + head_h * (h_ratio - 0.5)), 1),
            "ground_line": round(float(top + total_h), 1),
        }

    async def setup_turnaround_canvases(
        self,
        doc_id: str,
        spec: CharacterSheetSpec,
    ) -> Dict[str, Any]:
        """Configure Krita document with turnaround layer groups and proportion guide lines."""
        guide_lines = self.calculate_guide_lines(spec)

        payload = {
            "doc_id": doc_id,
            "character_name": spec.character_name,
            "views": [v.value for v in spec.views],
            "head_height_ratio": spec.head_height_ratio,
            "guide_lines": guide_lines,
            "clothing_tokens": spec.clothing_tokens or [],
            "color_tokens": spec.color_tokens or {},
        }

        resp = await self.client.send_job("character.setup_turnaround", payload)
        if resp.status == "error":
            err_dict = resp.error or {}
            err_code = err_dict.get("code", "DOCUMENT_ERROR")
            try:
                code_enum = ErrorCode(err_code)
            except ValueError:
                code_enum = ErrorCode.DOCUMENT_ERROR
            raise KritaError(code_enum, err_dict.get("message", "Character turnaround setup failed"))

        return resp.result or {}

    async def verify_character_consistency(
        self,
        doc_id: str,
        character_name: str,
        views: List[ViewAngle],
    ) -> Dict[str, Any]:
        """Verify alignment, silhouette proportions, and facial anchor consistency across views."""
        payload = {
            "doc_id": doc_id,
            "character_name": character_name,
            "views": [v.value for v in views],
        }

        resp = await self.client.send_job("character.verify_consistency", payload)
        if resp.status == "error":
            err_dict = resp.error or {}
            err_code = err_dict.get("code", "DOCUMENT_ERROR")
            try:
                code_enum = ErrorCode(err_code)
            except ValueError:
                code_enum = ErrorCode.DOCUMENT_ERROR
            raise KritaError(code_enum, err_dict.get("message", "Consistency check failed"))

        return resp.result or {}
